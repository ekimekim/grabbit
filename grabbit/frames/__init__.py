
"""
Low-level library for working with the frame protocol.
Used to implement methods and pack content. You shouldn't ever need to touch this directly.

All frame data has the superclass DataType. All data can be packed into a string of bytes with .pack().
This operation can be reversed with .unpack(), which returns (data, trailing bytes).

In most circumstances, you will want to be sending and recieving whole Frames at a time.
All other data types are generally sub-fields of Frame, or sub-fields of those sub-fields, etc.

For more information on the limitations of what python objects can be sent (and how they are converted
by default), see fieldtable.

A summary of modules:
	common: Helper functions
	datatypes: Primitive types and simple composite types (eg. Sequence)
	frame: Frames represent the highest-level type. Whole frames are sent and received at a time.
	method: Superclass for the implementation of methods
	properties, fieldtable: Specialised composite structures
"""

from common import Incomplete
from fieldtable import FieldTable
from frame import Frame
from method import Method
from properties import Properties, PropertyBit

from datatypes import DataType, Octet, Short, Long, LongLong, Timestamp, ShortString, LongString, Bits, Sequence
