import asyncio
from typing import Dict, List, NamedTuple

from . import ecodes


class DeviceInfo(NamedTuple):
    bustype: int
    product: int
    vendor: int
    version: int


class InputEvent:
    code: int
    type: int
    value: int

    def timestamp(self) -> float: ...


class ReadIterator:
    def __aiter__(self) -> ReadIterator: ...
    def __anext__(self) -> asyncio.Future[InputEvent]: ...


class InputDevice:
    info: DeviceInfo
    name: str
    path: str
    phys: str

    def __init__(self, dev: str): ...
    def async_read_loop(self) -> ReadIterator: ...
    def capabilities(self, verbose: bool = ..., absinfo: bool = ...) -> Dict[int, List[int]]: ...
    def close(self) -> None: ...
    def grab(self) -> None: ...
    def ungrab(self) -> None: ...


def categorize(event: InputEvent) -> InputEvent: ...
def list_devices(input_device_dir: str = ...) -> List[str]: ...
