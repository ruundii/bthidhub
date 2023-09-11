from typing import Tuple, Dict, Generic, List, NewType, IO, TypeVar

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

ObjPath = NewType('ObjPath', str)


class Variant(Generic[_T]):
    def get_type_string(self) -> str: ...
    def get_child_value(self, i: int) -> object: ...
    def get_variant(self) -> _T: ...
    def unpack(self) -> _T: ...


def unwrap_variant(variant: Variant[_T]) -> _T: ...
