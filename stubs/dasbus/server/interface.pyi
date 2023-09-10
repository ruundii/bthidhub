from typing import Callable, Tuple, Type, TypeVar

_T = TypeVar("_T", bound=Type[object])

def dbus_interface(interface_name: str, namespace: Tuple[str, ...] = ...) -> Callable[[_T], _T]: ...
