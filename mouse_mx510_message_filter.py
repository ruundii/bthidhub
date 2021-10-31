# Copyright (c) 2020 ruundii. All rights reserved.


from hid_message_filter import HIDMessageFilter
from mouse_message_filter import MouseMessageFilter
from bitarray import bitarray
from bitarray.util import ba2int


# Logitech USB-PS/2 Optical Mouse
# 0x05, 0x01,                    // Usage Page (Generic Desktop)        0
# 0x09, 0x02,                    // Usage (Mouse)                       2
# 0xa1, 0x01,                    // Collection (Application)            4
# 0x09, 0x01,                    //  Usage (Pointer)                    6
# 0xa1, 0x00,                    //  Collection (Physical)              8
# 0x05, 0x09,                    //   Usage Page (Button)               10
# 0x19, 0x01,                    //   Usage Minimum (1)                 12
# 0x29, 0x08,                    //   Usage Maximum (8)                 14
# 0x15, 0x00,                    //   Logical Minimum (0)               16
# 0x25, 0x01,                    //   Logical Maximum (1)               18
# 0x95, 0x08,                    //   Report Count (8)                  20
# 0x75, 0x01,                    //   Report Size (1)                   22
# 0x81, 0x02,                    //   Input (Data,Var,Abs)              24
# 0x95, 0x00,                    //   Report Count (0)                  26
# 0x81, 0x03,                    //   Input (Cnst,Var,Abs)              28
# 0x06, 0x00, 0xff,              //   Usage Page (Vendor Defined Page 1) 30
# 0x09, 0x40,                    //   Usage (Vendor Usage 0x40)         33
# 0x95, 0x02,                    //   Report Count (2)                  35
# 0x75, 0x08,                    //   Report Size (8)                   37
# 0x15, 0x81,                    //   Logical Minimum (-127)            39
# 0x25, 0x7f,                    //   Logical Maximum (127)             41
# 0x81, 0x02,                    //   Input (Data,Var,Abs)              43
# 0x05, 0x01,                    //   Usage Page (Generic Desktop)      45
# 0x09, 0x38,                    //   Usage (Wheel)                     47
# 0x15, 0x81,                    //   Logical Minimum (-127)            49
# 0x25, 0x7f,                    //   Logical Maximum (127)             51
# 0x75, 0x08,                    //   Report Size (8)                   53
# 0x95, 0x01,                    //   Report Count (1)                  55
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              57
# 0x09, 0x30,                    //   Usage (X)                         59
# 0x09, 0x31,                    //   Usage (Y)                         61
# 0x16, 0x01, 0xf8,              //   Logical Minimum (-2047)           63
# 0x26, 0xff, 0x07,              //   Logical Maximum (2047)            66
# 0x75, 0x0c,                    //   Report Size (12)                  69
# 0x95, 0x02,                    //   Report Count (2)                  71
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              73
# 0xc0,                          //  End Collection                     75
# 0xc0,                          // End Collection                      76



class MX510MessageFilter(MouseMessageFilter):
    # first 8 bits are flags for buttons. 01 is left button, 02 is right, 04 is scroll
    # second 16 bits are vendor specific x and y, one byte each
    # then 8 bits of wheel -127 to 127
    # then x and y from  -2047 to 2047, 12 bits each

    def __init__(self):
        self.message_size = 7

    def get_buttons_flags(self, msg):
        return msg[0:1]+b'\x00'

    def get_x(self, msg):
        a = bitarray()
        a.frombytes(msg[4:6])
        return int.to_bytes(ba2int(a[12:16] + a[0:8], signed=True), 2, "little", signed=True)

    def get_y(self, msg):
        a = bitarray()
        a.frombytes(msg[5:7])
        return int.to_bytes(ba2int(a[8:16]+a[0:4],signed=True), 2, "little", signed=True)

    def get_wheel(self, msg):
        return msg[3:4]

