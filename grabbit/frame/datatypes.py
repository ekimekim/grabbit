import struct

from common import eat

class DataType(object):
	def __init__(self, value):
		"""Simple data types may wish to not override this and use value directly.
		Data types with multiple values may wish to set their own attributes,
		and simply use self.value as an equality indicator (two pieces of data are equal if
		their types match and their .value are equal)"""
		self.value = value

	def __repr__(self):
		return "<{self.__class__.__name__} {self.value!r}>".format(self=self)
	__str__ = __repr__

	def __eq__(self, other):
		return type(self) == type(other) and self.value == other.value

	def pack(self):
		raise NotImplementedError

	@classmethod
	def unpack(cls, data):
		"""Data may be longer than needed.
		Returns (instance of datatype, left over data).
		Raises Incomplete if data is incomplete.
		"""
		raise NotImplementedError

	def __len__(self):
		"""You may override this if there's a better way to get length than simply packing."""
		return len(self.pack())


class Integer(DataType):
	format_char = NotImplemented

	def pack(self):
		return struct.pack(self.struct_fmt(), value)

	@classmethod
	def unpack(cls, data):
		data, leftover = eat(data, cls.len())
		value, = struct.unpack(cls.struct_fmt(), data)
		return cls(value), leftover

	@classmethod
	def struct_fmt(cls):
		return '!' + cls.format_char

	@classmethod
	def len(cls):
		return struct.calcsize(cls.struct_fmt())

	def __len__(self):
		return self.len()

class Octet(Integer):
	format_char = 'B'

class Short(Integer):
	format_char = 'H'

class Long(Integer):
	format_char = 'L'

class LongLong(Integer):
	format_char = 'Q'


class String(DataType):
	len_type = NotImplemented
	len_max = NotImplemented

	def pack(self):
		length = len(self.value)
		if length > self.len_max:
			raise ValueError("Value too long: {!r}".format(self.value))
		return self.len_type(length).pack() + self.value

	@classmethod
	def unpack(cls, data):
		length, data = cls.len_type.unpack(data)
		string, data = eat(data, length)
		return cls(string), data

	def __len__(self):
		return self.len_type.len() + len(self.value)

class ShortString(String):
	len_type = Octet
	len_max = 255

class LongString(String):
	len_type = Long
	len_max = 2**32 - 1


class ProtocolHeader(DataType):
	def __init__(self, proto_id='\x00', proto_version='\x00\x09\x01'):
		self.proto_version = proto_version
		super(ProtocolHeader, self).__init__((proto_id, proto_version))

	def pack(self):
		return "AMQP" + self.proto_id + self.proto_version

	@classmethod
	def unpack(cls, data):
		amqp, data = eat(data, 4)
		if amqp != "AMQP":
			raise ValueError('Invalid data: Data did not begin with "AMQP"')
		proto_id, data = eat(data, 1)
		proto_version, data = eat(data, 3)
		return cls(proto_id, proto_version), data

	def __len__(self):
		return 8


class Sequence(DataType):
	"""Generic class for a datatype which is a fixed sequence of other data types."""
	fields = NotImplemented # list of tuples (name, type)

	def __init__(self, *values):
		"""For a little magic niceness, we write attrs based on field names."""
		if len(fields) != len(values):
			raise TypeError("Wrong number of args to {}: Expected {}, got {}".format(
			                type(self).__name__, len(self.fields), len(values)))
		self.values = ()
		for (name, datatype), value in zip(fields, values):
			if not isinstance(value, datatype):
				value = datatype(value)
			setattr(self, name, value)
			self.values += (value,)
		super(Sequence, self).__init__(self.values)

	def pack(self):
		return ''.join(value.pack() for value in self.values)

	@classmethod
	def unpack(cls, data):
		values = []
		for name, datatype in fields:
			value, data = datatype.unpack(data)
			values.append(value)
		return cls(*values, data)

	def __len__(self):
		return sum(len(value) for value in self.values)
