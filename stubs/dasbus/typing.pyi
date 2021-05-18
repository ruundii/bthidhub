from typing import Tuple, Dict, List, NewType, IO, TypeVar

_T = TypeVar("_T")

Bool = bool
Double = float
Str = str
Int = int

Byte = NewType("Byte", int)
Int16 = NewType("Int16", int)
UInt16 = NewType("UInt16", int)
Int32 = NewType("Int32", int)
UInt32 = NewType("UInt32", int)
Int64 = NewType("Int64", int)
UInt64 = NewType("UInt64", int)

File = IO

ObjPath = NewType('ObjPath', str)


class Variant: ...


def unwrap_variant(variant: Variant) -> str: ...
