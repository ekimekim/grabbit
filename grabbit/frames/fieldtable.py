
import sys
import string
from decimal import Decimal as PyDecimal

from datatypes import DataType, Octet, FromStruct, ShortString, LongString, Timestamp
from common import eat, Incomplete


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
		scale = scale.value
		value, data = SignedLong.unpack(data)
		value = value.value
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
		if first not in self.FIRSTCHARS:
			raise ValueError("Illegal character {} as first character of field name".format(first))
		for c in rest:
			if c not in self.CHARS:
				raise ValueError("Illegal character {} in field name".format(c))
		return super(FieldName, self).pack()


class FieldArray(DataType):
	"""Expects an iterable value"""
	def pack(self):
		payload = ''
		for value in self.value:
			if not isinstance(value, DataType):
				value = field_type_coerce(value)
			field_type = type(value)
			field_specifier = FIELD_SPECIFIERS[field_type]
			payload += field_specifier + value.pack()
		return LongString(payload).pack()

	@classmethod
	def unpack(cls, data):
		payload, data = LongString.unpack(data)
		payload = payload.value
		values = []
		try:
			while payload:
				type_specifier, payload = eat(payload, 1)
				field_type = FIELD_TYPES[type_specifier]
				value, payload = field_type.unpack(payload)
				values.append(value.value)
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("FieldArray payload reported Incomplete")
			raise type(ex), ex, tb
		return cls(values), data


class FieldTable(DataType):
	"""Expects a dict value"""
	def pack(self):
		payload = ''
		for name, value in self.value.items():
			if not isinstance(value, DataType):
				value = field_type_coerce(value)
			field_type = type(value)
			field_specifier = FIELD_SPECIFIERS[field_type]
			payload += FieldName(name).pack() + field_specifier + value.pack()
		return LongString(payload).pack()

	@classmethod
	def unpack(cls, data):
		payload, data = LongString.unpack(data)
		payload = payload.value
		values = {}
		try:
			while payload:
				name, payload = FieldName.unpack(payload)
				name = name.value
				type_specifier, payload = eat(payload, 1)
				field_type = FIELD_TYPES[type_specifier]
				value, payload = field_type.unpack(payload)
				values[name] = value.value
		except Incomplete:
			_, _, tb = sys.exc_info()
			ex = ValueError("FieldTable payload reported Incomplete")
			raise type(ex), ex, tb
		return cls(values), data


def field_type_coerce(value):
	"""Pick a field type for value.
	We prefer consistency over the smallest possible representation.
	We thenn return the coverted value.
	"""
	type_map = {
		bool: Boolean,
		int: SignedLongLong,
		long: SignedLongLong,
		float: Double,
		PyDecimal: Decimal,
		str: LongString,
		dict: FieldTable
	}
	if isinstance(value, unicode):
		# if you care about your encoding, you should be doing it yourself
		# as a sensible default, we use UTF-8
		value = value.encode('utf-8')
	for type, datatype in type_map.items():
		if isinstance(value, type):
			return datatype(value)
	if value is None:
		return Void()
	# if we still haven't found a match, our next thing to check is to convert iterables to FieldArrays
	try:
		value = list(value)
	except TypeError:
		pass
	else:
		return FieldArray(value)
	# give up
	raise ValueError("Could not convert {!r} to a field table type".format(value))


# NOTE: These definitions are what is used by RabbitMQ, NOT what is defined by the spec.
# source: https://www.rabbitmq.com/amqp-0-9-1-errata.html as of 2014-04-05
FIELD_TYPES = {
	't': Boolean,
	'b': SignedOctet,
	's': SignedShort,
	'I': SignedLong,
	'l': SignedLongLong,
	'f': Float,
	'd': Double,
	'D': Decimal,
	'S': LongString,
	'A': FieldArray,
	'T': Timestamp,
	'F': FieldTable,
	'V': Void,
	'x': LongString, # NOTE: This is properly defined as "byte array" but the format is identical
	                 #       to LongString. We treat them as the same since we make no attempt at text encoding.
}
FIELD_SPECIFIERS = {v: k for k, v in FIELD_TYPES.items()}
FIELD_SPECIFIERS[LongString] = 'S' # we need to specify this manually as it appears in FIELD_TYPES twice
