
from grabbit.common import get_all_subclasses

class AMQPError(Exception):
	code = NotImplemented

	@classmethod
	def from_code(cls, code):
		for subcls in get_all_subclasses(cls):
			if subcls.code == code:
				return subcls
		raise ValueError("No known subclass for code: {!r}".format(code))

	def __str__(self):
		s = "{cls.__name__}: {cls.__doc__}".format(cls=type(self))
		if self.args:
			s += " ({})".format(', '.join(map(repr, self.args)))

class ChannelError(AMQPError):
	"""Class of errors which abort the channel"""

class ConnectionError(AMQPError):
	"""Class of errors which abort the connection"""


class ContentTooLarge(ChannelError):
	"""Server rejected content - too large. Try again later."""
	code = 311
class NoRoute(ChannelError):
	"""Mandatory flag set and message cannot be routed to a queue"""
	code = 312
class NoConsumers(ChannelError):
	"""Immediate flag set and no immediate delivery possible"""
	code = 313
class ConnectionForced(ConnectionError):
	"""Connection terminated by administrator"""
	code = 320

class InvalidPath(ConnectionError):
	"""Unknown virtual host"""
	code = 402
class AccessRefused(ChannelError):
	"""Client does not have permission to access this resource"""
	code = 403
class NotFound(ChannelError):
	"""Resource does not exist"""
	code = 404
class ResourceLocked(ChannelError):
	"""Resouce is unavailable as another client is using it"""
	code = 405
class PreconditionFailed(ChannelError):
	"""Method is not allowed as some precondition has failed"""
	code = 406

class FrameError(ConnectionError):
	"""Malformed frame received"""
	code = 501
class SyntaxError(ConnectionError):
	"""Frame contained illegal value"""
	code = 502
class CommandInvalid(ConnectionError):
	"""Client sent invalid sequence of frames"""
	code = 503
class InvalidChannelError(ConnectionError):
	# Note: In the spec, this is called a "channel-error"
	"""Given channel is not open"""
	code = 504
class UnexpectedFrame(ConnectionError):
	"""Peer sent a frame that was not expected"""
	# sorry, I have no idea what this actually means either
	code = 505
class ResourceError(ConnectionError):
	"""Server out of resource"""
	code = 506
class NotAllowed(ConnectionError):
	"""Client attempted to do something prohibited by the server"""
	# It is unclear what the difference is between this and AccessRefused
	code = 530
class NotImplemented(ConnectionError):
	"""Server does not implement this functionality"""
	code = 540
class InternalError(ConnectionError):
	"""Server suffered an internal error"""
	code = 541
