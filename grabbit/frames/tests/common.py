
import unittest

from grabbit.frames import datatypes
from grabbit.frames.method import Method
from grabbit.frames.properties import Properties, PropertyBit

TEST_METHOD_CLASS = 0xff42 # just in case, we use the extension class range

class TestMethod(Method):
	method_class = TEST_METHOD_CLASS
	method_id = 1
	fields = [
		('foo', datatypes.ShortString),
		('bar', datatypes.LongLong),
	]

class TestProperties(Properties):
	method_class = TEST_METHOD_CLASS
	property_map = [
		("an_int", datatypes.Short),
		("a_bool", PropertyBit),
		("a_string", datatypes.ShortString),
	]


class FramesTestCase(unittest.TestCase):
	def check(self, datatype, expected, *values):
		self.assertEquals(datatype(*values).pack(), expected)
		unpacked, leftover = datatype.unpack(expected)
		self.assertEquals(unpacked, datatype(*values))
		self.assertEquals(leftover, '')
