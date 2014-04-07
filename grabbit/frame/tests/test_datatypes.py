
from unittest import TestCase, main

from grabbit.frames.datatypes import *

class DatatypeTests(TestCase):

	def check(self, datatype, expected, *values):
		self.assertEquals(datatype(*values).pack(), expected)
		unpacked, leftover = datatype.unpack(expected)
		self.assertEquals(unpacked, datatype(*values))
		self.assertEquals(leftover, '')

	def test_octet(self):
		self.check(Octet, '\xab', 0xab)
	def test_short(self):
		self.check(Short, '\xbe\xef', 0xbeef)
	def test_long(self):
		self.check(Long, '\xde\xad\xbe\xef', 0xdeadbeef)
	def test_longlong(self):
		self.check(LongLong, '\x00\x0d\xef\xac\xed\xfa\xca\xde', 0x000defacedfacade)

	def test_shortstring(self):
		self.check(ShortString, '\x0bhello world', "hello world")
	def test_longstring(self):
		self.check(LongString, '\x00\x00\x00\x0bhello world', "hello world")

	def test_bits(self):
		TestFlags = Bits('foo', 'bar', 'baz')
		self.check(TestFlags, True, True, (False), '\x06')
	def test_bits_big(self):
		BigTestFlags = Bits('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j')
		self.check(BigTestFlags,
		           (True, False, True, False, True, True, False, False, False, True),
		           '\x0a\x35')
	def test_bits_properties(self):
		TestFlags = Bits('foo', 'bar', 'baz')
		flags = TestFlags((True, False, True))
		self.assertEquals((flags.foo, flags.bar, flags.baz), (True, False, True))

	def test_proto_header(self):
		self.check(ProtocolHeader, 'AMQP\x00\x00\x09\x01')

	def test_sequence(self):
		class TestSequence(Sequence):
			fields = [
				('one', Short),
				('two', Bits('x', 'y')),
				('three', ShortString),
			]
		obj = TestSequence(1, (True, False), "test")
		self.assertEquals(obj.one, 1)
		self.assertEquals(obj.two.x, True)
		self.assertEquals(obj.two.y, False)
		self.assertEquals(obj.three, "test")
		self.check(TestSequence, '\x00\x01\x01\x04test', 1, (True, False), "test")

if __name__ == '__main__':
	main()
