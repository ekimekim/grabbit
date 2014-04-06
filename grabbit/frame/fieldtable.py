
from decimal import Decimal as PyDecimal

from datatypes import DataType, Octet, FromStruct

# note that data types defined here (like the Signed integers)
# are defined here because they only ever appear as FieldTable values

class Boolean(Octet):
	def __init__(self, value):
		super(Boolean, self).__init__(bool(value))

class SignedOctet(FromStruct):
	format_char = 'b'

class SignedShort(FromStruct):
	format_char = 'h'

class SignedLong(FromStruct):
	format_char = 'l'

class SignedLongLong(FromStruct):
	format_char = 'q'

class Float(FromStruct):
	format_char = 'f'

class Double(FromStruct):
	format_char = 'd'

class Decimal(DataType):
	"""If you wish to accurately control precision of the value,
	you should pass in an instance of python decimal.Decimal,
	or a string which can be cast to that type."""
	def __init__(self, value):
		if not isinstance(value, PyDecimal):
			value = PyDecimal(value)
		super(Decimal, self).__init__(value)
	def pack(self):
		if not self.value.is_finite():
			raise ValueError("Cannot encode a non-finite value")
		sign, digits, exponent = self.value.as_tuple()
		value = sum(digit * 10**pos for pos, digit in enumerate(digits))
		if sign: value = -value
		scale = -exponent
		return Octet(scale).pack() + SignedLong(value).pack()

	@classmethod
	def unpack(cls, data):
		scale, data = Octet.unpack(data)
		value, data = SignedLong.unpack(data)
		sign = 0
		if value < 0:
			sign = 1
			value = -value
		digits = []
		while value:
			digits.append(value % 10)
			value /= 10
		digits = digits[::-1]
		exponent = -scale
		return cls(PyDecimal((sign, digits, exponent))), data

class Void(DataType):
	def __init__(self):
		super(Void, self).__init__(None)
	def pack(self):
		return ''
	@classmethod
	def unpack(cls, data):
		return Void(), data

class FieldName(ShortString):
	len_max = 128
	FIRSTCHARS = set(string.letters) | {'$', '#'}
	CHARS = FIRSTCHARS | set(string.digits) | {'_'}
	def pack(self):
		first, rest = eat(self.value, 1)
		if first not in FIRSTCHARS:
			raise ValueError("Illegal character {} as first character of field name".format(first))
		for c in rest:
			if c not in CHARS:
				raise ValueError("Illegal character {} in field name".format(c))
		return super(FieldName, self).pack()


# NOTE: These definitions are what is used by RabbitMQ, NOT what is defined by the spec.
# source: https://www.rabbitmq.com/amqp-0-9-1-errata.html as of 2014-04-05
class FieldTable(DataType):
	field_types = {
		't': Boolean,
		'b': SignedOctet,
		's': SignedShort,
		'I': SignedLong,
		'l': SignedLongLong,
		'f': Float,
		'd': Double,
		'D': Decimal,
		'S': LongString,
		'A': FieldArray, # ???
		'T': Timestamp,
		'F': None, # NOTE: We want to put FieldTable here, but that kind of recursive usage
		           #       is not possible within the class definition itself, we add it afterwards.
		'V': Void,
		'x': # TODO ??? rabbit calls this "byte array" but it's unclear if it's similar to ShortString or LongString
	}

	def __init__(self, **value):
		super(self, FieldTable).__init__(value)

	def pack(self):
		payload = ''
		for name, value in self.values.items():
			field_type = self.choose_type(value)
			field_specifier = {v: k for k, v in self.field_types.items()}[field_type]
			payload += FieldName(name).pack() + field_specifier + field_type(value).pack()
		return LongString(payload).pack()


FieldTable.field_types['F'] = FieldTable # see earlier comment on field_types['F']
