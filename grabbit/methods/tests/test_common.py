
import itertools
from unittest import TestCase

from grabbit.errors import AMQPError
from grabbit.frames import Method
from grabbit.methods.common import CloseMethod


class TestCloseMethod(CloseMethod):
	method_class = 0xff42
	method_id = 2

class TestBadMethod(Method):
	method_class = 0xff42
	method_id = 3
	fields = []

class TestError(AMQPError):
	"""A fake error for testing purposes"""
	code = 0xffff


class CloseMethodTests(TestCase):

	def construct_full(self, error=True, method=True):
		"""Shortcut to construct a CloseMethod using the full code, reason, method_class, method_id
		arguments."""
		code, reason, method_class, method_id = 0, '', 0, 0
		if error:
			code, reason = TestError.code, TestError.__doc__
		if method:
			method_class, method_id = TestBadMethod.method_class, TestBadMethod.method_id
		return TestCloseMethod(code, reason, method_class, method_id)

	def construct(self, error=True, method=True):
		"""Shortcut to construct a CloseMethod using the helper error and method arguments."""
		return TestCloseMethod(error = TestError if error else None,
		                       method = TestBadMethod if method else None)

	def test_equality(self):
		"""Test all combinations of having and not having an error and a method,
		and ensure both constructors return equal objects."""
		for error, method in itertools.product([True, False], repeat=2):
			self.assertEqual(self.construct_full(error, method),
			                 self.construct(error, method))

	def test_properties(self):
		close = self.construct()
		self.assertIsInstance(close.error, TestError)
		self.assertEqual(close.error.reason, close.reason)
		self.assertEqual(close.method, TestBadMethod)
		self.assertEqual(close.error.data, {'code': TestError.code, 'method': TestBadMethod})

	def test_no_properties(self):
		close = self.construct(False, False)
		self.assertEqual(close.error, None)
		self.assertEqual(close.method, None)

	def test_raise(self):
		close = self.construct()
		self.assertRaises(TestError, close.raise_error)
