import sys

from datatypes import DataType, Octet, Short, Long, LongLong, Sequence
from properties import Properties
from common import eat, Incomplete
from method import Method


class FrameHeader(Sequence):
	fields = [
		('type', Octet),
		('channel', Short),
		('size', Long),
	]


class MethodPayload(Sequence):
	fields = [
		('method_class', Short),
		('method_id', Short),
	]

	def __init__(self, *args):
		"""Args can either be a single arg Method, or method_class, method_id, *args
		where *args are passed onto the correct Method constructor"""
		if len(args) == 1 and isinstance(args[0], Method):
			self.method, = args
			method_class, method_id = self.method.method_class, self.method.method_id
		else:
			if len(args) < 2:
				raise TypeError("If no Method given, method_class and method_id must be provided")
			method_class, method_id  = args[:2]
			args = args[2:]
			self.method = Method.from_id(method_class, method_id)(*args)
		super(MethodPayload, self).__init__(method_class, method_id)

	def pack(self):
		return super(MethodPayload, self).pack() + self.method.pack()

	@classmethod
	def unpack(cls, data):
		method_class, data = Short.unpack(data)
		method_id, data = Short.unpack(data)
		method_type = Method.from_id(method_class.value, method_id.value)
		method, data = method_type.unpack(data)
		return cls(method), data


class ContentHeaderPayload(Sequence):
	fields = [
		('method_class', Short),
		('weight', Short), # always 0
		('body_size', LongLong),
		('properties', Properties),
	]

	def __init__(self, method_class, body_size, properties):
		if not isinstance(properties, Properties):
			properties = Properties.get_by_class(method_class)(properties)
		super(ContentHeaderPayload, self).__init__(method_class, 0, body_size, properties)

	@classmethod
	def unpack(cls, data):
		# we special-case as we need properties unpack class to change according to method_class
		method_class, data = Octet.unpack(data)
		weight, data = Octet.unpack(data)
		body_size, data = LongLong.unpack(data)
		properties, data = Properties.get_by_class(method_class).unpack(data)
		return cls(method_class, body_size, properties)


class ContentPayload(DataType):
	def pack(self):
		return self.value

	@classmethod
	def unpack(cls, data):
		return cls(data), '' # eat it all! because we know we're only being passed the frame body.


class HeartbeatPayload(Sequence):
	fields = [] # heartbeat payload is always 0-length


class Frame(DataType):
	FRAME_END = '\xCE'
	METHOD_TYPE, HEADER_TYPE, BODY_TYPE, HEARTBEAT_TYPE = range(1, 5)
	payload_types = {
		METHOD_TYPE: MethodPayload,
		HEADER_TYPE: ContentHeaderPayload,
		BODY_TYPE: ContentPayload,
		HEARTBEAT_TYPE: HeartbeatPayload,
	}

	def __init__(self, type, channel, *payload):
		self.type = type
		self.channel = channel
		payload_type = self.payload_types[type]
		if len(payload) == 1 and isinstance(payload[0], payload_type):
			self.payload, = payload
		else:
			self.payload = payload_type(*payload)
		super(Frame, self).__init__((self.type, self.channel, self.payload))

	def pack(self):
		payload = self.payload.pack()
		header = FrameHeader(self.type, self.channel, len(payload))
		return header.pack() + payload + self.FRAME_END

	@classmethod
	def unpack(cls, data):
		header, data = FrameHeader.unpack(data)
		payload, data = eat(data, header.size)
		frame_end, data = eat(data, 1)
		if frame_end != cls.FRAME_END:
			raise ValueError("Framing error: Frame ended with {!r}, not {!r}".format(frame_end, cls.FRAME_END))
		payload_type = cls.payload_types[header.type]
		try:
			payload, leftover = payload_type.unpack(payload)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("Frame payload reported Incomplete")
			raise type(ex), ex, tb
		if leftover:
			raise ValueError("Payload had excess bytes: {!r}".format(leftover))
		return cls(header.type, header.channel, payload), data

	def get_value(self):
		return self
