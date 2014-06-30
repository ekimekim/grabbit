import struct
import math

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
		if isinstance(other, DataType):
			return type(self) == type(other) and self.value == other.value
		return self.value == other

	def get_value(self):
		"""This should return the "value" that the user expects to get when reading this data type.
		For simple data types, this can just be self.value (and this default). Others may wish to
		return other values, or even just self."""
		return self.value

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
			values = list(values)
			if len(values) != len(names):
				raise ValueError("Bad length for values, expected {} items, got: {!r}".format(len(names), values))
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

		def get_value(self):
			return self

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
		eg. they can be accessed with sequence.name and set in the constructor by kwarg.
	Otherwise, if name is None, this is treated as an "unused" field which will not be settable
		except by the default (this is used to implement those annoying "reserved" fields).
		(This latter part also applies to Bits() names, where None values will always be False)
	"""
	fields = NotImplemented # list of tuples (name, type)

	# class methods that are transforms on cls.fields
	@classmethod
	def allnames(cls):
		"""All names in fields"""
		return [field[0] for field in cls.fields]
	@classmethod
	def names(cls):
		"""All non-None names in fields"""
		return [name for name in cls.allnames() if name is not None]
	@classmethod
	def types(cls):
		return [field[1] for field in cls.fields]
	@classmethod
	def defaults(cls):
		"""Returns a list of the default value for each field respectively,
		with None for fields without a default"""
		return [field[2] if len(field) >= 3 else None for field in cls.fields]
	@classmethod
	def bitnames(cls):
		"""Returns a list of the attr names of each bittype field, or None if not a bittype"""
		return [datatype._names if issubclass(datatype, BitsType) else None for datatype in cls.types()]

	def __init__(self, *args, **kwargs):
		"""This constructor takes field values as both ordered args and kwargs.
		Note that only named fields are taken as args, and bit fields that are exposed (by having
		the field name of the BitsType set to None) must be set from kwargs.
		"""
		values = {None: False} # This gives a default to BitType flags named None
		values.update(dict(zip(self.names(), args)))
		values.update(kwargs)

		self.values = ()
		for name, datatype, default, bitnames in zip(self.allnames(), self.types(),
		                                             self.defaults(), self.bitnames()):
			if name is not None and name in values:
				value = values[name]
			elif bitnames is not None:
				missing = set(bitnames) - set(values.keys())
				if missing:
					raise TypeError("Flags {} not given".format(', '.join(missing)))
				value = [values[name] for name in bitnames]
			elif default is not None:
				value = default
			elif name is None:
				raise TypeError("Unnamed argument of type {} has no default".format(datatype.__name__))
			else:
				raise TypeError("Argument {!r} is required".format(name))

			if not isinstance(value, datatype):
				value = datatype(value)

			self.values += (value,)

		super(Sequence, self).__init__(self.values)

	def __getattr__(self, attr):
		for name, value, bitnames in zip(self.allnames(), self.values, self.bitnames()):
			if name == attr:
				return value.get_value()
			if bitnames and attr in bitnames:
				return getattr(value, attr)
		raise AttributeError(attr)

	def pack(self):
		return ''.join(value.pack() for value in self.values)

	@classmethod
	def unpack(cls, data):
		kwargs = {}
		for name, datatype, bitnames in zip(cls.allnames(), cls.types(), cls.bitnames()):
			value, data = datatype.unpack(data)
			if name is not None:
				kwargs[name] = value
			if bitnames is not None:
				# map BitType values to bit flag names and update kwargs
				kwargs.update(dict(zip(bitnames, value.value)))
		return cls(**kwargs), data

	def __len__(self):
		return sum(len(value) for value in self.values)
