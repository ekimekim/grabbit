
from datatypes import Sequence

class Method(Sequence):
	"""Subclass this class to define a method of the given method_class and method_id.
	Optional attribute "response" may define the synchronous response method for a given method
		(for example, OpenOk is the response to Open). It should be left as None for methods
		without a synchronous response.
	Attribute "has_content" indicates that the method is to be followed by content frames,
		and defaults to False.
	Don't forget to define fields as per datatype.Sequence
	"""
	method_class = NotImplemented
	method_id = NotImplemented
	response = None
	has_content = False

