# Copyright (c) 2020 ruundii. All rights reserved.

import asyncio
import socket
import os
from concurrent.futures import Future
from contextlib import suppress
from subprocess import DEVNULL, PIPE
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from dasbus.connection import SystemMessageBus

if TYPE_CHECKING:
    from hid_devices import HIDDeviceRegistry

OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
DEVICE_INTERFACE = 'org.bluez.Device1'
PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
INPUT_DEVICE_INTERFACE = 'org.bluez.Input1'
INPUT_HOST_INTERFACE = 'org.bluez.InputHost1'

IGNORE_INPUT_DEVICES = True

class BluetoothDevice:
    def __init__(self, bus: SystemMessageBus, loop: asyncio.AbstractEventLoop,
                 device_registry: "BluetoothDeviceRegistry", object_path: str,
                 is_host: bool,  control_socket_path: str, interrupt_socket_path: str):
        self.device = bus.get_proxy(service_name="org.bluez", object_path=object_path, interface_name=DEVICE_INTERFACE)
        self.props = bus.get_proxy(service_name="org.bluez", object_path=object_path, interface_name=PROPERTIES_INTERFACE)
        self.props.PropertiesChanged.connect(self.device_connected_state_changed)

        self.bus = bus
        self.loop = loop
        self.device_registry = device_registry
        self.object_path = object_path
        self.is_host = is_host
        self.control_socket_path: Optional[str] = control_socket_path
        self.control_socket: Optional[socket.socket] = None
        self.interrupt_socket_path: Optional[str] = interrupt_socket_path
        self.interrupt_socket: Optional[socket.socket] = None
        self.sockets_connected = False
        self._tasks: set[Future[None]] = set()

        print("BT Device ",object_path," created")
        asyncio.run_coroutine_threadsafe(self.reconcile_connected_state(1), loop=self.loop)

    async def reconcile_connected_state(self, delay: int) -> None:
        await asyncio.sleep(delay)
        try:
            if self.connected and not self.sockets_connected:
                await self.connect_sockets()
            elif not self.connected and self.sockets_connected:
                await self.disconnect_sockets()
        except Exception as exc:
            print("Possibly dbus error during reconcile_connected_state ",exc)

    async def connect_sockets(self) -> None:
        if self.sockets_connected or self.control_socket_path is None or self.interrupt_socket_path is None:
            return
        print("Connecting sockets for ",self.object_path)
        if not self.connected:
            print("BT Device is not connected. No point connecting sockets. Skipping.")
        try:
            self.control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self.control_socket.connect(self.control_socket_path)
            self.control_socket.setblocking(False)

            self.interrupt_socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self.interrupt_socket.connect(self.interrupt_socket_path)
            self.interrupt_socket.setblocking(False)
            self.sockets_connected = True
            if(self.is_host):
                self.device_registry.connected_hosts.append(self)
                addr = self.object_path[-17:].replace("_",":")
                asyncio.create_task(self.device_registry.switch_to_master(addr))
            else:
                self.device_registry.connected_devices.append(self)
            print("Connected sockets for ",self.object_path)
            self._tasks.add(asyncio.run_coroutine_threadsafe(self.loop_of_fun(True), loop=self.loop))
            self._tasks.add(asyncio.run_coroutine_threadsafe(self.loop_of_fun(False), loop=self.loop))
        except Exception as err:
            print("Error while connecting sockets for ",self.object_path,". Will retry in a sec", err)
            try:
                if self.control_socket is not None:
                    self.control_socket.close()
                if self.interrupt_socket is not None:
                    self.interrupt_socket.close()
            except:
                pass
            await asyncio.sleep(1)
            asyncio.run_coroutine_threadsafe(self.connect_sockets(), loop=self.loop)

    async def disconnect_sockets(self) -> None:
        for t in self._tasks:
            t.cancel()
            # TODO: Reenable if we manage to turn this into tasks (i.e. not use coroutine_threasfe).
            #with suppress(asyncio.CancelledError):
            #    await t

        if self.control_socket is not None:
            self.control_socket.close()
            self.control_socket = None
        if self.interrupt_socket is not None:
            self.interrupt_socket.close()
            self.interrupt_socket = None
        if(self.is_host and self in self.device_registry.connected_hosts):
            self.device_registry.connected_hosts.remove(self)
        elif self in self.device_registry.connected_devices:
            self.device_registry.connected_devices.remove(self)
        self.sockets_connected = False

        print("Disconnected  sockets for ",self.object_path)


    async def loop_of_fun(self, is_ctrl: bool) -> None:
        sock = self.control_socket if is_ctrl else self.interrupt_socket
        while sock is not None:
            try:
                msg = await self.loop.sock_recv(sock,255)
            except Exception:
                print("Cannot read data from socket. ", self.object_path ,"Closing sockets")
                if self is not None:
                    try:
                        await self.disconnect_sockets()
                    except:
                        print("Error while disconnecting sockets")
                print("Arranging reconnect")
                asyncio.run_coroutine_threadsafe(self.reconcile_connected_state(1), loop=self.loop)
                break
            if msg is None or len(msg)==0:
                continue
            self.device_registry.send_message(msg, not self.is_host, is_ctrl)
            sock = self.control_socket if is_ctrl else self.interrupt_socket


    @property
    def name(self) -> str:
        return self.device.Name

    @property
    def alias(self) -> str:
        return self.device.Alias

    @property
    def connected(self) -> bool:
        return self.device.Connected

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BluetoothDevice):
            return self.object_path == other.object_path
        return False

    def device_connected_state_changed(self, _arg1: object, _arg2: object, _arg3: object) -> None:
        print("device_connected_state_changed")
        asyncio.run_coroutine_threadsafe(self.reconcile_connected_state(1), loop=self.loop)
        if self.device_registry.on_devices_changed_handler is not None:
            asyncio.run_coroutine_threadsafe(self.device_registry.on_devices_changed_handler(), loop=self.loop)

    async def finalise(self) -> None:
        self.props.PropertiesChanged.disconnect(self.device_connected_state_changed)
        self.control_socket_path = None
        self.interrupt_socket_path = None
        # Close sockets
        await self.disconnect_sockets()
        print("BT Device ",self.object_path," finalised")


    def __del__(self) -> None:
        print("BT Device ",self.object_path," removed")

