
from unittest import main

from grabbit.frames.properties import Properties
from grabbit.frames.datatypes import Octet

from common import FramesTestCase, TestProperties, TEST_METHOD_CLASS


class BigProperties(Properties):
	method_class = TEST_METHOD_CLASS + 1
	property_map = [('attr%d' % x, Octet) for x in range(30)]


class PropertiesTests(FramesTestCase):

	def test_basic(self):
		self.check(TestProperties, '\xa0\x00\x00\x03\x03foo', dict(an_int=3, a_bool=False, a_string='foo'))
		self.check(TestProperties, '\xe0\x00\x00\x03\x03foo', dict(an_int=3, a_bool=True, a_string='foo'))
		self.check(TestProperties, '\x40\x00', dict(a_bool=True))

	def test_big(self):
		self.check(BigProperties, '\x00\x01\x00\x00', {})
		self.check(BigProperties, '\xff\xff\xff\xfe' + '\x01' * 30,
		           {attr: 1 for attr, type in BigProperties.property_map})


if __name__ == '__main__':
	main()
