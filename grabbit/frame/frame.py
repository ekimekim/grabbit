import sys

from datatypes import Octet, Short, Long, Sequence
from common import eat


class FrameHeader(Sequence):
	fields = [
		('type', Octet),
		('channel', Short),
		('size', Long),
	]


class MethodPayload(Sequence):
	fields = []
class ContentHeaderPayload(Sequence):
class ContentPayload(Sequence):
class HeartbeatPayload(Sequence):


class Frame(object):
	FRAME_END = '\xCE'
	payload_types = {
		1: MethodPayload,
		2: ContentHeaderPayload,
		3: ContentPayload,
		4: HeartbeatPayload,
	}

	def __init__(self, type, channel, payload):
		self.type = type
		self.channel = channel
		payload_type = self.payload_types[type]
		if not isinstance(payload, payload_type):
			payload = payload_type(*payload)
		self.payload = payload

	def pack(self):
		payload = self.payload.pack()
		header = FrameHeader(self.type, self.channel, len(payload))
		return header.pack() + payload + self.FRAME_END

	@classmethod
	def unpack(self, data):
		header, data = FrameHeader.unpack(data)
		payload, data = eat(data, header.size)
		frame_end = eat(data, 1)
		if frame_end != cls.FRAME_END:
			raise ValueError("Framing error: Frame ended with {!r}, not {!r}".format(frame_end, cls.FRAME_END))
		payload_type = cls.payload_types[header.type]
		try:
			payload, leftover = payload_type.unpack(payload)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("Payload reported Incomplete")
			raise type(ex), ex, tb
		if leftover:
			raise ValueError("Payload had excess bytes: {!r}".format(leftover))
		return cls(header.type, header.channel, payload)


	fields = [
	]
class HeartbeatFrame(Frame):
	type = 1
	payload_type = MethodPayload

	def __init__(self, channel, payload):
		if channel != 0:
			raise CommandInvalid("Heartbeat frame on non-zero channel")
		super(HeartbeatFrame
