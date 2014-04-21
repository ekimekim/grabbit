
from grabbit.frames import Method, FieldTable, ShortString, LongString, Octet

from common import CloseMethod


CLASS_ID = 10

class ConnectionMethod(Method):
	method_class = CLASS_ID


class StartOk(ConnectionMethod):
	"""Response to Start, containing various client settings
	The chosen security mechanism defines the payload in security_response,
		as well as any further Secure/SecureOk methods.
	The chosen locale affects any returned human-readable text, such as error messages.
	"""
	method_id = 11
	fields = [
		('client_properties', FieldTable),
		('security_mechanism', ShortString),
		('security_response', LongString),
		('locale', ShortString),
	]

class Start(ConnectionMethod):
	"""Begin connection negotiation, sent by server.
	If client does not support requested version, it must immediately close the connection.
	Both security_mechanisms and locales should have a value selected and returned in StartOk.
	"""
	method_id = 10
	response = StartOk
	fields = [
		('version_major', Octet),
		('version_minor', Octet),
		('server_properties', FieldTable),
		('_security_mechanisms', LongString),
		('_locales', LongString),
	]
	@property
	def version(self):
		return self.version_major.value, self.version_minor.value
	@property
	def security_mechanisms(self):
		return self._security_mechanisms.split(' ')
	@property
	def locales(self):
		return self._locales.split(' ')

class SecureOk(ConnectionMethod):
	"""Security response, returned by client. Contents are defined by chosen security mechanism."""
	method_id = 21
	fields = [('response', LongString)]

class Secure(ConnectionMethod):
	"""Security challenge, sent by server. Contents are defined by chosen security mechanism."""
	method_id = 20
	response = SecureOk
	fields = [('challenge', LongString)]

class TuneOk(ConnectionMethod):
	"""Confirm tuning parameters, returned by client.
	See Tune for details.
	The client may return different values than received in Tune, but they must be
	less than the values given in Tune (unless the Tune value was 0, ie. no limit).
	Note: As far as I can tell, no such rule is defined for heartbeat_delay.
	      The allowed values of heartbeat_delay are thus unknown - it is safest to use either the exact
	      value given in Tune, or 0 to disable heartbeat.
	"""
	method_id = 31
	fields = [
		('channel_max', Short),
		('frame_size_max', Long),
		('heartbeat_delay', Short),
	]

class Tune(ConnectionMethod):
	"""Propose tuning parameters, sent by server:
		channel_max: Highest channel number that can be opened.
		             0 means no limit (except the limit implied by the data type).
		frame_size_max: Maximum size for a whole frame, including header and end-of-frame byte.
		                0 means no limit, though the server may still reject if out of resources.
		heartbeat_delay: Expected delay in seconds between heartbeat frames. Server will drop connections
		                 on which no frame is recieved in double this time. 0 means heartbeats are disabled.
	"""
	method_id = 30
	response = TuneOk
	fields = [
		('channel_max', Short),
		('frame_size_max', Long),
		('heartbeat_delay', Short),
	]

class OpenOk(ConnectionMethod):
	"""Connection is ready"""
	method_id = 41
	fields = [('reserved', ShortString)]

class Open(ConnectionMethod):
	"""Open the new connection with given virtual host, sent by client"""
	method_id = 40
	response = OpenOk
	fields = [
		('virtual_host', ShortString),
		('reserved1', ShortString),
		('reserved2', Bits('reserved')),
	]

class CloseOk(ConnectionMethod):
	"""Confirm connection gracefully closed"""
	method_id = 51
	fields = []

class Close(CloseMethod, ConnectionMethod):
	"""Close connection gracefully.
	After sending a Close, all subsequent methods should be ignored (except Close and CloseOk).
	A received Close should be responded to with a CloseOk even if a Close has been sent.
	"""
	method = 50
	response = CloseOk

