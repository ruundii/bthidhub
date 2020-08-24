from evdev import *
from hidtools.uhid import UHIDDevice
import asyncio
from typing import List

CONSUMER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING = {
    ecodes.KEY_NEXTSONG : 0x01, # Usage (Scan Next Track)
    ecodes.KEY_PREVIOUSSONG : 0x02, # Usage (Scan Previous Track)
    ecodes.KEY_STOP : 0x04,  # Usage (Stop)
    ecodes.KEY_PLAYPAUSE : 0x08,  # Usage (Play/Pause)
    ecodes.KEY_MUTE : 0x10,  # Usage (Mute)
    ecodes.KEY_VOLUMEUP : 0x20,  # Usage (Volume Increment)
    ecodes.KEY_VOLUMEDOWN : 0x40,  # Usage (Volume Decrement)
}

MODIFIER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING = {
    ecodes.KEY_LEFTCTRL : 0x01,
    ecodes.KEY_LEFTSHIFT : 0x02,
    ecodes.KEY_LEFTALT : 0x04,
    ecodes.KEY_LEFTMETA : 0x08,
    ecodes.KEY_RIGHTCTRL : 0x10,
    ecodes.KEY_RIGHTSHIFT : 0x20,
    ecodes.KEY_RIGHTALT : 0x40,
    ecodes.KEY_RIGHTMETA: 0x80,
}

#see https://www.usb.org/sites/default/files/hut1_2.pdf
#a bit unsure about US layouts and HID usage 31, now producing 0x32 usage for key_backslash, not sure if 0x31 need to be produced for us backslash. also ecodes.KEY_102ND
NORMAL_KEYS_EVENT_TO_USAGE_FLAG_MAPPING = {
    ecodes.KEY_RESERVED : 0x00,
    ecodes.KEY_A: 0x04,
    ecodes.KEY_B: 0x05,
    ecodes.KEY_C: 0x06,
    ecodes.KEY_D: 0x07,
    ecodes.KEY_E: 0x08,
    ecodes.KEY_F: 0x09,
    ecodes.KEY_G: 0x0A,
    ecodes.KEY_H: 0x0B,
    ecodes.KEY_I: 0x0C,
    ecodes.KEY_J: 0x0D,
    ecodes.KEY_K: 0x0E,
    ecodes.KEY_L: 0x0F,
    ecodes.KEY_M: 0x10,
    ecodes.KEY_N: 0x11,
    ecodes.KEY_O: 0x12,
    ecodes.KEY_P: 0x13,
    ecodes.KEY_Q: 0x14,
    ecodes.KEY_R: 0x15,
    ecodes.KEY_S: 0x16,
    ecodes.KEY_T: 0x17,
    ecodes.KEY_U: 0x18,
    ecodes.KEY_V: 0x19,
    ecodes.KEY_W: 0x1A,
    ecodes.KEY_X: 0x1B,
    ecodes.KEY_Y: 0x1C,
    ecodes.KEY_Z: 0x1D,
    ecodes.KEY_1: 0x1E,
    ecodes.KEY_2: 0x1F,
    ecodes.KEY_3: 0x20,
    ecodes.KEY_4: 0x21,
    ecodes.KEY_5: 0x22,
    ecodes.KEY_6: 0x23,
    ecodes.KEY_7: 0x24,
    ecodes.KEY_8: 0x25,
    ecodes.KEY_9: 0x26,
    ecodes.KEY_0: 0x27,
    ecodes.KEY_ENTER: 0x28,
    ecodes.KEY_ESC: 0x29,
    ecodes.KEY_BACKSPACE: 0x2A,
    ecodes.KEY_TAB: 0x2B,
    ecodes.KEY_SPACE: 0x2C,
    ecodes.KEY_MINUS: 0x2D,
    ecodes.KEY_EQUAL: 0x2E,
    ecodes.KEY_LEFTBRACE: 0x2F,
    ecodes.KEY_RIGHTBRACE: 0x30,
    ecodes.KEY_BACKSLASH: 0x32,
    ecodes.KEY_SEMICOLON: 0x33,
    ecodes.KEY_APOSTROPHE: 0x34,
    ecodes.KEY_GRAVE: 0x35,
    ecodes.KEY_COMMA: 0x36,
    ecodes.KEY_DOT: 0x37,
    ecodes.KEY_SLASH: 0x38,
    ecodes.KEY_CAPSLOCK: 0x39,
    ecodes.KEY_F1: 0x3A,
    ecodes.KEY_F2: 0x3B,
    ecodes.KEY_F3: 0x3C,
    ecodes.KEY_F4: 0x3D,
    ecodes.KEY_F5: 0x3E,
    ecodes.KEY_F6: 0x3F,
    ecodes.KEY_F7: 0x40,
    ecodes.KEY_F8: 0x41,
    ecodes.KEY_F9: 0x42,
    ecodes.KEY_F10: 0x43,
    ecodes.KEY_F11: 0x44,
    ecodes.KEY_F12: 0x45,
    ecodes.KEY_SYSRQ: 0x46, #print screen
    ecodes.KEY_SCROLLLOCK: 0x47,
    ecodes.KEY_PAUSE: 0x48,
    ecodes.KEY_INSERT: 0x49,
    ecodes.KEY_HOME: 0x4A,
    ecodes.KEY_PAGEUP: 0x4B,
    ecodes.KEY_DELETE: 0x4C,
    ecodes.KEY_END: 0x4D,
    ecodes.KEY_PAGEDOWN: 0x4E,
    ecodes.KEY_RIGHT: 0x4F,
    ecodes.KEY_LEFT: 0x50,
    ecodes.KEY_DOWN: 0x51,
    ecodes.KEY_UP: 0x52,
    ecodes.KEY_NUMLOCK: 0x53,
    ecodes.KEY_KPSLASH: 0x54,
    ecodes.KEY_KPASTERISK: 0x55,
    ecodes.KEY_KPMINUS: 0x56,
    ecodes.KEY_KPPLUS: 0x57,
    ecodes.KEY_KPENTER: 0x58,
    ecodes.KEY_KP1: 0x59,
    ecodes.KEY_KP2: 0x5A,
    ecodes.KEY_KP3: 0x5B,
    ecodes.KEY_KP4: 0x5C,
    ecodes.KEY_KP5: 0x5D,
    ecodes.KEY_KP6: 0x5E,
    ecodes.KEY_KP7: 0x5F,
    ecodes.KEY_KP8: 0x60,
    ecodes.KEY_KP9: 0x61,
    ecodes.KEY_KP0: 0x62,
    ecodes.KEY_KPDOT: 0x63,
    ecodes.KEY_102ND: 0x64, #uk pipe and backslash
    ecodes.KEY_COMPOSE: 0x65,
    ecodes.KEY_POWER: 0x66,
    ecodes.KEY_KPEQUAL: 0x67,
    ecodes.KEY_F13: 0x68,
    ecodes.KEY_F14: 0x69,
    ecodes.KEY_F15: 0x6a,
    ecodes.KEY_F16: 0x6b,
    ecodes.KEY_F17: 0x6c,
    ecodes.KEY_F18: 0x6d # last usage for the HID descriptor

}