class BluetoothDeviceRegistry:
    def __init__(self, bus: SystemMessageBus, loop: asyncio.AbstractEventLoop):
        self.bus = bus
        self.loop = loop
        self.all: dict[str, BluetoothDevice] = {}
        self.connected_hosts: list[BluetoothDevice] = []
        self.connected_devices: list[BluetoothDevice] = []
        self.on_devices_changed_handler: Optional[Callable[[], Awaitable[None]]] = None
        self.hid_devices: Optional["HIDDeviceRegistry"] = None
        self.current_host_index = 0

    def set_hid_devices(self, hid_devices: "HIDDeviceRegistry") -> None:
        self.hid_devices = hid_devices

    def set_on_devices_changed_handler(self, handler: Callable[[], Awaitable[None]]) -> None:
        self.on_devices_changed_handler = handler

    def add_devices(self) -> None:
        print("Adding all BT devices")
        om = self.bus.get_proxy(service_name= "org.bluez", object_path="/", interface_name=OBJECT_MANAGER_INTERFACE)
        objs = om.GetManagedObjects()

        for obj in list(objs):
            if INPUT_HOST_INTERFACE in objs[obj]:
                self.add_device(obj, True)

            elif INPUT_DEVICE_INTERFACE in objs[obj]:
                self.add_device(obj, False)

    def add_device(self, device_object_path: str, is_host: bool) -> None:
        if(IGNORE_INPUT_DEVICES and not is_host): return

        if device_object_path in self.all:
            print("Device ", device_object_path, " already exist. Cannot add. Skipping.")
            return
        #ensure master role for this connection, otherwise latency of sending packets to hosts may get pretty bad
        asyncio.ensure_future(self.switch_to_master(device_object_path[-17:].replace("_",":")))
        p = self.bus.get_proxy(service_name="org.bluez", object_path=device_object_path, interface_name=INPUT_HOST_INTERFACE if is_host else INPUT_DEVICE_INTERFACE)
        device = BluetoothDevice(self.bus, self.loop, self, device_object_path, is_host, p.SocketPathCtrl, p.SocketPathIntr)
        self.all[device_object_path] = device

    async def switch_to_master(self, device_address: str) -> None:
        print("switch to master called for ", device_address)
        while await self.is_slave(device_address):
            try:
                proc = await asyncio.create_subprocess_exec("sudo", "hcitool", "sr", device_address, "MASTER", stdout=DEVNULL)
                await proc.wait()
                print("hcitool ", device_address, " success:", proc.returncode == 0)
            except Exception as exc:
                print("hcitool ",device_address," exception:",exc)
            await asyncio.sleep(5)

    async def is_slave(self, device_address: str) -> bool:
        proc = await asyncio.create_subprocess_exec("sudo", "hcitool", "con", stdout=PIPE, stderr=DEVNULL)
        stdout, stderr = await proc.communicate()
        return any("SLAVE" in l and device_address in l for l in stdout.decode().split("\n"))

    async def remove_devices(self) -> None:
        print("Removing all BT devices")
        while len(self.all) >0:
            await self.remove_device(list(self.all)[0])


    async def remove_device(self, device_object_path: str) -> None:
        if device_object_path not in self.all:
            return  # No such device
        device = self.all[device_object_path]
        del self.all[device_object_path]
        list = self.connected_hosts if device.is_host else self.connected_devices
        if device in list:
            list.remove(device)
        await device.finalise()

    def switch_host(self) -> None:
        self.current_host_index = (self.current_host_index + 1) % len(self.connected_hosts)

    def __get_current_host_as_list(self) -> list[BluetoothDevice]:
        if len(self.connected_hosts) <= self.current_host_index:
            return []
        return [self.connected_hosts[self.current_host_index]]

    def send_message(self, msg: bytes, send_to_hosts: bool, is_control_channel: bool) -> None:
        if IGNORE_INPUT_DEVICES and not send_to_hosts and not is_control_channel and self.hid_devices is not None:
            asyncio.run_coroutine_threadsafe(self.hid_devices.send_message_to_devices(msg), loop=self.loop)
            return
        targets: list[BluetoothDevice] = self.__get_current_host_as_list() if send_to_hosts else self.connected_devices
        for target in list(targets):
            try:
                socket = target.control_socket if is_control_channel else target.interrupt_socket
                if socket is not None:
                    socket.sendall(msg)
            except Exception:
                print("Cannot send data to socket of ",target.object_path,". Closing")
                if target is not None:
                    try:
                        asyncio.run_coroutine_threadsafe(target.disconnect_sockets(), loop=self.loop)
                    except:
                        print("Error while trying to disconnect sockets")
                asyncio.run_coroutine_threadsafe(target.reconcile_connected_state(1), loop=self.loop)
