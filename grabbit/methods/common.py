
from grabbit.frames import Method


class CloseMethod(Method):
	"""This class implements some shared functionality between
	channel.Close and connection.Close. In particular, these methods
	behave more like exceptions than normal methods, and we define a
	constructor more suited to this usage.

	Field info:
		code refers to the error code causing the close.
		Spec is unclear about how to handle an application-level close request,
		so we will just set code to 0.
		reason is a human-readable error message. Similar to above, we set it to empty string if no error.
		If the error was due to a failed method, the method class and method id should be given.
		If it was not, again the spec is unclear. We set them both to 0.
	"""
	fields = [
		('code', Short),
		('reason', ShortString),
		('failed_class', Short),
		('failed_method', Short),
	]

	def __init__(self, code=None, reason=None, failed_class=None, failed_method=None,
	             error=None, method=None):
		"""This constructor allows for two alternate sets of arguments: The standard
		*args -> fields constructor (this is required by Sequence.unpack()), and a more useful
		constructor that takes error and method args.
		The second form is assumed if none of the first form args are given.

		The error and method args are both optional and mean the following:
			error: The Channel or Connection exception that is causing the Close.
			method: The Method instance (or class) that failed.
		"""
		if code is None:
			# second form
			if error:
				code = error.code
				reason = str(error)
			if method:
				failed_class = method.method_class
				failed_method = method.method_id
		else:
			# first form
			if any(arg is None for arg in (code, reason, failed_class, failed_method)):
				raise TypeError("Constructor for CloseMethod did not receive enough args")
		super(CloseMethod, self).__init__(code, reason, failed_class, failed_method)
