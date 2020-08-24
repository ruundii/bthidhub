# Copyright (c) 2020 ruundii. All rights reserved.

class HIDMessageFilter:

    def filter_message_to_host(self, msg):
        if len(msg) < 7:
            return None
        msg = b'\xa1\x01' + msg
        return msg


    def filter_message_from_host(self, msg):
        return msg[1:]