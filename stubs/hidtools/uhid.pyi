from typing import Iterable, Tuple

class UHIDDevice:
    info: Tuple[int, int, int]
    name: str
    phys: str
    rdesc: bytes

    def call_input_event(self, data: Iterable[int]) -> None: ...
    def create_kernel_device(self) -> None: ...
    def destroy(self) -> None: ...
