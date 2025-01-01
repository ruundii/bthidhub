# Copyright (c) 2020 ruundii. All rights reserved.

import asyncio
from collections.abc import Container
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional, TypedDict, cast

from dasbus.connection import InterfaceProxy, SystemMessageBus
import dasbus.typing as dt

from agent import Action, Agent
from bluetooth_devices import BluetoothDeviceRegistry, INPUT_DEVICE_INTERFACE, INPUT_HOST_INTERFACE
from hid_devices import HIDDeviceRegistry


class _Device(TypedDict):
    path: str
    address: str
    alias: str
    paired: bool
    trusted: bool
    connected: bool
    host: bool


class _GetDevices(TypedDict):
    devices: list[_Device]
    scanning: bool


DBUS_PATH_PROFILE = '/ruundii/btkb_profile'
DBUS_PATH_AGENT = '/ruundii/btkb_agent'
ROOT_OBJECT = '/org/bluez'
ADAPTER_OBJECT = '/org/bluez/hci0'
ADAPTER_INTERFACE = 'org.bluez.Adapter1'
DEVICE_INTERFACE = 'org.bluez.Device1'
OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
DEVICE_NAME = 'Bluetooth HID Hub - RPi'
UUID = '00001124-0000-1000-8000-00805f9b34fb'


