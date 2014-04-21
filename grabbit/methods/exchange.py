
from grabbit.frames import Method


CLASS_ID = 40

class ExchangeMethod(Method):
	method_class = CLASS_ID


class DeclareOk(ExchangeMethod):
	"""Confirms an exchange has been declared successfully"""
	method_id = 11
	fields = []

class Declare(ExchangeMethod):
	"""Create a new exchange if it doesn't already exist.
	Args:
		name: Exchange name, limited to characters: a-z A-Z 0-9 _ . : -
		type: Exhange type. Rabbit supports 'direct', 'fanout', 'topic', 'headers'
		passive: Do not create the exchange if it doesn't exist (raise a NotFound instead)
		durable: Whether exchange needs to persist across a broker restart
		autodelete: Automatically delete exchange when the last queue unbinds from it
		internal: Exchange cannot be published to (instead it should bind to other exchanges)
	Some special error cases:
		PreconditionFailed: Name contained illegal characters,
		                    or exchange already exists with differing attributes
		CommandInvalid: Bad exchange type
	Other notes:
		Flags 3 and 4 (autodelete and internal) are rabbitmq-specific.
		They are referred to in the docs as 'reserved-2' and 'reserved-3'.
	"""
	method_id = 10
	response = DeclareOk
	fields = [
		('reserved', Short),
		('name', ShortString),
		('type', ShortString),
		('flags', Bits('passive', 'durable', 'autodelete', 'internal', 'nowait')),
		('arguments', FieldTable),
	]

class DeleteOk(ExchangeMethod):
	"""Confirms an exchange was deleted successfully"""
	method_id = 21
	fields = []

class Delete(ExchangeMethod):
	"""Delete an exchange (which also unbinds all queues)
	If if_unused is True, only delete if no bindings present.
	(otherwise raise PreconditionFailed)
	"""
	method_id = 20
	response = DeleteOk
	fields = [
		('reserved', Short),
		('name', ShortString),
		('flags', Bits('if_unused', 'nowait')),
	]

class BindOk(ExchangeMethod):
	"""Confirms an exchange was bound successfully"""
	method_id = 31
	fields = []

class Bind(ExchangeMethod):
	"""Binds destination exchange to source exchange with given routing_key.
	This acts like a queue binding, in that matching messages published to source
	will then also get published to dest.
	Note this is rabbitmq specific as AMQP 0.9.1 officially removed exchange bindings.
	"""
	method_id = 30
	response = BindOk
	fields = [
		('reserved', Short),
		('destination', ShortString),
		('source', ShortString),
		('routing_key', ShortString),
		('flags', Bits('nowait')),
		('arguments', FieldTable),
	]
