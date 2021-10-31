# Copyright (c) 2020 ruundii. All rights reserved.


from hid_message_filter import HIDMessageFilter
from mouse_message_filter import MouseMessageFilter


# 0x67, 0x05, 0x01, 0x09, 0x02,  // Unit (Mass: Gram, Luminous Intensity: Candela)
# 0xA1, 0x01,        // Collection (Application)
# 0x09, 0x01,        //   Usage (0x01)
# 0xA1, 0x00,        //   Collection (Physical)
# 0x05, 0x09,        //     Usage Page (Button)
# 0x19, 0x01,        //     Usage Minimum (0x01)
# 0x29, 0x10,        //     Usage Maximum (0x10)
# 0x15, 0x00,        //     Logical Minimum (0)
# 0x25, 0x01,        //     Logical Maximum (1)
# 0x95, 0x10,        //     Report Count (16)
# 0x75, 0x01,        //     Report Size (1)
# 0x81, 0x02,        //     Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
# 0x05, 0x01,        //     Usage Page (Generic Desktop Ctrls)
# 0x16, 0x01, 0x80,  //     Logical Minimum (-32767)
# 0x26, 0xFF, 0x7F,  //     Logical Maximum (32767)
# 0x75, 0x10,        //     Report Size (16)
# 0x95, 0x02,        //     Report Count (2)
# 0x09, 0x30,        //     Usage (X)
# 0x09, 0x31,        //     Usage (Y)
# 0x81, 0x06,        //     Input (Data,Var,Rel,No Wrap,Linear,Preferred State,No Null Position)
# 0x15, 0x81,        //     Logical Minimum (-127)
# 0x25, 0x7F,        //     Logical Maximum (127)
# 0x75, 0x08,        //     Report Size (8)
# 0x95, 0x01,        //     Report Count (1)
# 0x09, 0x38,        //     Usage (Wheel)
# 0x81, 0x06,        //     Input (Data,Var,Rel,No Wrap,Linear,Preferred State,No Null Position)
# 0x05, 0x0C,        //     Usage Page (Consumer)
# 0x0A, 0x38, 0x02,  //     Usage (AC Pan)
# 0x95, 0x01,        //     Report Count (1)
# 0x81, 0x06,        //     Input (Data,Var,Rel,No Wrap,Linear,Preferred State,No Null Position)
# 0xC0,              //   End Collection
# 0xC0,              // End Collection
#
# // 68 bytes


class G502MessageFilter(MouseMessageFilter):
    # first 16 bits are flags for buttons. 01 is left button, 02 is right, 04 is scroll
    # second 16 bits are X -32767 to 32767
    # third 16 bits are Y -32767 to 32767
    # then 8 bits of wheel -127 to 127
    # then AC pan

    def __init__(self):
        self.message_size = 8

