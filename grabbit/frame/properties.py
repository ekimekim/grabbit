
from datatypes import DataType


class PropertyBit(DataType):
	# this data type never gets explicitly packed/unpacked
	pass


class Properties(DataType):
	property_map = NotImplemented # list of tuples (property name, property type)

	def __init__(self, values):
		"""Values should be a dict"""
		self.values = {}
		for name, value in values.items():
			if name not in property_map:
				raise TypeError("{} not a valid property for this method class".format(name))
			value_type = self.property_map[name]
			if not isinstance(value, value_type):
				value = value_type(value)
			self.values[name] = value
		self.__dict__.update(self.values)

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
