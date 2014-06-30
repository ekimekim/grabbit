
from grabbit.common import get_all_subclasses

from datatypes import DataType, Short


class PropertyBit(DataType):
	# this data type never gets explicitly packed/unpacked
	pass


class Properties(DataType):
	method_class = NotImplemented
	property_map = NotImplemented # list of tuples (property name, property type)

	def __init__(self, values):
		"""Values should be a dict"""
		self.values = {}
		for name, value in values.items():
			for _name, _type in self.property_map:
				if _name == name:
					value_type = _type
					break
			else:
				raise TypeError("{} not a valid property for this method class".format(name))
			if not isinstance(value, value_type):
				value = value_type(value)
			self.values[name] = value
		# special case for PropertyBit - always present, default False
		for name, type in self.property_map:
			if type == PropertyBit:
				self.values.setdefault(name, PropertyBit(False))
		super(Properties, self).__init__(self.values)

	def __getattr__(self, attr):
		for name, type in self.property_map:
			if name == attr:
				return self.values[name]
		raise AttributeError(attr)

	def get_value(self):
		return {key: value.get_value() for key, value in self.values.items()}

	def pack(self):
		# presence of a property is encoded as a bit in 16-bit words (highest first)
		# last bit of each word is 1 if there is another word coming, else 0
		properties = self.property_map[:]
		masks = []
		value_list = []
		while properties:
			mask = 0
			for bit in range(15, 0, -1):
				if not properties: break
				name, datatype = properties.pop(0)
				if name in self.values:
					value = self.values[name]
					if datatype == PropertyBit:
						# special case for PropertyBit - encode value (default False) instead of presence
						if value.value: mask |= 1 << bit
						continue
					mask |= 1 << bit
					value_list.append(value)
			if properties:
				mask |= 1
			masks.append(mask)
		masks = ''.join(Short(mask).pack() for mask in masks)
		value_list = ''.join(value.pack() for value in value_list)
		return masks + value_list

	@classmethod
	def unpack(cls, data):
		values = {}
		property_index = -1
		list_items = []
		while True:
			mask, data = Short.unpack(data)
			mask = mask.value
			for bit in range(15, 0, -1):
				property_index += 1
				if not mask & (1 << bit):
					continue
				if property_index >= len(cls.property_map):
					raise ValueError("Property bit out of range for {}".format(cls.__name__))
				name, datatype = cls.property_map[property_index]
				if datatype == PropertyBit:
					# special case for PropertyBit - if present, it means True, no list entry
					values[name] = True
					continue
				list_items.append((name, datatype))
			if not mask & 1:
				break
		for name, datatype in list_items:
			value, data = datatype.unpack(data)
			values[name] = value
		return cls(values), data

	@classmethod
	def get_by_class(cls, method_class):
		for subcls in get_all_subclasses(cls):
			if subcls.method_class == method_class:
				return subcls
		raise ValueError("No Properties defined for method class {:x}".format(method_class))
