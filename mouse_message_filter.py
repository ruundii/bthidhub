# Copyright (c) 2020 ruundii. All rights reserved.
#

from typing import Optional

from hid_message_filter import HIDMessageFilter

class MouseMessageFilter(HIDMessageFilter):
    def filter_message_to_host(self, msg: bytes) -> Optional[bytes]:
        if len(msg) != 7:
            return None
        return b'\xa1\x03' + msg

    def filter_message_from_host(self, msg: bytes) -> None:
        return None
