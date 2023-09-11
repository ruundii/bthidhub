from typing import Callable, TypeVar

_T = TypeVar("_T", bound=type[object])

def dbus_interface(interface_name: str, namespace: tuple[str, ...] = ...) -> Callable[[_T], _T]: ...
