
from grabbit.common import get_all_subclasses
from grabbit.errors import GRabbitError

from datatypes import Sequence

class Method(Sequence):
	"""Subclass this class to define a method of the given method_class and method_id.
	Optional attribute "response" may define the synchronous response method(s) for a given method
		(for example, OpenOk is the response to Open). It should be left as None for methods
		without a synchronous response. Use any iterable for multiple acceptable methods.
	Attribute "has_content" indicates that the method is to be followed by content frames,
		and defaults to False.
	Don't forget to define fields as per datatype.Sequence
	"""
	method_class = NotImplemented
	method_id = NotImplemented
	response = None
	has_content = False

	@classmethod
	def from_id(cls, method_class, method_id):
		"""Look up Method class based on method_class and method_id numbers."""
		for method in get_all_subclasses(Method):
			if method.method_class == method_class and method.method_id == method_id:
				return method
		else:
			raise ValueError("Unknown method for class {} and method_id {}".format(method_class, method_id))

	@classmethod
	def unpack(cls, data):
		try:
			return super(Method, cls).unpack(data)
		except GRabbitError as ex:
			ex.data.setdefault('method', cls)
			raise
