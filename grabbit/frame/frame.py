import sys

from datatypes import Octet, Short, Long, Sequence
from common import eat


class FrameHeader(Sequence):
	fields = [
		('type', Octet),
		('channel', Short),
		('size', Long),
	]


class Frame(object):
	type = NotImplemented
	payload_type = NotImplemented
	FRAME_END = '\xCE'

	def __init__(self, channel, payload):
		self.channel = channel
		if not isinstance(payload, self.payload_type):
			payload = self.payload_type(*payload)
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
		subcls = cls.resolve_type(header.type)
		try:
			payload, leftover = subcls.payload_type.unpack(payload)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("Payload reported Incomplete")
			raise type(ex), ex, tb
		if leftover:
			raise ValueError("Payload had excess bytes: {!r}".format(leftover))
		return subcls(header.channel, payload)

	@classmethod
	def resolve_type(cls, type):
		for subcls in cls.__subclasses__():
			if subcls.type == type:
				return subcls
		else:
			raise ValueError("Unknown frame type: {!r}".format(type))

class MethodPayload(Sequence):
	fields = [
	]
class MethodFrame(Frame):
	type = 1
	payload_type = MethodPayload

class ContentHeaderPayload(Sequence):
	fields = [
	]
class ContentHeaderFrame(Frame):
	type = 1
	payload_type = MethodPayload

class ContentPayload(Sequence):
	fields = [
	]
class ContentFrame(Frame):
	type = 1
	payload_type = MethodPayload

class HeartbeatPayload(Sequence):
	fields = [
	]
class HeartbeatFrame(Frame):
	type = 1
	payload_type = MethodPayload

	def __init__(self, channel, payload):
		if channel != 0:
			raise CommandInvalid("Heartbeat frame on non-zero channel")
		super(HeartbeatFrame
