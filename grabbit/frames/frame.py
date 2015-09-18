import sys

from grabbit.errors import FrameError, AMQPSyntaxError

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
		('method', Method),
	]

	def __init__(self, *args):
		"""Args can either be a single arg Method, or method_class, method_id, *args
		where *args are passed onto the correct Method constructor"""
		if len(args) == 1 and isinstance(args[0], Method):
			method, = args
			method_class, method_id = method.method_class, method.method_id
		else:
			if len(args) < 2:
				raise TypeError("If no Method given, method_class and method_id must be provided")
			method_class, method_id = args[:2]
			args = args[2:]
			method = Method.from_id(method_class, method_id)(*args)
		super(MethodPayload, self).__init__(method_class, method_id, method)

	@classmethod
	def unpack(cls, data):
		# we special-case as we need to look up correct method class
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
		# we special-case as we need to look up correct properties class
		method_class, data = Short.unpack(data)
		method_class = method_class.value
		weight, data = Short.unpack(data)
		body_size, data = LongLong.unpack(data)
		body_size = body_size.value
		properties, data = Properties.get_by_class(method_class).unpack(data)
		return cls(method_class, body_size, properties), data


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
			raise FrameError("Framing error: Frame ended with {!r}, not {!r}".format(frame_end, cls.FRAME_END),
			                 data=frame_end, header=header, payload=payload)
		payload_type = cls.payload_types[header.type]
		try:
			payload, leftover = payload_type.unpack(payload)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = AMQPSyntaxError("Frame payload expected more data", data=payload, datatype=payload_type)
			raise type(ex), ex, tb
		if leftover:
			raise AMQPSyntaxError("Frame payload had excess bytes: {!r}".format(leftover), data=leftover,
			                  datatype=payload_type, payload=payload)
		return cls(header.type, header.channel, payload), data

	def get_value(self):
		return self

	@classmethod
	def size_without_payload(cls):
		"""The size in bytes of the non-payload parts of a Frame. This value is a constant."""
		return sum(datatype.len() for datatype in FrameHeader.types()) + len(cls.FRAME_END)
