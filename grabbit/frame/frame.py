import sys
import itertools as it

from datatypes import Octet, Short, Long, Sequence
from common import eat, Method


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

	@classmethod
	def get_method(cls, method_class, method_id):
		for method in Method.__subclasses__():
			if method.class_id == method_class and method.method_id == method_id:
				return method
		else:
			raise ValueError("Unknown method for class {} and method_id {}".format(method_class, method_id))

	def __init__()
		# TODO pass params through to method unless third arg is Method, use super() for other two

	def pack():
		# TODO super() + method.pack()

	@classmethod
	def unpack():
		# TODO manually interpret shorts, then lookup method and unpack arguments


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


class Frame(object):
	FRAME_END = '\xCE'
	METHOD_TYPE, HEADER_TYPE, BODY_TYPE, HEARTBEAT_TYPE = it.count(1)
	payload_types = {
		1: MethodPayload,
		2: ContentHeaderPayload,
		3: ContentPayload,
		4: HeartbeatPayload,
	}

	def __init__(self, type, channel, *payload):
		self.type = type
		self.channel = channel
		payload_type = self.payload_types[type]
		if len(payload) == 1 and isinstance(payload[0], payload_type):
			self.payload = payload
		else:
			self.payload = payload_type(*payload)

	def pack(self):
		payload = self.payload.pack()
		header = FrameHeader(self.type, self.channel, len(payload))
		return header.pack() + payload + self.FRAME_END

	@classmethod
	def unpack(self, data):
		header, data = FrameHeader.unpack(data)
		payload, data = eat(data, header.size.value)
		frame_end = eat(data, 1)
		if frame_end != cls.FRAME_END:
			raise ValueError("Framing error: Frame ended with {!r}, not {!r}".format(frame_end, cls.FRAME_END))
		payload_type = cls.payload_types[header.type.value]
		try:
			payload, leftover = payload_type.unpack(payload)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("Payload reported Incomplete")
			raise type(ex), ex, tb
		if leftover:
			raise ValueError("Payload had excess bytes: {!r}".format(leftover))
		return cls(header.type, header.channel.value, payload)
