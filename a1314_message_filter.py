# Copyright (c) 2020 ruundii. All rights reserved.

from typing import Optional

from hid_message_filter import HIDMessageFilter

MODIFIER_MASK_A1314_FN = 0x10
MODIFIER_MASK_A1314_EJECT = 0x08
MODIFIER_MASK_LEFT_CONTROL = 0x01
MODIFIER_MASK_LEFT_SHIFT = 0x02
MODIFIER_MASK_LEFT_ALT = 0x04
MODIFIER_MASK_LEFT_GUI_OR_CMD = 0x08
MODIFIER_MASK_A1314_RIGHT_CMD = 0x80
MODIFIER_MASK_RIGHT_ALT = 0x40
MODIFIER_MASK_RIGHT_SHIFT = 0x20

KEY_APPLICATION = 0x65

KEY_DELETE_FORWARD = 0x4c
KEY_LEFT_ARROW = 0x50
KEY_RIGHT_ARROW = 0x4f
KEY_DOWN_ARROW = 0x51
KEY_UP_ARROW = 0x52
KEY_HOME = 0x4a
KEY_END = 0x4d
KEY_PGUP = 0x4b
KEY_PGDN = 0x4e
KEY_PRINT_SCREEN = 0x46

FN_SUBSTITUTES = {
    KEY_LEFT_ARROW:KEY_HOME,
    KEY_RIGHT_ARROW: KEY_END,
    KEY_DOWN_ARROW: KEY_PGDN,
    KEY_UP_ARROW: KEY_PGUP,
}

class A1314MessageFilter(HIDMessageFilter):
    #LeftControl: 0 | LeftShift: 0 | LeftAlt: 0 | Left GUI: 0 | RightControl: 0 | RightShift: 0 | RightAlt: 0 | Right GUI: 0 | # |Keyboard ['00', '00', '00', '00', '00', '00']


    def __init__(self) -> None:
        self.is_fn_pressed = False
        self.is_eject_pressed = False
        self.last_regular_report = bytearray(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00')

    def filter_message_to_host(self, msg: bytes) -> Optional[bytes]:
        if len(msg) < 1:
            return None

        result_report = bytearray(msg)
        if msg[0] == 0x11:
            result_report = self.last_regular_report

            #special key report
            self.is_fn_pressed = (msg[1] & MODIFIER_MASK_A1314_FN) != 0

            old_eject_state = self.is_eject_pressed
            self.is_eject_pressed = (msg[1] & MODIFIER_MASK_A1314_EJECT) != 0
            if(old_eject_state and not self.is_eject_pressed):
                #eject unpressed - remove delete forward key from report
                for i in range(3,9):
                    if result_report[i] == KEY_DELETE_FORWARD:
                        for j in range (i+1,9):
                            result_report[j-1]=result_report[j]
                        result_report[8]=0
                        break
            if (not old_eject_state and self.is_eject_pressed):
                # eject pressed
                for i in range(3,9):
                    if result_report[i] == 0:
                        result_report[i] = KEY_DELETE_FORWARD
                        break

        elif msg[0] == 0x01:
            #normal key report
            modifiers = result_report[1]
            result_report[1] = 0 # reset modifiers

            if(modifiers & MODIFIER_MASK_LEFT_ALT): # left alt is pressed
                result_report[1] = result_report[1] | MODIFIER_MASK_LEFT_GUI_OR_CMD

            if(modifiers & MODIFIER_MASK_LEFT_GUI_OR_CMD): # left cmd is pressed
                result_report[1] = result_report[1] | MODIFIER_MASK_LEFT_ALT

            if(modifiers & MODIFIER_MASK_A1314_RIGHT_CMD): # right cmd is pressed
                result_report[1] = result_report[1] | MODIFIER_MASK_RIGHT_ALT

            if(modifiers & MODIFIER_MASK_LEFT_SHIFT): # left shift is pressed
                result_report[1] = result_report[1] | MODIFIER_MASK_LEFT_SHIFT

            if(modifiers & MODIFIER_MASK_RIGHT_SHIFT): # right shift is pressed
                result_report[1] = result_report[1] | MODIFIER_MASK_RIGHT_SHIFT

            if(modifiers & MODIFIER_MASK_RIGHT_ALT): # right alt is pressed - send application
                for i in range(3,9):
                    if result_report[i] == 0:
                        result_report[i] = KEY_APPLICATION
                        break

            my_fn_pressed = modifiers & MODIFIER_MASK_LEFT_CONTROL # left control is pressed - behave like fn button
            if my_fn_pressed:
                #process combinations
                for i in range(3,9):
                    if result_report[i] == 0:
                        break
                    if result_report[i] in FN_SUBSTITUTES:
                        result_report[i] = FN_SUBSTITUTES[result_report[i]]


        # set the fn state in output report
        result_report[1] = (result_report[1] | MODIFIER_MASK_LEFT_CONTROL) if self.is_fn_pressed else (
                    result_report[1] & ~MODIFIER_MASK_LEFT_CONTROL)

        #print(bytes(result_report).hex())
        if result_report == b'\x01\x05\x00\x2b\x00\x00\x00\x00\x00':
            print("host switch")
            return b'\xff'

        self.last_regular_report = result_report
        return b'\xa1'+bytes(result_report)

    def filter_message_from_host(self, msg: bytes) -> bytes:
        return msg[1:]
