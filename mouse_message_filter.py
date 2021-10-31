# Copyright (c) 2020 ruundii. All rights reserved.
#
from hid_message_filter import HIDMessageFilter

#default mouse filter

# first 16 bits are flags for buttons. 01 is left button, 02 is right, 04 is scroll
# second 16 bits are X -32767 to 32767
# third 16 bits are Y -32767 to 32767
# then 8 bits of wheel -127 to 127


# from the default sdp record

# 0x05, 0x01,                    // Usage Page (Generic Desktop)        0
# 0x09, 0x02,                    // Usage (Mouse)                       2
# 0xa1, 0x01,                    // Collection (Application)            4
# 0x09, 0x01,                    //  Usage (Pointer)                    6
# 0xa1, 0x00,                    //  Collection (Physical)              8
# 0x05, 0x09,                    //   Usage Page (Button)               10
# 0x19, 0x01,                    //   Usage Minimum (1)                 12
# 0x29, 0x10,                    //   Usage Maximum (16)                14
# 0x15, 0x00,                    //   Logical Minimum (0)               16
# 0x25, 0x01,                    //   Logical Maximum (1)               18
# 0x95, 0x10,                    //   Report Count (16)                 20
# 0x75, 0x01,                    //   Report Size (1)                   22
# 0x81, 0x02,                    //   Input (Data,Var,Abs)              24
# 0x05, 0x01,                    //   Usage Page (Generic Desktop)      26
# 0x16, 0x01, 0x80,              //   Logical Minimum (-32767)          28
# 0x26, 0xff, 0x7f,              //   Logical Maximum (32767)           31
# 0x75, 0x10,                    //   Report Size (16)                  34
# 0x95, 0x02,                    //   Report Count (2)                  36
# 0x09, 0x30,                    //   Usage (X)                         38
# 0x09, 0x31,                    //   Usage (Y)                         40
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              42
# 0x15, 0x81,                    //   Logical Minimum (-127)            44
# 0x25, 0x7f,                    //   Logical Maximum (127)             46
# 0x75, 0x08,                    //   Report Size (8)                   48
# 0x95, 0x01,                    //   Report Count (1)                  50
# 0x09, 0x38,                    //   Usage (Wheel)                     52
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              54
# 0x05, 0x0c,                    //   Usage Page (Consumer Devices)     56
# 0x0a, 0x38, 0x02,              //   Usage (AC Pan)                    58
# 0x95, 0x01,                    //   Report Count (1)                  61
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              63
# 0xc0,                          //  End Collection                     65
# 0xc0,                          // End Collection                      66


class MouseMessageFilter(HIDMessageFilter):
    def __init__(self):
        self.message_size = 7

    def filter_message_to_host(self, msg):
        if len(msg) != self.message_size:
            return None
        msg = b'\xa1\x03' + self.get_buttons_flags(msg) + self.get_x(msg) + self.get_y(msg) + self.get_wheel(msg)
        return msg

    def get_buttons_flags(self, msg):
        return msg[0:2]

    def get_x(self, msg):
        return msg[2:4]

    def get_y(self, msg):
        return msg[4:6]

    def get_wheel(self, msg):
        return msg[6:7]

    def filter_message_from_host(self, msg):
        return None
