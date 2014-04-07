
import decimal
from collections import OrderedDict
from unittest import main

from grabbit.frames.fieldtable import *

from common import FramesTestCase


class FieldTableTests(FramesTestCase):

	def test_signed_octet(self):
		self.check(SignedOctet, '\xff', -1)
	def test_signed_short(self):
		self.check(SignedShort, '\xff\xff', -1)
	def test_signed_long(self):
		self.check(SignedLong, '\xff\xff\xff\xff', -1)
	def test_signed_longlong(self):
		self.check(SignedLongLong, '\xff\xff\xff\xff\xff\xff\xff\xff', -1)

	def test_float(self):
		self.check(Float, '\x3f\x80\x00\x00', 1)
	def test_double(self):
		self.check(Double, '\x3f\xf0\x00\x00\x00\x00\x00\x00', 1)

	def test_decimal(self):
		self.check(Decimal, '\x01\x00\x00\x00\x05', 0.5)

	def test_void(self):
		self.check(Void, '')

	def test_field_name(self):
		self.check(FieldName, '\x06foobar', 'foobar')

	def test_table(self):
		# we use an ordered dict to make the packed result predictable
		values = OrderedDict([
			('a', False),
			('b', 255),
			('c', 0.5),
			('d', decimal.Decimal('0.5')),
			('e', 'test'),
			('f', None),
			('g', {'inner': 'foobar'}),
			('h', ['x', 'y']),
		])
		expected = (
			'\x00\x00\x00\x5b' # payload size: 3*8+1+8+8+5+8+21+16 = 91
			# payload:
				'\x01a' 't' '\x00' # a Boolean False
				'\x01b' 'l' '\x00\x00\x00\x00\x00\x00\x00\xff' # b SignedLongLong 255
				'\x01c' 'd' '\x3f\xe0\x00\x00\x00\x00\x00\x00' # c Double 0.5
				'\x01d' 'D' '\x01\x00\x00\x00\x05' # d Decimal 0.5 (Octet scale + SignedLong value)
				'\x01e' 'S' '\x00\x00\x00\x04test' # e LongString "test"
				'\x01f' 'V' # f Void
				'\x01g' 'F' # g FieldTable:
					'\x00\x00\x00\x11' # payload size: 17
					# payload:
						'\x05inner' 'S' '\x00\x00\x00\x06foobar' # inner LongString "foobar"
				'\x01h' 'A' # h FieldArray:
					'\x00\x00\x00\x0c' # payload size: 12
					# payload:
						'S' '\x00\x00\x00\x01x' # LongString "x"
						'S' '\x00\x00\x00\x01y' # LongString "y"
		) # phew...
		self.check(FieldTable, expected, values)


if __name__ == '__main__':
	main()
