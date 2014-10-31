
import socket
from weakref import WeakValueDict

import gevent
from gevent import GreenletExit

from grabbit import methods
from grabbit.common import ChunkedPriorityQueue
from grabbit.frames import ProtocolHeader, Frame, Incomplete
from grabbit.errors import AuthFailed, BadServerVersion, ServerClosed # non-AMQP errors
from grabbit.errors import AMQPSyntaxError, ConnectionForced, NoMoreChannels, CommandInvalid # AMQP errors

from channel import Channel

class Connection(object):
	"""Represents a connection between a server and the client.

	You can wait for a connection to be established with:
		connection.connected.wait()
	or simply start performing operations - they will be deferred until they can be dispatched.

	connection.on_error is a set of callbacks.
	You may add callbacks to register them to be called if a fatal error occurs.
	These callbacks are called in seperate greenlets and should take args (connection, exception).
	Note that a graceful connection.close(error) WILL cause the callbacks to be called.
	A causeless connection.close() will have the error set to None.
	"""

	# default properties for client_properties
	default_properties = {
		# TODO
	}

	def __init__(self, host, vhost='/', port=5672, security_handlers=[], locales=[], frame_size_max=0,
	             heartbeat=True, on_error=None, **properties):
		"""Args:
			host, port: Hostname and port number. Host is required. Port defaults to 5672.
			vhost: The virtual host to open, "/" by default.
			security_handlers: A list of security handler objects. Such objects must contain the following:
			                       name: The name of the security mechanism
			                       response: The initial response to send in StartOk, a string.
			                       challenge: Optional. A method that takes the channel object,
			                                  sends and receives Secure and SecureOk messages
			                                  until authenticated or raises AuthFailed.
			                   The first mechanism in the list that is supported by the server will be used.
			                   Entries may also simply be tuples (name, response, challenge) or just
			                   (name, response).
			locales: A list of locales in order of preference. The first locale supported by the server
			         will be selected as the locale for the server to send human-readable messages in.
			         If none match or not given, 'en_US' will be used.
			frame_size_max: Maximum size in bytes for a single frame, or 0 for no limit.
			haertbeat: Whether to enable heartbeat for this connection. Due to confusion in the spec,
			           we cannot reliably specify the actual delay, so this is a boolean flag only.
			on_error: An optional shortcut to immediately set an error callback in connection.on_error.
			properties: Additional information to pass as client_properties.
			            Some values are already set by default.
		"""
		def _normalize_handler(handler):
			try: # iterable?
				handler = tuple(handler)
			except ValueError:
				return handler.name, handler.response, getattr(handler, 'challenge', None)
			if len(handler) == 2:
				handler += None,
			if len(handler) == 3:
				return handler
			raise ValueError("Security handler tuple must be of length 2 or 3")

		self.host = host
		self.port = port
		self.vhost = vhost
		self.security_handlers = map(_normalize_handler, security_handlers)
		self.preferred_locales = locales
		if 0 < frame_size_max <= Frame.size_without_payload():
			raise ValueError("Frame size max {} too small to fit any content".format(frame_size_max))
		self.tune_params = dict(
			channel_max = 0,
			frame_size_max = frame_size_max,
			heartbeat_delay = heartbeat,
		)
		self.client_properties = self.defualt_properties.copy()
		self.client_properties.update(properties)
		self.on_error = set()
		if on_error: self.on_error.add(on_error)

		self.greenlets = gevent.pool.Group()
		self.connected = gevent.event.Event()
		self.socket = None
		self.socket_lock = gevent.lock.RLock()
		self.send_queues = ChunkedPriorityQueue()

		self.channels = WeakValueDict()
		self.control_channel = ControlChannel(self)

		self.connect()

	def connect(self):
		"""Connect to the server."""

		try:
			self.socket = socket.socket()
			self.socket.bind((self.host, self.port))
			self.socket.sendall(ProtocolHeader().pack())

			with self.send_queue.limit_to(0): # block sending "normal" messages until setup finished
				channel = self.control_channel # shortcut variable because lazy, readable
				self.greenlets.spawn(self._send_loop)

				start = channel.wait_for(method=methods.connection.Start)
				self.server_version = start.version
				if self.server_version not in self.SUPPORTED_VERSIONS:
					raise BadServerVersion(version=self.server_version)

				if not start.locales:
					raise AMQPSyntaxError("Start method contained no locales",
					                      data=start._locales, method=start)
				for locale in self.preferred_locales:
					if locale in start.locales:
						break
				else: # none of our suggested locales are supported. use server's preferred.
					locale = start.locales[0]

				for mechanism, response, challenge in self.security_handlers:
					if mechanism in start.security_mechanisms:
						break
				else:
					raise AuthFailed(("No given security mechanisms supported by server. "
					                  "Server supports: {}").format(', '.join(start.security_mechanisms)),
					                 server_supports=start.security_mechanisms)

				channel.send(methods.connection.StartOk(self.client_properties,
														mechanism,
														response,
														locale))

				if challenge:
					challenge()

				tune = channel.wait_for(method=methods.connection.Tune)
				if 0 < tune.frame_size_max <= Frame.size_without_payload():
					raise AMQPSyntaxError("frame-max {} is too small to send any content".format(tune.frame_size_max),
					                      method=tune, frame_size_max=tune.frame_size_max)
				# reconcile our tune_params with contents of tune method
				for param in ('channel_max', 'frame_size_max', 'heartbeat_delay'):
					ours = self.tune_params[param]
					theirs = getattr(tune, param)
					if param == 'heartbeat_delay': # special case, see help(TuneOk)
						self.tune_params[param] = theirs if ours and theirs else 0
					else:
						self.tune_params[param] = (ours if ours != 0 and (theirs == 0 or ours < theirs)
						                           else theirs)
				channel.send(methods.connection.TuneOk(**self.tune_params))

				channel.send_sync(methods.connection.Open(self.vhost))

				self.connected.set()
		except Exception as ex:
			self.error(ex)
			raise

	def wait(self):
		"""Block until connection is closed. Raises if connection fails.
		This is the reccomended way to "block forever" when application setup is complete."""
		self.finished.get()

	def channel(self, priority=16):
		"""Spawn a new channel. Note the new channel will be automatically closed if you lose
		all other references to it."""
		return Channel(self, priority=priority)

	def close(self, error=None, method=None, wait_for_ok=True):
		"""Gracefully close the connection, optionally in response to a given error
		that should be sent to the server.
		wait_for_ok=False causes the socket to be closed immediately, without waiting for
		a CloseOk. It should only be used in situations where messages can no longer be received.
		close() should not be used if messages can no longer be sent - use error() instead.
		"""
		if not self.finished.ready():
			# only attempt a graceful close if we aren't already shutting down
			send_error = ConnectionForced() if error is None else error
			self.send_queue.set_limit(-1) # now no more messages can be sent except Close-related
			close_method = methods.connection.Close(error=send_error, method=method)
			waiter = self.control_channel.send_sync(close_method, priority=-1, block=False)
			if wait_for_ok:
				waiter.get()
		self.error(error)

	def __del__(self):
		if not self.finished.ready():
			self.close()

	def error(self, ex):
		"""React to a fatal error - halt operations and close the socket"""

		# NOTE: This function is the common point for stopping all connection operations,
		# gracefully or not. If we have a fatal error, we raise this same error in all greenlets.
		# This should ensure that no matter where you're watching, you'll get the REAL reason for
		# the stoppage (with a generic GreenletExit indicating a graceful close).

		if self.finished.ready() and self.finished.exception == ex:
			return # don't report errors we raised in the process of running error()
		if ex:
			self.finished.set_exception(ex)
		else:
			self.finished.set(None)

		# the current greenlet may be in self.greenlets, so to avoid killing ourselves we spawn
		# a seperate greenlet to do the job
		@gevent.spawn
		def _error_worker():
			# stop any pending operations by sending ex. 
			self.greenlets.kill(ex if ex else GreenletExit, block=False)
			self.socket.close()
			for cb in self.on_error:
				gevent.spawn(cb, self, ex)
		_error_worker.get()

	def send(self, frame, block=False, callback=None, priority=16):
		"""Enqueue a frame to be sent. If block=True, don't return until sent.
		If callback is given, it will be called when the frame is sent.
		If block is False, returns a greenlet which will run until the frame is sent.
		Messages sent at the same priority will be sent in the order send() was called.
		Messages of a lower priority will be sent before any enqueued messages of a higher priority.
		Priorities are defined as follows:
			-1: Reserved for connection close and other exceptional events.
			0: High priority protocol tasks. Users MUST NOT use this or any lower priority.
			16: Normal operation (the default).
			32: Reccomended setting for high-message-count operations, to avoid starving smaller messages.
		"""
		sent = gevent.event.AsyncResult() # AsyncResult lets us propogate an exception if needed
		# we ensure we're blocking on a self.greenlets greenlet,
		# so we receive errors reported to self.error()
		waiter = self.greenlets.spawn(self._send_waiter, sent, callback)
		self.send_queue.put((priority, (frame, sent)))
		if block:
			waiter.get()
		else:
			return waiter

	def get_next_channel(self):
		"""Return next available channel id"""
		channel_max = self.tune_params['channel_max'] or 65535 # max implied by data type
		for x in range(channel_max):
			if x not in self.channels:
				return x
		raise NoMoreChannels(channel_max=channel_max, connection=self)

	def _send_waiter(self, sent, callback):
		sent.get()
		if callback:
			callback()

	def _send(self, frame, sent):
		"""Send an individaual frame, blocking until fully sent.
		Will set exception on sent if an error occurs in packing. Will error the whole
		connection if an error occurs in sending, as such errors are unrecoverable."""
		# if we get killed halfway through the operation, we want it to continue
		# until finished (half-sent frames cannot be recovered from).
		# we create a background task to do the sending, then wait for it to finish.
		def _send_worker():
			# Note we capture the value of socket here, as by the time this runs,
			# self.socket may be None.
			send_started = False
			try:
				packed = frame.pack()
				with self.socket_lock:
					send_started = True
					self.socket.sendall(packed)
				sent.set(None)
			except Exception as ex:
				sent.set_exception(ex)
				if send_started:
					raise # partial send is important - otherwise isn't.
		gevent.spawn(_send_worker).get()

	def _send_loop(self):
		try:
			for priority, (frame, sent) in self.send_queue:
				self._send(frame, sent)
		except Exception as ex:
			self.error(ex)
			raise

	def _recv_loop(self):
		buf = ''
		last_read = True # force True on first loop, thereafter quit if nothing read
		try:
			while last_read:
				last_read = self.socket.recv(4096)
				buf += last_read
				try:
					frame, buf = Frame.unpack(buf)
				except Incomplete:
					continue
				except AMQPSyntaxError as ex:
					method = ex.data.get('method', None)
					self.close(ex, method)
					return
				if frame.channel not in self.channels:
					method = frame.payload.method if frame.type == Frame.METHOD_TYPE else None
					self.close(CommandInvalid("Channel {} is not open".format(frame.channel), frame=frame), method)
					return
				self.channels[frame.channel].recv_frame(frame)
			raise ServerClosed()
		except Exception as ex:
			self.close(ex, wait_for_ok=False) # don't wait for close as recv no longer works!


class ControlChannel(Channel):
	"""The zero channel is a special case. It doesn't need opening and is only used for connection-level
	activity."""

	id = 0 # Control channel is always channel 0
	priority = 0 # Control channel by default is high priority

	def connect(self):
		pass # Control channel is created automatically, and cannot be Open()ed

	def close(self, error=None, method=None):
		# A connection close and a channel close mean the same thing for this channel
		self.connection.close(error, method)

	# TODO on recv Close, reply CloseOk and call error()
	# ??? Make that common to Channels, and ControlChannel treats Conn level Closes as local closes?
