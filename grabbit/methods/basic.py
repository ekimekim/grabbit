
from grabbit.frames import Method, Properties


CLASS_ID = 60

class BasicMethod(Method):
	method_class = CLASS_ID

class BasicProperties(Properties):
	"""Properties of a Basic message.
	The following fields have special behaviour or implied meaning:
		content_type: MIME type
		content_encoding: MIME encoding
		headers: The values used in here can be used in a "headers" type exchange,
		         but are otherwise application-defined.
		delivery_mode: Must be 2 for persistent messages, 1 otherwise.
		priority: Message priority. Higher-priority messages "jump" to the front of the queue.
		expiration: TODO ???
		reserved: Do not use
	All other fields are available for application-specific use.
	"""
	method_class = CLASS_ID
	property_map = [
		('content_type', ShortString),
		('content_encoding', ShortString),
		('headers', FieldTable),
		('delivery_mode', Octet),
		('priority', Octet),
		('correlation_id', ShortString),
		('reply_to', ShortString),
		('expiration', ShortString),
		('message_id', ShortString),
		('timestamp', Timestamp),
		('type', ShortString),
		('user_id', ShortString),
		('app_id', ShortString),
		('reserved', ShortString),
	]

class QosOk(BasicMethod):
	"""Qos was successfully applied"""
	method_id = 11
	fields = []

class Qos(BasicMethod):
	"""Specify a quality of service
	Args:
		prefetch_size: Server should send more messages until next message would put total size (in bytes)
		               of pending messages over prefetch_size. A message will always be sent if no messages
		               are pending. Set to 0 for "no limit".
		prefetch_count: Server should send up to this many pending messages,
		                assuming prefetch_size also allows it.
		global: If this flag is false, these settings are only applied to new consumers on this channel.
		        Otherwise, it applies to the channel as a whole.
		        Note this RabbitMQ behaviour differs from the spec, where the global flag switches between
		        per-channel and connection-wide settings.
	"""
	method_id = 10
	response = QosOk
	fields = [
		('prefetch_size', Long),
		('prefetch_count', Short),
		(None, Bits('global')),
	]

class ConsumeOk(BasicMethod):
	"""New consumer was successfully created with this consumer_tag"""
	method_id = 21
	fields = [('consumer_tag', ShortString)]

class Consume(BasicMethod):
	"""Create a new consumer for a queue.
	For as long as this consumer is active, messages from the queue will be sent to the client
	with a Deliver method.
	Args:
		queue: The name of the queue to consume
		consumer_tag: String to tag incoming messages from this consumer with. Leave empty to let
		              the server generate one (this is reccomended).
		no_local: If True, messages originating from this connection will not be consumed.
		no_ack: If True, consumer's messages are considered automatically acked after being recieved.
		exclusive: If True, enforce that this consumer is the only consumer for this queue.
	RabbitMQ Extension arguments (these go in the "arguments" field):
		"x-priority": Set to an integer value. Can be positive or negative, and if unspecified is considered
		              to default to 0. Consumer priority controls which consumer of a queue will recieve
		              a message. A consumer of higher priority will be delivered to unless it is busy
		              (eg. already recieving a message, prefetch limit reached). Consumers of equal priority
		              are allocated to in round-robin.
	Note that consumers are channel-local, and are automatically cancelled when the channel is closed.
	Some possible errors:
		NotAllowed: Tag already in use
		AccessRefused: Exclusive requested and queue already has consumer
	"""
	method_id = 20
	response = ConsumeOk
	fields = [
		(None, Short),
		('queue', ShortString),
		('consumer_tag', ShortString),
		(None, Bits('no_local', 'no_ack', 'exclusive', 'no_wait')),
		('arguments', FieldTable),
	]

class CancelOk(BasicMethod):
	"""Confirm that a consumer has been cancelled, and no further messages will arrive."""
	method_id = 31
	fields = [('consumer_tag', ShortString)]

class Cancel(BasicMethod):
	"""Cancel a consumer.
	Note that the server may send a Cancel to the client to indicate an unexpected consumer cancel,
	such as when the queue is deleted or due to clustered failover.
	"""
	method_id = 30
	response = CancelOk
	fields = [
		('consumer_tag', ShortString),
		(None, Bits('no_wait')),
	]

