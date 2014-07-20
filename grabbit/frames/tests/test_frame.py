
from unittest import main

from grabbit.frames.frame import Frame

from common import TEST_METHOD_CLASS, TestMethod, FramesTestCase


class FrameTests(FramesTestCase):

	def check(self, frame, expected):
		self.assertEquals(frame.pack(), expected)
		unpacked, leftover = Frame.unpack(expected)
		self.assertEquals(unpacked, frame)
		self.assertEquals(leftover, '')

	def test_method_frame(self):
		frame = Frame(Frame.METHOD_TYPE, 1, TestMethod('hello world', 1234))
		expected = (
			"\x01" # frame type: method
			"\x00\x01" # channel: 1
			"\x00\x00\x00\x18" # payload size: 24
			# payload:
				"\xff\x42" # method class: 0xff42
				"\x00\x01" # method id: 1
				# method args:
					"\x0bhello world" # foo: "hello world"
					"\x00\x00\x00\x00\x00\x00\x04\xd2" # bar: 1234
			"\xCE" # frame end
		)
		self.check(frame, expected)

	def test_header_frame(self):
		frame = Frame(Frame.HEADER_TYPE, 1, TEST_METHOD_CLASS, 42, {"an_int": 7, "a_bool": True})
		expected = (
			"\x02" # frame type: header
			"\x00\x01" # channel: 1
			"\x00\x00\x00\x10" # payload size: 16
			# payload:
				"\xff\x42" # method class: 0xff42
				"\x00\x00" # weight: 0
				"\x00\x00\x00\x00\x00\x00\x00\x2a" # content body size: 42 (meaningless here)
				# properties:
					"\xc0\x00" # flags: 1st and 2nd bits set, no more flags
					"\x00\x07" # an_int: 7
					# a_bool: present, but no data as it is a bool
			"\xCE" # frame end
		)
		self.assertEquals(frame.pack(), expected)

	def test_body_frame(self):
		frame = Frame(Frame.BODY_TYPE, 1, "placeholder strings are hard")
		expected = (
			"\x03" # frame type: body
			"\x00\x01" # channel: 1
			"\x00\x00\x00\x1c" # payload size: 28
			# payload:
				"placeholder strings are hard"
			"\xCE" # frame end
		)
		self.assertEquals(frame.pack(), expected)

	def test_heartbeat(self):
		frame = Frame(Frame.HEARTBEAT_TYPE, 0)
		expected = (
			"\x04" # frame type: body
			"\x00\x00" # channel: 0
			"\x00\x00\x00\x00" # payload size: 0
			"\xCE" # frame end
		)
		self.assertEquals(frame.pack(), expected)


if __name__ == '__main__':
	main()
