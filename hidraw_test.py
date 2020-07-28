# Copyright (c) 2020 ruundii. All rights reserved.

import sys
import os
import select
import asyncio, gbulb
from evdev import InputDevice

import evdev

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(device.path, device.name, device.phys)

dev = InputDevice('/dev/input/event18')

fp = os.open('/dev/hidraw1', os.O_RDWR | os.O_NONBLOCK)
dev.grab()
#fcntl.flock(fp, fcntl.LOCK_EX)
def cb():
    print("read",os.read(fp, 768768))

loop = asyncio.get_event_loop()
loop.add_reader(fp, cb)

loop.run_forever()
# tStr = ''
# while 1:
#         fp = os.open('/dev/hidraw1', os.O_RDONLY|os.O_NONBLOCK)
#         poller = select.poll()
#         poller.
#         #buffer =fp.readline()
#         buffer = fp.read(7)
#         print(buffer)
