
from grabbit.errors import AMQPError
from grabbit.frames import Method, Short, ShortString


class CloseMethod(Method):
	"""This class implements some shared functionality between
	channel.Close and connection.Close. In particular, these methods
	behave more like exceptions than normal methods, and we define a
	constructor and some helpers more suited to this usage.

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
				# allow reason to come from error.reason if present (ie. if error is an instance)
				# or error.__doc__ otherwise (ie. if error is a class)
				reason = getattr(error, 'reason', error.__doc__)
			else:
				code, reason = 0, ''
			if method:
				failed_class = method.method_class
				failed_method = method.method_id
			else:
				failed_class = failed_method = 0
		else:
			# first form
			if any(arg is None for arg in (code, reason, failed_class, failed_method)):
				raise TypeError("Constructor for CloseMethod did not receive enough args")
		super(CloseMethod, self).__init__(code, reason, failed_class, failed_method)

	@property
	def method(self):
		"""Looks up the method that failed, or None"""
		if 0 in (self.failed_class, self.failed_method):
			return None
		return Method.from_id(self.failed_class, self.failed_method)

	@property
	def error(self):
		"""Looks up the error type according to code,
		returning an instance with reason, and method as extra data.
		If no code (no error), returns None."""
		if not self.code:
			return None
		cls = AMQPError.from_code(self.code)
		return cls(self.reason, method=self.method)

	def raise_error(self):
		"""Raises the associated error, if any."""
		if self.error:
			raise self.error
