# Copyright (c) 2020 ruundii. All rights reserved.

import asyncio
import sys
from signal import SIGINT

import asyncio_glib
from dasbus.connection import SystemMessageBus

from adapter import BluetoothAdapter
from bluetooth_devices import *
from hid_devices import *
from web import Web

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(SIGINT, sys.exit)
    bus = SystemMessageBus()
    bluetooth_devices = BluetoothDeviceRegistry(bus, loop)
    hid_devices = HIDDeviceRegistry(loop)
    hid_devices.set_bluetooth_devices(bluetooth_devices)
    bluetooth_devices.set_hid_devices(hid_devices)
    adapter = BluetoothAdapter(bus, loop, bluetooth_devices, hid_devices)
    web = Web(loop, adapter, bluetooth_devices, hid_devices)
    loop.run_forever()


#print(proxy)
