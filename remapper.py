# Copyright (c) 2020 ruundii. All rights reserved.

from dasbus.connection import SystemMessageBus
from web import Web
import asyncio
import asyncio_glib
from adapter import BluetoothAdapter

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
    loop = asyncio.get_event_loop()
    bus = SystemMessageBus()
    adapter = BluetoothAdapter(bus, loop)
    web = Web(loop, adapter)
    loop.run_forever()


#print(proxy)