

class Connection(object):
	"""Represents a connection between a server and the client.

	You can wait for a connection to be established with:
		connection.connected.wait()
	or simply start performing operations - they will be deferred until they can be dispatched.
	"""

	# default properties for client_properties
	default_properties = {
		# TODO
	}

	def __init__(self, vhost='/', security_handlers=[], locales=[], frame_size_max=0,
	             heartbeat=True, on_error=None, **properties):
		"""Args:
			vhost: The virtual host to open, "/" by default.
			security_handlers: A list of (security mechanism, response_fn, challenge_fn).
			                   The first mechanism in the list that is supported by the server
			                   will have its matching response_fn called to get a security_response.
			                   The third arg (which may also be omitted or None) is a function that
			                   completes the challenge process by sending/receiving Secure/SecureOK
			                   and should only return once authentication is complete (or raise AuthFailed).
			locales: A list of locales in order of preference. The first locale supported by the server
			         will be selected as the locale for the server to send human-readable messages in.
			         If none match or not given, 'en_US' will be used.
			frame_size_max: Maximum size in bytes for a single frame, or 0 for no limit.
			haertbeat: Whether to enable heartbeat for this connection. Due to confusion in the spec,
			           we cannot reliably specify the actual delay, so this is a boolean flag only.
			on_error: Optional callback to be called if a fatal error occurs in the connection.
			          The callback should take one arg, the error instance.
			properties: Additional information to pass as client_properties.
			            Some values are already set by default.
		"""
		self.vhost = vhost
		self.security_handlers = security_handlers
		self.preferred_locales = locales
		self.tune_params = dict(
			channel_max = 0,
			frame_size_max = frame_size_max,
			heartbeat = heartbeat,
		)
		self.client_properties = self.defualt_properties.copy()
		self.client_properties.update(properties)
		self.on_error = on_error

		self.greenlets = gevent.pool.Group()
		self.connected = gevent.event.Event()
		self.closed = False
		self.socket = None
		self.socket_lock = gevent.lock.RLock()
		self.send_queue = gevent.queue.Queue()
		self.deferred_sends = []

		self.connect()

	def connect(self):
		"""Connect to the server."""

		# TODO socket connect

		self.socket.sendall(ProtocolHeader().pack())
		self.greenlets.spawn(self._send_loop)

		# TODO recv Start
		# TODO locale
		# TODO security
		# TODO send StartOk

		# TODO call out to security handler for challenge

		# TODO recv Tune
		# TODO send TuneOk

		# TODO send-and-get Open->OpenOk

		self.connected.set()
		for item in self.deferred_sends:
			self.send_queue.put(item)

	def close(self, error=None, method=None):
		"""Gracefully close the connection, optionally in response to a given error
		that should be sent to the server.
		"""
		if not error:
			error = ConnectionForced()
		self.closed = True
		self.send_sync_method(methods.connection.Close(error=error, method=method))
		self.error(error)

	def __del__(self):
		self.close()

	def error(self, ex):
		"""React to a fatal error - halt operations and close the socket"""
		# the current greenlet may be in self.greenlets, so to avoid killing ourselves we spawn
		# a seperate greenlet to do the job
		self.closed = True
		@gevent.spawn
		def _error_worker():
			# stop any pending operations by sending ex
			self.greenlets.kill(ex, block=False)
			self.socket.close()
			if self.on_error:
				self.on_error(ex)
		_error_worker.get()

	def send_method(self, channel, method, block=False, callback=None):
		"""Enqueue a method to be sent on given channel. Other args as per send()"""
		self.send(Frame(Frame.METHOD_TYPE, channel, method), block=block, callback=callback)

	def send(self, frame, block=False, callback=None):
		"""Enqueue a frame to be sent. If block=True, don't return until sent.
		If callback is given, it will be called when the frame is sent."""
		sent = gevent.event.Event()
		# we ensure we're blocking on a self.greenlets greenlet,
		# so we receive errors reported to self.error()
		waiter = self.greenlets.spawn(self._send_waiter, sent, callback)
		if not self.connected.is_set() and frame.channel != 0:
			# non-setup operations during setup go onto a deferred queue for later enqueuing proper
			self.deferred_sends.append((frame, sent))
		else:
			self.send_queue.put((frame, sent))
		if block:
			waiter.get()

	def _send_waiter(self, sent, callback):
		sent.wait()
		if callback:
			callback()

	def _send(self, frame):
		"""Actually send the frame."""
		# if we get killed halfway through the operation, we want it to continue
		# until finished (half-sent frames cannot be recovered from).
		# we create background task to do the sending, then wait for it to finish.
		def _send_worker(socket):
			# Note we capture the value of socket here, as by the time this runs,
			# self.socket may be None.
			with self.socket_lock:
				socket.sendall(frame.pack())
		gevent.spawn(_send_worker, self.socket).get()

	def _send_loop(self):
		for frame, sent in self.send_queue:
			self.socket.sendall(frame.pack())
			sent.set()

	def send_sync_method(self, channel, method):
		"""As per send_method, but block until the associated reply is received, and return it."""
		...


