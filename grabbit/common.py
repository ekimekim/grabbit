

def get_all_subclasses(cls):
	"""Recursive method to find all decendents of cls, ie.
	it's subclasses, subclasses of those classes, etc.
	Returns a set.
	"""
	subs = set(cls.__subclasses__())
	subs_of_subs = [get_all_subclasses(subcls) for subcls in subs]
	return subs.union(*subs_of_subs)


class classproperty(object):
	"""Acts like a stdlib @property, but the wrapped get function is a class method.
	For simplicity, only read-only properties are implemented."""

	def __init__(self, fn):
		self.fn = fn

	def __get__(self, instance, cls):
		return self.fn(cls)
