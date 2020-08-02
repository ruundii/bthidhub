# Copyright (c) 2020 ruundii. All rights reserved.

from dasbus.connection import SystemMessageBus
from web import Web
import asyncio
import asyncio_glib
from adapter import BluetoothAdapter
from hid_devices import *
from bluetooth_devices import *

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
    loop = asyncio.get_event_loop()
    bus = SystemMessageBus()
    bluetooth_devices = BluetoothDeviceRegistry(bus, loop)
    hid_devices = HIDDeviceRegistry(loop)
    hid_devices.set_bluetooth_devices(bluetooth_devices)
    adapter = BluetoothAdapter(bus, loop, bluetooth_devices, hid_devices)
    web = Web(loop, adapter, bluetooth_devices, hid_devices)
    loop.run_forever()


#print(proxy)