# Copyright (c) 2020 ruundii. All rights reserved.

from dasbus.connection import SystemMessageBus
from agent import Agent
from device import *
from mouse import *

import asyncio, gbulb
gbulb.install()


DBUS_PATH_PROFILE = '/ruundii/btkb_profile'
DBUS_PATH_AGENT = '/ruundii/btkb_agent'
ROOT_OBJECT = '/org/bluez'
ADAPTER_OBJECT = '/org/bluez/hci0'
ADAPTER_INTERFACE = 'org.bluez.Adapter1'
DEVICE_INTERFACE = 'org.bluez.Device1'
OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
DEVICE_NAME = 'Bluetooth HID Hub - Ubuntu'

bus = SystemMessageBus()
loop = asyncio.get_event_loop()

class BluetoothAdapter:
    def __init__(self):
        self.device_registry = DeviceRegistry(bus)
        self.mouse = Mouse(loop, self.device_registry)
        self.agent_published = False
        self.om_proxy_initialised = False
        self.initialising_adapter = False

        asyncio.ensure_future(self.init())

    async def init(self):
        await self.wait_bt_service_run()
        if not self.om_proxy_initialised:
            om = bus.get_proxy(service_name="org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
            om.InterfacesAdded.connect(self.interfaces_added)
            om.InterfacesRemoved.connect(self.interfaces_removed)
            self.om_proxy_initialised = True
        self.wait_till_adapter_present_then_init_sync()

    def bt_service_running(self):
        try:
            om = bus.get_proxy(service_name= "org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
            om.GetManagedObjects()
            return True
        except:
            return False

    async def wait_bt_service_run(self):
        while not self.bt_service_running():
            print("No BT service. Waiting...")
            await asyncio.sleep(2)

    def adapter_exists(self):
        try:
            adapter = bus.get_proxy(service_name="org.bluez", object_path=ADAPTER_OBJECT, interface_name=ADAPTER_INTERFACE)
            return adapter.Version == "Hacked"
        except:
            return False

    def wait_till_adapter_present_then_init_sync(self):
        if self.initialising_adapter:
            return # already initing
        self.initialising_adapter = True
        asyncio.ensure_future(self.wait_till_adapter_present_then_init())

    async def wait_till_adapter_present_then_init(self):
        while not self.adapter_exists():
            print("No BT adapter. Waiting...")
            await asyncio.sleep(2)

        self.register_agent()
        self.adapter = bus.get_proxy(service_name="org.bluez", object_path=ADAPTER_OBJECT,
                                     interface_name="org.bluez.Adapter1")

        while not self.powered:
            print("Bluetooth adapter is turned off. Trying to turn on")
            try:
                self.powered = True
                if (self.powered):
                    print("Successfully turned on")
                else:
                    print("Failed to turn on. Please turn on Bluetooth in the system")
            except Exception:
                print("Failed to turn on. Please turn on Bluetooth in the system")
            await asyncio.sleep(2)

        self.alias = DEVICE_NAME
        self.discoverable = True
        self.discoverable_timeout = 0
        self.device_registry.remove_devices()
        self.device_registry.add_devices()
        self.initialising_adapter = False


    def interfaces_added(self, obj_name, interfaces):
        if not self.adapter_exists():
            return
        if(obj_name==ADAPTER_OBJECT or obj_name==ROOT_OBJECT):
            print("Bluetooth adapter added. Starting")
            self.wait_till_adapter_present_then_init_sync()

        elif INPUT_HOST_INTERFACE in interfaces:
            self.device_registry.add_device(obj_name, True)

        elif INPUT_DEVICE_INTERFACE in interfaces:
            self.device_registry.add_device(obj_name, False)


    def interfaces_removed(self, obj_name, interfaces):
        if(obj_name==ADAPTER_OBJECT or obj_name==ROOT_OBJECT):
            self.adapter = None
            self.device_registry.remove_devices()
            print("Bluetooth adapter removed. Stopping")
            asyncio.ensure_future(self.init())
        elif INPUT_HOST_INTERFACE in interfaces or  INPUT_DEVICE_INTERFACE in interfaces:
            self.device_registry.remove_device(obj_name)


    def register_agent(self):
        if not self.agent_published:
            agent = Agent()
            bus.publish_object(DBUS_PATH_AGENT, agent)
            self.agent_published = True
            agent_manager = bus.get_proxy(service_name="org.bluez", object_path="/org/bluez",
                                          interface_name="org.bluez.AgentManager1")
            agent_manager.RegisterAgent(DBUS_PATH_AGENT, "KeyboardOnly")
            agent_manager.RequestDefaultAgent(DBUS_PATH_AGENT)
            print("Agent registered")

    @property
    def powered(self):
        return self.adapter.Powered

    @powered.setter
    def powered(self, new_value):
        self.adapter.Powered = new_value

    @property
    def alias(self):
        return self.adapter.Alias

    @alias.setter
    def alias(self, new_value):
        self.adapter.Alias = new_value

    @property
    def discoverable(self):
        return self.adapter.Discoverable

    @discoverable.setter
    def discoverable(self, new_value):
        self.adapter.Discoverable = new_value

    @property
    def discoverable_timeout(self):
        return self.adapter.DiscoverableTimeout

    @discoverable_timeout.setter
    def discoverable_timeout(self, new_value):
        self.adapter.DiscoverableTimeout = new_value


if __name__ == "__main__":

    a = BluetoothAdapter()
    loop.run_forever()


#print(proxy)