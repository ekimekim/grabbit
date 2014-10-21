

class Channel(object):

	def __init__(self, conn, id=None):
		if id is None:
			id = conn.get_next_channel()

		if id in conn.channels:
			raise ValueError("Channel {} already exists".format(id))
		conn.channels[id] = self

		self.conn = conn
		self.id = id

		self.open()

	def open(self):
		...

	def send_method(self, method, block=False, callback=None):
		"""Enqueue a method to be sent. Other args as per send()"""
		self.conn.send(Frame(Frame.METHOD_TYPE, self.id, method), block=block, callback=callback)

	def send_content(self, method_class, payload, properties, block=False):
		"""Enqueue a content payload (aka. a message) to be sent.
		Block is as per send()."""
		waiter = self.send(Frame(Frame.HEADER_TYPE, channel, method_class, len(payload), properties))
		frame_max = self.conn.tune_params['frame_max'] # TODO include header? what about 0?
		while payload:
			this_frame, payload = payload[:frame_max], payload[frame_max:]
			waiter = self.send(Frame(Frame.BODY_TYPE, self.id, this_frame))
		if block:
			waiter.get() # wait for last message to send
		else:
			return waiter

	def send_sync_method(self, method):
		"""As per send_method, but block until the associated reply is received, and return it."""
		...

	# TODO close, error


class ControlChannel(Channel):
	"""Special case of channel - it should NOT send an Open."""

	def open(self):
		pass
