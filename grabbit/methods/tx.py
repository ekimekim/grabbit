
from grabbit.frames import Method


CLASS_ID = 90

class TxMethod(Method):
	method_class = CLASS_ID
	fields = []

class SelectOk(TxMethod):
	"""Confirm that channel is now in transaction mode.
	Subsequent actions on the channel are part of the first commit."""
	method_id = 11

class Select(TxMethod):
	"""Put channel into transaction mode, allowing the use of later Commit and Rollback methods.
	"""
	method_id = 10
	response = SelectOk

class CommitOk(TxMethod):
	"""Confirm the transaction was successful, automatically starting a new transaction."""
	method_id = 21

class Commit(TxMethod):
	"""Commit all basic.Publish and basic.Ack actions on this channel since the last Commit, Rollback or Select.
	Either all the actions will succeed, or none of them will (eg. on a broker failure or exception).
	"""
	method_id = 20
	response = CommitOk

class RollbackOk(TxMethod):
	"""Confirm transaction rollback was successful, automatically starting a new transaction."""
	method_id = 31

class Rollback(TxMethod):
	"""Roll back current transaction, discarding all basic.Publish and basic.Ack actions on this channel
	since the last Commit, Rollback or Select.
	"""
	method_id = 30
	response = RollbackOk
