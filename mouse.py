# Copyright (c) 2020 ruundii. All rights reserved.

import evdev
import os
import asyncio
from device import *

mouse_raw_device = '/dev/hidraw4'
mouse_event_device = '/dev/input/event18'

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(device.path, device.name, device.phys)

class Mouse:
    def __init__(self, loop: asyncio.AbstractEventLoop, device_registry: DeviceRegistry):
        self.dev = evdev.InputDevice(mouse_event_device)
        self.hidraw = os.open(mouse_raw_device, os.O_RDWR | os.O_NONBLOCK)
        #self.dev.grab()
        self.device_registry = device_registry
        self.loop = loop
        loop.add_reader(self.hidraw, self.mouse_event)

    def mouse_event(self):
        if self.hidraw is None:
            return
        try:
            msg = os.read(self.hidraw, 2147483647)
        except Exception:
            #reopen
            self.loop.remove_reader(self.hidraw)
            os.close(self.hidraw)
            self.hidraw = None
            asyncio.ensure_future(self.mouse_reconnect())
            return
        if len(msg) != 7:
            return
        msg = b'\xa1\x03' + msg
        asyncio.ensure_future(self.device_registry.send_message(msg, True, False))

    async def mouse_reconnect(self):
        while True:
            try:
                fp = os.open(mouse_raw_device, os.O_RDWR | os.O_NONBLOCK)
                self.loop.add_reader(fp, self.mouse_event)
                return
            except Exception:
                await asyncio.sleep(1, loop=self.loop)