class Publish(BasicMethod):
	"""Publish the following content (a message) to an exchange.
	Args:
		exchange: Name of the exchange to publish to.
		routing_key: Routing key for the message
		mandatory: If True, Return the message if it cannot be routed to any queue.
		immediate: If True, Return the message if it cannot be delivered to a consumer immediately.
	"""
	method_id = 40
	has_content = True
	fields = [
		(None, Short),
		('exchange', ShortString),
		('routing_key', ShortString),
		(None, Bits('mandatory', 'immediate')),
	]

class Return(BasicMethod):
	"""Return a message that could not be delivered. This is delievered from server to client when a publish
	is rejected due to mandatory or immediate flags, and is followed by the message content.
	Contains an error code as well as a human readable text reason.
	"""
	method_id = 50
	has_content = True
	fields = [
		("code", Short),
		("reason", ShortString),
		("exchange", ShortString),
		("routing_key", ShortString),
	]

class Deliver(BasicMethod):
	"""Deliver a message to a comsumer.
	The consumer_tag matches the consumer that wanted the message.
	The delivery_tag is channel-local and identifies this delivery for later ack/nack.
	The redelivered flag may be set if the message was previously delivered to this or another client.
	"""
	method_id = 60
	has_content = True
	fields = [
		('consumer_tag', ShortString),
		('delivery_tag', LongLong),
		(None, Bits('redelivered')),
		('exchange', ShortString),
		('routing_key', ShortString),
	]

class GetOk(BasicMethod):
	"""Report delivery of a single message requested by a Get call."""
	method_id = 71
	has_content = True
	fields = [
		('delivery_tag', LongLong),
		(None, Bits('redelivered')),
		('exchange', ShortString),
		('routing_key', ShortString),
		('message_count', Long),
	]

class GetEmpty(BasicMethod):
	"""Report that no messages were available in response to a Get call."""
	method_id = 72
	fields = [(None, ShortString)]

class Get(BasicMethod):
	"""Request delivery of a single message from a queue.
	Response is a GetOk with content if a message is available, GetEmpty otherwise.
	"""
	method_id = 70
	response = (GetOk, GetEmpty)
	fields = [
		(None, Short),
		('queue', ShortString),
		(None, Bits('no_ack')),
	]

class Ack(BasicMethod):
	"""Acknowledge messages as processed. If messages are not acknowledged within reasonable time,
	they may be re-delivered.
	As a RabbitMQ extension, a channel in confirm mode will send Acks to the client for published messages.
	Args:
		delivery_tag: The meaning of this changes depending on the multiple flag
		multiple: If False, only the message refered to by the delivery_tag exactly is acked.
		          If True, acks all un-acked messages with a delivery tag <= the given value.
		          (This effectively means all messages recieved before the specified message,
		          plus the message itself). If delivery_tag is 0 all un-acked messages are acked.
	Some specific errors:
		PreconditonFailed: Given delivery tag did not refer to an un-acked message.
	"""
	method_id = 80
	fields = [
		('delivery_tag', LongLong),
		(None, Bits('multiple')),
	]

class Reject(BasicMethod):
	"""Reject a partially recieved or fully delivered message.
	If requeue is set, the server will attempt to deliver this message to an alternate consumer.
	Otherwise it is dropped or sent to a dead letter queue."""
	method_id = 90
	fields = [
		('delivery_tag', LongLong),
		(None, Bits('requeue')),
	]

class RecoverAsync(BasicMethod):
	"""Request re-delivery of all un-acked messages on this channel.
	If requeue is True, messages will attempt to be delivered to alternate consumers.
	Otherwise:
		Messages will always be redelivered to the same consumer.
		Messages delivered via Get will not be re-delivered.
		Consumers that have since been cancelled WILL still re-recieve the message.
	This method is deprecated in favour of Recover and RecoverOk.
	"""
	method_id = 100
	fields = [(None, Bits('requeue'))]

class RecoverOk(BasicMethod):
	"""Confirm reciept of a Recover method"""
	method_id = 111
	fields = []

class Recover(BasicMethod):
	"""Syncronous version of RecoverAsync"""
	method_id = 110
	response = RecoverOk
	fields = [(None, Bits('requeue'))]

class Nack(BasicMethod):
	"""RabbitMQ extension that acts like Reject, but has fields similar to Ack.
	Nacked messages obey the same semantics as Rejected messages.
	It is also sent by the server to reject messages when in confirm mode.
	The client should re-send any such rejected messages.
	Args:
		delivery_tag, multiple: See Ack
		requeue: See Reject
	Note that a Nack with multiple=False is functionally equivilent to a Reject.
	"""
	method_id = 120
	fields = [
		('delivery_tag', LongLong),
		(None, Bits('multiple', 'requeue')),
	]
