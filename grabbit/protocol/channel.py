

class Channel(object):
	id = None
	priority = 16

	def __init__(self, conn, priority=None, id=None):
		"""Create a new channel. First argument is the parent connection.
		Optional arg priority lets you specify the default priority for this channel's messages,
		see Connection.send() for details.
		id can be used to force a certain channel id (the usefulness of this is debatable).
		"""
		if id is not None:
			self.id = id
		if self.id is None:
			id = conn.get_next_channel()

		if priority is not None:
			self.priority = priority

		if id in conn.channels:
			raise ValueError("Channel {} already exists".format(id))
		conn.channels[id] = self

		self.connection = conn
		self.id = id

		self.connect()

	def connect(self):
		...

	def send(self, method, content=None, properties={}, block=False, priority=None):
		"""Enqueue a method (possibly with content) to be sent.
		Properties is only meaningful when sending content.
		Other args as per connection.send()"""
		if priority is None:
			priority = self.priority

		has_content = (content is not None)
		if has_content and not method.has_content:
			raise ValueError("Method {} does not expect content".format(method))
		if not has_content and method.has_content:
			raise ValueError("Method {} requires content".format(method))

		waiter = self.conn.send(Frame(Frame.METHOD_TYPE, self.id, method),
		                        block=block and not has_content, priority=priority)
		if has_content:
			waiter = self.send_content(method.method_class, content, properties,
			                           block=block, priority=priority)
		if not block:
			return waiter
		waiter.get()

	def send_content(self, method_class, payload, properties, block=False, priority=None):
		"""Enqueue a content payload (aka. a message) to be sent.
		Block and priority are as per connection.send()."""
		if priority is None:
			priority = self.priority
		waiter = self.send(Frame(Frame.HEADER_TYPE, channel, method_class, len(payload), properties))
		frame_max = self.conn.tune_params['frame_size_max']
		if frame_max == 0:
			# if not limited, send in one frame
			frame_max = len(payload) + Frame.size_without_payload()
		payload_max = frame_max - Frame.size_without_payload()
		assert payload_max > 0, "frame_size_max smaller than size needed to send 1 char"
		while payload:
			this_frame, payload = payload[:payload_max], payload[payload_max:]
			waiter = self.send(Frame(Frame.BODY_TYPE, self.id, this_frame))
		if block:
			waiter.get() # wait for last message to send
		else:
			return waiter

	def send_sync(self, method, priority=None):
		"""As per send_method, but block until the associated reply is received, and return it."""
		responses = method.response
		if responses is None:
			raise ValueError("Method {} does not have a syncronous response".format(method))
		if isinstance(method.response, Method):
			responses = responses,
		

	# TODO close

	# TODO wait_for(): Set a temp watch for a message based on params.
	# TODO recv: A handler needs to "claim" a message.
	#            An unclaimed message has a timeout before being dead-lettered and a warning emitted.
	#            This lets us capture specific methods safely without race problems, and still allows
	#            wildcard "any time this happens" handlers.