class BluetoothAdapter:
    adapter: Optional[InterfaceProxy]

    def __init__(self, bus: SystemMessageBus, loop: asyncio.AbstractEventLoop,
                 bluetooth_devices: BluetoothDeviceRegistry, hid_devices: HIDDeviceRegistry):
        self.bus = bus
        self.loop = loop
        self.bluetooth_devices = bluetooth_devices
        self.hid_devices = hid_devices
        self.agent_published = False
        self.agent: Optional[Agent] = None
        self.om_proxy_initialised = False
        self.initialising_adapter = False
        self.scan_start_time: Optional[datetime] = None
        self.discoverable_start_time: Optional[datetime] = None
        self.on_agent_action_handler: Optional[Callable[[Action], Awaitable[None]]] = None
        self.on_interface_changed_handler: Optional[Callable[[], Awaitable[None]]] = None
        asyncio.run_coroutine_threadsafe(self.init(), loop=self.loop)

    async def init(self) -> None:
        await self.wait_bt_service_run()
        if not self.om_proxy_initialised:
            om = self.bus.get_proxy(service_name="org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
            om.InterfacesAdded.connect(self.interfaces_added)
            om.InterfacesRemoved.connect(self.interfaces_removed)
            self.om_proxy_initialised = True
        self.wait_till_adapter_present_then_init_sync()

    def bt_service_running(self) -> bool:
        try:
            om = self.bus.get_proxy(service_name= "org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
            om.GetManagedObjects()
            return True
        except:
            return False

    async def wait_bt_service_run(self) -> None:
        while not self.bt_service_running():
            print("No BT service. Waiting...")
            await asyncio.sleep(2)

    def adapter_exists(self) -> bool:
        try:
            adapter = self.bus.get_proxy(service_name="org.bluez", object_path=ADAPTER_OBJECT, interface_name=ADAPTER_INTERFACE)
            return adapter.Version == "Hacked"
        except:
            return False

    def wait_till_adapter_present_then_init_sync(self) -> None:
        if self.initialising_adapter:
            return # already initing
        self.initialising_adapter = True
        asyncio.run_coroutine_threadsafe(self.wait_till_adapter_present_then_init(), loop=self.loop)

    async def wait_till_adapter_present_then_init(self) -> None:
        while not self.adapter_exists():
            print("No BT adapter. Waiting...")
            await asyncio.sleep(2)

        self.register_agent()
        self.adapter = self.bus.get_proxy(service_name="org.bluez", object_path=ADAPTER_OBJECT,
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
        await self.bluetooth_devices.remove_devices()
        self.bluetooth_devices.add_devices()
        self.initialising_adapter = False


    def interfaces_added(self, obj_name: str, interfaces: Container[str]) -> None:
        self.on_interface_changed()
        if not self.adapter_exists():
            return
        if (obj_name==ADAPTER_OBJECT or obj_name==ROOT_OBJECT):
            print("Bluetooth adapter added. Starting")
            self.wait_till_adapter_present_then_init_sync()

        elif INPUT_HOST_INTERFACE in interfaces:
            self.bluetooth_devices.add_device(obj_name, True)

        elif INPUT_DEVICE_INTERFACE in interfaces:
            self.bluetooth_devices.add_device(obj_name, False)

    def interfaces_removed(self, obj_name: str, interfaces: Container[str]) -> None:
        if (obj_name==ADAPTER_OBJECT or obj_name==ROOT_OBJECT):
            self.adapter = None
            asyncio.run_coroutine_threadsafe(self.bluetooth_devices.remove_devices(), loop=self.loop)
            print("Bluetooth adapter removed. Stopping")
            asyncio.run_coroutine_threadsafe(self.init(), loop=self.loop)
        elif INPUT_HOST_INTERFACE in interfaces or INPUT_DEVICE_INTERFACE in interfaces:
            asyncio.run_coroutine_threadsafe(self.bluetooth_devices.remove_device(obj_name), loop=self.loop)
        self.on_interface_changed()

    def register_agent(self) -> None:
        if not self.agent_published:
            self.agent = Agent()
            self.agent.set_on_agent_action_handler(self.on_agent_action)
            self.bus.publish_object(DBUS_PATH_AGENT, self.agent)
            self.agent_published = True
            agent_manager = self.bus.get_proxy(service_name="org.bluez", object_path="/org/bluez",
                                          interface_name="org.bluez.AgentManager1")
            agent_manager.RegisterAgent(DBUS_PATH_AGENT, "KeyboardDisplay")
            agent_manager.RequestDefaultAgent(DBUS_PATH_AGENT)
            print("Agent registered")

    def start_scan(self) -> None:
        if self.adapter is not None:
            #self.adapter.SetDiscoveryFilter({"UUIDs":dt.get_variant(dt.List[dt.Str], [UUID])})
            self.scan_start_time = datetime.now()
            self.adapter.StartDiscovery()
            asyncio.run_coroutine_threadsafe(self.__shutdown_scanning(), loop=self.loop)

    def stop_scan(self) -> None:
        if self.adapter is not None:
            self.adapter.StopDiscovery()
            #self.adapter.SetDiscoveryFilter({})

    async def __shutdown_scanning(self) -> None:
        while self.adapter is not None \
                and self.adapter.Discovering \
                and self.scan_start_time is not None \
                and (self.scan_start_time+timedelta(seconds=60))>datetime.now():
            await asyncio.sleep(1)
        if self.adapter is not None and self.adapter.Discovering:
            self.stop_scan()

    def start_discoverable(self) -> None:
        if self.adapter is not None:
            self.discoverable_start_time = datetime.now()
            self.discoverable = True
            self.discoverable_timeout = 0
            asyncio.run_coroutine_threadsafe(self.__shutdown_discoverable(), loop=self.loop)

    def stop_discoverable(self) -> None:
        if self.adapter is not None:
            self.discoverable = False

    async def __shutdown_discoverable(self) -> None:
        while self.adapter is not None \
                and self.discoverable \
                and self.discoverable_start_time is not None \
                and (self.discoverable_start_time+timedelta(seconds=120))>datetime.now():
            await asyncio.sleep(1)
        if self.adapter is not None and self.discoverable:
            self.discoverable = False

    def agent_request_confirmation_response(self, device: str, passkey: str, confirmed: bool) -> None:
        if self.agent_published and self.agent is not None:
            self.agent.request_confirmation_response(device, passkey, confirmed)

    def get_devices(self) -> _GetDevices:
        if self.adapter is None:
            return {"devices": [], "scanning": False }
        om = self.bus.get_proxy(service_name="org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
        objs = om.GetManagedObjects()
        devices: list[_Device] = []
        for path in objs:
            obj = objs[path]
            if DEVICE_INTERFACE in obj:
                dev = obj[DEVICE_INTERFACE]
                devices.append({
                    "path"    : path,
                    "address" : cast(str, dt.unwrap_variant(dev["Address"])),
                    "alias": cast(str, dt.unwrap_variant(dev["Alias"])),
                    "paired": cast(bool, dt.unwrap_variant(dev["Paired"])),
                    "trusted": cast(bool, dt.unwrap_variant(dev["Trusted"])),
                    "connected": cast(bool, dt.unwrap_variant(dev["Connected"])),
                    "host"     : INPUT_HOST_INTERFACE in obj
                })
        return {"devices": devices, "scanning": self.adapter.Discovering}

    def device_action(self, action: str, device_path: str) -> None:
        if self.adapter is None:
            return
        dp = self.bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name=DEVICE_INTERFACE)
        try:
            if action == 'pair':
                try:
                    dp.CancelPairing()
                except:
                    pass
                dp.Pair()
            elif action == 'connect':
                dp.Connect()
            elif action == 'disconnect':
                dp.Disconnect()
        except Exception as exc:
            print(exc)
        self.on_interface_changed()

    def remove_device(self, device_path: str) -> None:
        if self.adapter is None:
            return
        try:
            self.adapter.RemoveDevice(device_path)
        except Exception as exc:
            print(exc)

    def cancel_pairing(self, device_path: str) -> None:
        if self.adapter is None:
            return
        try:
            dp = self.bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name=DEVICE_INTERFACE)
            dp.CancelPairing()
        except:
            pass

    def set_on_agent_action_handler(self, handler: Callable[[Action], Awaitable[None]]) -> None:
        self.on_agent_action_handler = handler

    def on_agent_action(self, msg: Action) -> None:
        if self.on_agent_action_handler is not None:
            asyncio.run_coroutine_threadsafe(self.on_agent_action_handler(msg), loop=self.loop)

    def set_on_interface_changed_handler(self, handler: Callable[[], Awaitable[None]]) -> None:
        self.on_interface_changed_handler = handler

    def on_interface_changed(self) -> None:
        if self.on_interface_changed_handler is not None:
            asyncio.run_coroutine_threadsafe(self.on_interface_changed_handler(), loop=self.loop)

    @property
    def powered(self) -> bool:
        if self.adapter is None:
            return False
        return self.adapter.Powered

    @powered.setter
    def powered(self, new_value: bool) -> None:
        if self.adapter is None:
            return
        self.adapter.Powered = new_value

    @property
    def alias(self) -> str:
        if self.adapter is None:
            return ""
        return self.adapter.Alias

    @alias.setter
    def alias(self, new_value: str) -> None:
        if self.adapter is None:
            return
        self.adapter.Alias = new_value

    @property
    def discoverable(self) -> bool:
        if self.adapter is None:
            return False
        return self.adapter.Discoverable

    @discoverable.setter
    def discoverable(self, new_value: bool) -> None:
        if self.adapter is None:
            return
        self.adapter.Discoverable = new_value

    @property
    def discoverable_timeout(self) -> int:
        if self.adapter is None:
            return 0
        return self.adapter.DiscoverableTimeout

    @discoverable_timeout.setter
    def discoverable_timeout(self, new_value: int) -> None:
        if self.adapter is None:
            return
        self.adapter.DiscoverableTimeout = new_value
