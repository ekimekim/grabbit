
from datatypes import Sequence

class Method(Sequence):
	"""Subclass this class to define a method of the given method_class and method_id.
	Optional attribute "response" may define the synchronous response method for a given method
		(for example, OpenOk is the response to Open). It should be left as None for methods
		without a synchronous response.
	Don't forget to define fields as per datatype.Sequence
	"""
	method_class = NotImplemented
	method_id = NotImplemented
	response = None

