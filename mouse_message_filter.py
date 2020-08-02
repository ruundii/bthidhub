# Copyright (c) 2020 ruundii. All rights reserved.
#
from hid_message_filter import HIDMessageFilter

class MouseMessageFilter(HIDMessageFilter):
    def __init__(self):
        pass

    def filter_message_to_host(self, msg):
        if len(msg) != 7:
            return None
        msg = b'\xa1\x03' + msg
        return msg

    def filter_message_from_host(self, msg):
        return None
