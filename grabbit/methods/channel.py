
from grabbit.frames import Method, Bits, LongString, ShortString

from common import CloseMethod


CLASS_ID = 20

class ChannelMethod(Method):
	method_class = CLASS_ID


class OpenOk(ChannelMethod):
	"""Server response indicating channel is now able to be used"""
	method_id = 11
	fields = [(None, LongString)]

class Open(ChannelMethod):
	"""First method on a new channel. Client request to open this channel."""
	method_id = 10
	response = OpenOk
	fields = [(None, ShortString)]

# NOTE: rabbitmq does not support the Flow method
# It is included here only for completeness.
class FlowOk(ChannelMethod):
	"""Indicates flow control was responded to.
	rabbitmq does not support this method."""
	method_id = 21
	fields = [(None, Bits('active'))]

class Flow(ChannelMethod):
	"""Requests flow control action.
	rabbitmq does not support this method."""
	method_id = 20
	response = FlowOk
	fields = [(None, Bits('active'))]

class CloseOk(ChannelMethod):
	"""Confirms channel as closed."""
	method_id = 41
	fields = []

class Close(CloseMethod, ChannelMethod):
	"""Close channel.
	After sending a Close, all subsequent methods should be ignored (except Close and CloseOk).
	A received Close should be responded to with a CloseOk even if a Close has been sent.
	"""
	method = 40
	response = CloseOk

