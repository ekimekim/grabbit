
from unittest import TestCase

from gevent.queue import Empty

from grabbit import common


class CommonHelperTests(TestCase):

	def test_get_all_subclasses(self):
		class A(object): pass
		class B(A): pass
		class C(A): pass
		class D(C): pass
		self.assertEquals(common.get_all_subclasses(A), {B, C, D})
		self.assertEquals(common.get_all_subclasses(B), set())
		self.assertEquals(common.get_all_subclasses(C), {D})

	def test_classproperty(self):
		class Foo(object):
			@common.classproperty
			def bar(cls):
				return cls
		self.assertIs(Foo.bar, Foo)
		self.assertIs(Foo().bar, Foo)


class ChunkedPriorityQueueTests(TestCase):

	def test_basic(self):
		queue = common.ChunkedPriorityQueue()
		queue.put((1, 'foo'))
		queue.put((1, 'bar'))
		self.assertEquals(queue.get(), (1, 'foo'))
		queue.put((0, 'baz'))
		self.assertEquals(queue.get(), (0, 'baz'))
		self.assertEquals(queue.get(), (1, 'bar'))

	def test_limit(self):
		queue = common.ChunkedPriorityQueue()
		queue.put((0, 'foo'))
		queue.put((1, 'bar'))
		queue.set_limit(0)
		self.assertEquals(queue.get(), (0, 'foo'))
		self.assertRaises(Empty, lambda: queue.get(block=False))
		queue.set_limit(None)
		self.assertEquals(queue.get(), (1, 'bar'))

	def test_limit_context(self):
		queue = common.ChunkedPriorityQueue()
		queue.put((0, 'foo'))
		queue.put((1, 'bar'))
		with queue.limit_to(0):
			with queue.limit_to(-1):
				self.assertRaises(Empty, lambda: queue.get(block=False))
			self.assertEquals(queue.get(), (0, 'foo'))
			self.assertRaises(Empty, lambda: queue.get(block=False))
		self.assertEquals(queue.get(), (1, 'bar'))
