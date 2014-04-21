import struct
import math
from collections import defaultdict

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


class FromStruct(DataType):
	format_char = NotImplemented

	def pack(self):
		return struct.pack(self.struct_fmt(), self.value)

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

class Octet(FromStruct):
	format_char = 'B'

class Short(FromStruct):
	format_char = 'H'

class Long(FromStruct):
	format_char = 'L'

class LongLong(FromStruct):
	format_char = 'Q'
Timestamp = LongLong


class String(DataType):
	len_type = NotImplemented
	len_max = NotImplemented

	def pack(self):
		length = len(self.value)
		if length > self.len_max:
			raise ValueError("String value too long: {!r}".format(self.value))
		return self.len_type(length).pack() + self.value

	@classmethod
	def unpack(cls, data):
		length, data = cls.len_type.unpack(data)
		string, data = eat(data, length.value)
		return cls(string), data

	def __len__(self):
		return self.len_type.len() + len(self.value)

class ShortString(String):
	len_type = Octet
	len_max = 255
	def pack(self):
		if '\0' in self.value:
			raise ValueError("ShortString cannot contain nul characters")
		return super(ShortString, self).pack()

class LongString(String):
	len_type = Long
	len_max = 2**32 - 1


class BitsType(DataType):
	"""This supertype for generated Bits types is used in subclass tests"""
def Bits(*names):
	"""Generates a datatype for len(names) bit fields.
	Fields are accessible under given names
	"""
	length = int(math.ceil(len(names)/8.0))
	class _Bits(BitsType):
		_names = names
		def __init__(self, values):
			super(_Bits, self).__init__(list(values))

		def pack(self):
			masks = []
			values = self.value[:]
			for x in range(length):
				mask = 0
				for bit in range(8):
					if not values: break
					if values.pop(0):
						mask |= 1 << bit
				masks.append(mask)
			return ''.join(Octet(mask).pack() for mask in masks)

		@classmethod
		def unpack(cls, data):
			values = []
			for x in range(length):
				mask, data = Octet.unpack(data)
				mask = mask.value
				for bit in range(8):
					values.append(bool(mask & (1 << bit)))
			values = values[:len(names)] # discard trailing bits
			return cls(values), data

		def __len__(self):
			return length

	def gen_property(bit):
		def get(self): return self.value[bit]
		def set(self, value): self.value[bit] = value
		return property(get, set)
	for bit, name in enumerate(names):
		setattr(_Bits, name, gen_property(bit))

	_Bits.__name__ = '{}_Bits'.format(len(names))
	return _Bits


class ProtocolHeader(DataType):
	def __init__(self, proto_id='\x00', proto_version='\x00\x09\x01'):
		self.proto_id = proto_id
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
	"""Generic class for a datatype which is a fixed sequence of other data types.
	Data values are accessible as attributes.
	fields should be a list of (name, type) or (name, type, default).
	If name is None and value is a BitsType, then the names of the individual bits are exposed,
		eg. they can be accessed with sequence.name and set in the contstructor by kwarg.
	Otherwise, if name is None, this is treated as an "unused" field which will not be settable
		except by the default (this is used to implement those annoying "reserved" fields).
	"""
	fields = NotImplemented # list of tuples (name, type)

	# class methods that are transforms on cls.fields
	@classmethod
	def allnames(cls):
		return [field[0] for field in cls.fields]
	@classmethod
	def names(cls):
		return [name for name in cls.allnames() if name is not None]
	@classmethod
	def types(cls):
		return [field[1] for field in cls.fields]
	@classmethod
	def defaults(cls):
		return {field[0]: field[2] for field in cls.fields if len(field) == 3}
	@classmethod
	def bittypes(cls):
		"""Map from field name to the bittype that contains it"""
		result = {}
		for name, datatype in zip(cls.allnames(), cls.types()):
			if name is not None or not issubclass(datatype, BitsType):
				continue
			for bit_name in datatype._names:
				result[bit_name] = datatype

	def __init__(self, *args, **kwargs):
		"""This constructor takes field values as both ordered args and kwargs."""
		# get defaults
		values = self.defaults()
		# add in args
		values.update(dict(zip(self.names(), args)))
		# extract BitType kwargs
		bittype_kwargs = defaultdict(lambda: {})
		bittypes = self.bittypes()
		for name in kwargs.keys(): # .keys as we modify kwargs during the loop
			if name in bittypes:
				datatype = bittypes[name]
				bittype_kwargs[datatype][name] = kwargs.pop(name)
		# add in kwargs
		values.update(kwargs)

		self.values = ()
		for name, datatype in zip(self.allnames(), self.types()):
			if name not in values:
				if name is None:
					raise TypeError("Unnamed argument of type {} has no default".format(datatype.__name__))
				else:
					raise TypeError("Argument {!r} is required".format(name))
			value = values[name]
			if not isinstance(value, datatype):
				value = datatype(value)
			self.values += (value,)

		super(Sequence, self).__init__(self.values)

	def __getattr__(self, attr):
		for name, value in zip(self.allnames(), self.values):
			if name == attr:
				return value
		raise AttributeError(attr)

	def pack(self):
		return ''.join(value.pack() for value in self.values)

	@classmethod
	def unpack(cls, data):
		values = []
		for datatype in cls.types():
			value, data = datatype.unpack(data)
			values.append(value)
		return cls(*values), data

	def __len__(self):
		return sum(len(value) for value in self.values)
