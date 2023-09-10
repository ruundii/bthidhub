# Copyright (c) 2020 ruundii. All rights reserved.

from typing import Optional

class HIDMessageFilter:
    def filter_message_to_host(self, msg: bytes) -> Optional[bytes]:
        if len(msg) == 8:
            return b'\xa1\x01' + msg

        return b'\xa1' + msg


    def filter_message_from_host(self, msg: bytes) -> Optional[bytes]:
        return msg[1:]
