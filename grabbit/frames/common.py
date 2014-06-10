

class Incomplete(Exception):
	"""Indicates the data given was incomplete."""


def eat(data, length):
	"""Helper method: Split (length) bytes from data and return it along with remainder,
	or raise Incomplete if not long enough."""
	if len(data) < length:
		raise Incomplete
	return data[:length], data[length:]
