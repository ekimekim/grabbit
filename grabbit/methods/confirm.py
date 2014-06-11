
"""Note that the confirm method class is a RabbitMQ extension."""

from grabbit.frames import Method, Bits


CLASS_ID = 85

class ConfirmMethod(Method):
	method_class = CLASS_ID

class SelectOk(ConfirmMethod):
	"""Confirm that channel was put into confirm mode, and publish sequence number has been started at 1"""
	method_id = 11
	fields = []

class Select(ConfirmMethod):
	"""Put channel into confirm mode, instructing the broker to send a basic.Ack for published messages.
	The "delivery_tag" of these outgoing messages begins at 1, and increments with every message.
	"""
	method_id = 10
	fields = [(None, Bits('no_wait'))]
