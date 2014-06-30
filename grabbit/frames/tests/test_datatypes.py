
from unittest import main

from grabbit.frames.datatypes import *

from common import FramesTestCase

class DatatypeTests(FramesTestCase):

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
		self.check(TestFlags, '\x03', (True, True, False))
	def test_bits_big(self):
		BigTestFlags = Bits('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j')
		self.check(BigTestFlags,
		           '\x35\x02',
		           (True, False, True, False, True, True, False, False, False, True))
	def test_bits_properties(self):
		TestFlags = Bits('foo', 'bar', 'baz')
		flags = TestFlags((True, False, True))
		self.assertEquals((flags.foo, flags.bar, flags.baz), (True, False, True))

	def test_proto_header(self):
		self.check(ProtocolHeader, 'AMQP\x00\x00\x09\x01')

	def test_sequence(self):
		class TestSequence(Sequence):
			fields = [
				(None, ShortString, ''),
				('one', Short),
				(None, Bits('two', 'three')),
				('four', ShortString, 'test'),
				('five', Short, 5),
			]
		obj = TestSequence(1, two=True, three=False, five=3)
		self.assertEquals(obj.one, 1)
		self.assertEquals(obj.two, True)
		self.assertEquals(obj.three, False)
		self.assertEquals(obj.four, "test")
		self.assertEquals(obj.five, 3)
		self.check(TestSequence, '\x00\x00\x01\x01\x04test\x00\x03', 1, two=True, three=False, five=3)

if __name__ == '__main__':
	main()