class CompatibilityModeDevice:
    def __init__(self, loop: asyncio.AbstractEventLoop, device_path):
        self.device_path = device_path
        self.loop = loop
        self.ev_device = InputDevice(device_path)
        self.ev_device.grab()
        self.hidraw_device = UHIDDevice()
        self.hidraw_device.name = "BT HID Hub Virtual Hid Raw Keyboard"
        self.hidraw_device.info = [0x06, 0x0001, 0x0001]  # 0x06 - BUS_VIRTUAL, vendor id 1 product id 1
        self.hidraw_device.phys = "0"
        self.hidraw_device.rdesc = bytearray.fromhex(
            "05010906a1018501050719e029e715002501750195088102950175088103950575010508190129059102950175039103950675081500256d05071900296d8100c0050C0901A1018502050C150025017501950709B509B609B709CD09E209E909EA810295018101C0")
        self.pressed_keys:List[int]=[]
        self.pressed_consumer_keys:List[int]=[]

        self.hidraw_device.create_kernel_device()
        asyncio.run_coroutine_threadsafe(self.__read_events(),self.loop)
        print("Compatibility Device ",self.device_path," initialised")

    async def __read_events(self):
        async for ev in self.ev_device.async_read_loop():
            if ev.type == ecodes.EV_KEY and ev.value<2:
                print(categorize(ev))
                if ev.code in CONSUMER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING:
                    if ev.value == 1:  # down
                        if ev.code not in self.pressed_consumer_keys:
                            self.pressed_consumer_keys.append(ev.code)
                    elif ev.value == 0:  # up
                        if ev.code in self.pressed_consumer_keys:
                            self.pressed_consumer_keys.remove(ev.code)
                    self.__send_consumer_hid_report()
                else: #normal keys
                    if ev.code not in NORMAL_KEYS_EVENT_TO_USAGE_FLAG_MAPPING and ev.code not in MODIFIER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING: continue
                    if ev.value == 1:  # down
                        if ev.code not in self.pressed_keys:
                            self.pressed_keys.append(ev.code)
                    elif ev.value == 0:  # up
                        if ev.code in self.pressed_keys:
                            self.pressed_keys.remove(ev.code)
                    self.__send_normal_hid_report()

    def __send_consumer_hid_report(self):
        report = bytearray(b'\x02\x80') #first byte - report id 2, second byte - consumer key flags and one bit is constant (0x80)
        for code in self.pressed_consumer_keys:
            report[1] = report[1] | CONSUMER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING[code]
        self.hidraw_device.call_input_event(report)

    def __send_normal_hid_report(self):
        report = bytearray(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00') #first byte - report id 1, then 1 byte with modifier key flags, then const byte with 0, then 6 bytes with up to 6 keycodes (0 to 109)
        key_index = 3
        for code in self.pressed_keys:
            if code in MODIFIER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING:
                report[1] = report[1] | MODIFIER_KEYS_EVENT_TO_USAGE_FLAG_MAPPING[code]
            else:
                report[key_index] = NORMAL_KEYS_EVENT_TO_USAGE_FLAG_MAPPING[code]
                key_index += 1
                if key_index > 8: break

        self.hidraw_device.call_input_event(report)

    def __eq__(self, other):
        return self.device_path == other.device_path

    def finalise(self):
        #close device
        self.hidraw_device.destroy()
        self.hidraw_device = None
        self.ev_device.ungrab()
        self.ev_device.close()
        self.ev_device = None
        print("Compatibility Device ",self.device_path," finalised")

    def __del__(self):
        print("Compatibility Device ",self.device_path," removed")
