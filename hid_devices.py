# Copyright (c) 2020 ruundii. All rights reserved.

from __future__ import annotations

import asyncio
import os
import json
import re
import time
from typing import Awaitable, Callable, Literal, Optional, TypedDict, cast

import evdev
from watchfiles import awatch

from a1314_message_filter import A1314MessageFilter
from bluetooth_devices import BluetoothDeviceRegistry
from compatibility_device import CompatibilityModeDevice
from hid_message_filter import HIDMessageFilter
from mouse_g502_message_filter import G502MessageFilter
from mouse_message_filter import MouseMessageFilter
from mouse_mx510_message_filter import MX510MessageFilter


class __Device(TypedDict, total=False):
    capture: bool
    filter: str


class _Device(__Device):
    id: str
    instance: str
    name: str
    hidraw: str
    events: list[str]
    compatibility_mode: bool


class _InputDevice(TypedDict):
    name: str
    path: str
    phys: str
    compatibility_mode: bool


class _HIDDevices(TypedDict):
    devices: list[_Device]
    filters: list[dict[str, str]]
    input_devices: list[_InputDevice]


class _DeviceConfig(TypedDict, total=False):
    capture: bool
    filter: str


DEVICES_CONFIG_FILE_NAME = 'devices_config.json'
DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY = 'compatibility_devices'
CAPTURE_ELEMENT: Literal['capture'] = 'capture'
FILTER_ELEMENT: Literal['filter'] = 'filter'

FILTERS = [
    {"id":"Default", "name":"Default"},
    {"id":"Mouse", "name":"Mouse"},
    {"id":"A1314", "name":"A1314"},
    {"id":"G502", "name":"G502"},
    {"id":"MX510", "name":"MX510"}
]

FILTER_INSTANCES = {
"Default" : HIDMessageFilter(), "Mouse":MouseMessageFilter(), "A1314":A1314MessageFilter(), "G502":G502MessageFilter(), "MX510":MX510MessageFilter()
}

class HIDDevice:
    def __init__(self, device: _Device, filter: HIDMessageFilter,
                 loop: asyncio.AbstractEventLoop, device_registry: HIDDeviceRegistry):
        self.loop = loop
        self.filter = filter
        self.device_registry = device_registry
        self.device_id = device["instance"]
        self.device_class = device["id"]
        self.name = device["name"]
        self.hidraw = device["hidraw"]
        self.events = device["events"]
        self.events_devices = []
        for event in self.events:
            event_device = evdev.InputDevice('/dev/input/'+event)
            event_device.grab()
            self.events_devices.append(event_device)
        self.hidraw_file: Optional[int] = os.open('/dev/'+self.hidraw, os.O_RDWR | os.O_NONBLOCK)
        loop.add_reader(self.hidraw_file, self.hidraw_event)
        print("HID Device ",self.device_id," created")

    def set_device_filter(self, filter: HIDMessageFilter) -> None:
        self.filter = filter

    def hidraw_event(self) -> None:
        if self.hidraw_file is None:
            return
        try:
            msg = os.read(self.hidraw_file, 16)
        except Exception:
            #reopen
            self.loop.remove_reader(self.hidraw_file)
            os.close(self.hidraw_file)
            self.hidraw_file = None
            print("HID device ",self.device_id, " exception on read. closing")
            return
        tm = self.filter.filter_message_to_host(msg)
        if tm is None or self.device_registry.bluetooth_devices is None:
            return
        if tm == b'\xff':
            self.device_registry.bluetooth_devices.switch_host()
            self.indicate_switch_with_mouse_movement()
        else:
            self.device_registry.bluetooth_devices.send_message(tm, True, False)

    def indicate_switch_with_mouse_movement(self) -> None:
        """Move mouse in circular direction so user can see which host is active now"""
        for i in range(3):
            # Up
            self.move_mouse(b'\x00\xF0\xFE')
            time.sleep(0.05)
            # Right
            self.move_mouse(b'\x10\x00\x00')
            time.sleep(0.05)
            # Down
            self.move_mouse(b'\x00\x00\x01')
            time.sleep(0.05)
            # Left
            self.move_mouse(b'\xEF\x0F\x00')
            time.sleep(0.05)

    def move_mouse(self, xy: bytes) -> None:
        if self.device_registry.bluetooth_devices is None:
            return
        self.device_registry.bluetooth_devices.send_message(b'\xa1\x03\x00\x00\x00\x00' + xy, True, False)

    async def send_message(self, msg: bytes) -> None:
        tm = self.filter.filter_message_from_host(msg)
        if tm is not None and self.hidraw_file is not None:
            os.write(self.hidraw_file, tm)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HIDDevice):
            return self.device_id == other.device_id
        return False

    def finalise(self) -> None:
        #close file
        for event_device in self.events_devices:
            try:
                event_device.ungrab()
            except:
                pass
        if self.hidraw_file is not None:
            try:
                self.loop.remove_reader(self.hidraw_file)
                os.close(self.hidraw_file)
                self.hidraw_file = None
            except:
                pass
        print("HID Device ",self.device_id," finalised")

    def __del__(self) -> None:
        print("HID Device ",self.device_id," removed")


class HIDDeviceRegistry:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        try:
            with open(DEVICES_CONFIG_FILE_NAME) as devices_config:
                self.devices_config: dict[str, _DeviceConfig] = json.load(devices_config)
        except Exception:
            self.devices_config = {}
        self.devices: list[_Device] = []
        self.capturing_devices: dict[str, HIDDevice] = {}
        self.input_devices: list[_InputDevice] = []
        self.compatibility_mode_devices: dict[str, CompatibilityModeDevice] = {}
        asyncio.run_coroutine_threadsafe(self.__watch_device_changes(), loop=self.loop)
        self.on_devices_changed_handler: Optional[Callable[[], Awaitable[None]]] = None
        self.__scan_devices()
        self.bluetooth_devices: Optional[BluetoothDeviceRegistry] = None

    def set_bluetooth_devices(self, bluetooth_devices: BluetoothDeviceRegistry) -> None:
        self.bluetooth_devices = bluetooth_devices

    def set_on_devices_changed_handler(self, handler: Callable[[], Awaitable[None]]) -> None:
        self.on_devices_changed_handler = handler

    async def send_message_to_devices(self, msg: bytes) -> None:
        for device in self.capturing_devices.values():
            await device.send_message(msg)

    async def __watch_device_changes(self) -> None:
        async for changes in awatch("/dev/input/", recursive=False):
            self.__scan_devices()
            if self.on_devices_changed_handler is not None:
                await self.on_devices_changed_handler()

    def __scan_devices(self) -> None:
        #input_devices
        self.input_devices = []

        def _filter(d: evdev.InputDevice) -> bool:
            """Filter out devices without key capability and without esc button."""
            return 1 in d.capabilities().keys() and 1 in d.capabilities()[1] and d.info.bustype != 0x06

        for dev in filter(_filter, (evdev.InputDevice(path) for path in evdev.list_devices())):
            compatibility_mode = DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY in self.devices_config and dev.path in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]
            self.input_devices.append({"name": dev.name, "path": dev.path, "phys": dev.phys, "compatibility_mode": compatibility_mode})
            if compatibility_mode and dev.path not in self.compatibility_mode_devices:
                self.compatibility_mode_devices[dev.path] = CompatibilityModeDevice(self.loop, dev.path)

        devs_to_remove = []
        for dev_path in self.compatibility_mode_devices:
            if len([d for d in self.input_devices if d["path"]==dev_path and d["compatibility_mode"]]) == 0:
                devs_to_remove.append(dev_path)
        for dev_path in devs_to_remove:
            # remove compatibility device
            comp_device = self.compatibility_mode_devices[dev_path]
            del self.compatibility_mode_devices[dev_path]
            comp_device.finalise()
            del comp_device

        devs: list[_Device] = []
        devs_dict = {}
        devs_in_compatibility_mode = []
        for device in os.listdir('/sys/bus/hid/devices'):
            try:
                with open('/sys/bus/hid/devices/'+device+'/uevent', 'r') as uevent:
                    m = re.search('HID_NAME\s*=(.+)', uevent.read())
                    if m is not None:
                        name: str = m.group(1)
                        hidraw = os.listdir('/sys/bus/hid/devices/'+device+'/hidraw')[0]
                        inputs = os.listdir('/sys/bus/hid/devices/'+device+'/input')
                        events = []
                        compatibility_mode = False
                        for input in inputs:
                            input_events = [e for e in os.listdir('/sys/bus/hid/devices/' + device + '/input/'+input) if e.startswith('event')]
                            for event in input_events:
                                for input_device in self.input_devices:
                                    if input_device["compatibility_mode"] and input_device["path"].find(event)>=0:
                                        compatibility_mode = True
                                        break
                            events.extend(input_events)

                        id = device.split('.')[0]
                        devs.append({"id":id, "instance":device, "name":name, "hidraw": hidraw, "events":events, "compatibility_mode":compatibility_mode})
                        devs_dict[device] = id
                        if compatibility_mode: devs_in_compatibility_mode.append(device)
            except Exception as exc:
                print("Error while loading HID device: ", device, ", Error: ", exc,", Skipping.")
        devs_to_remove = []
        for dev_name in self.capturing_devices:
            if dev_name not in devs_dict or not self.__is_configured_capturing_device(devs_dict[dev_name]) or dev_name in devs_in_compatibility_mode:
                #remove capturing device
                devs_to_remove.append(dev_name)

        for dev_name in devs_to_remove:
            hid_device = self.capturing_devices[dev_name]
            del self.capturing_devices[dev_name]
            hid_device.finalise()
            del hid_device

        for dev_dict in devs:
            if dev_dict["instance"] not in self.capturing_devices and self.__is_configured_capturing_device(dev_dict["id"]) and dev_dict["instance"] not in devs_in_compatibility_mode:
                #create capturing device
                self.capturing_devices[dev_dict["instance"]] = HIDDevice(dev_dict, self.__get_configured_device_filter(dev_dict["id"]), self.loop, self)
        self.devices = devs


    def set_device_capture(self, device_id: str, capture: bool) -> None:
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][CAPTURE_ELEMENT] = capture
        self.__save_config()
        self.__scan_devices()

    def set_device_filter(self, device_id: str, filter_id: str) -> None:
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][FILTER_ELEMENT] = filter_id
        self.__save_config()
        filter = self.__get_configured_device_filter(device_id)
        for dev in self.capturing_devices:
            if self.capturing_devices[dev].device_class == device_id:
                self.capturing_devices[dev].set_device_filter(filter)

    def set_compatibility_device(self, device_path: str, compatibility_state: bool) -> None:
        if DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY not in self.devices_config:
            self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY] = []  # type: ignore[assignment]
        if compatibility_state and device_path not in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]:
            cast(list[str], self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]).append(device_path)
        elif not compatibility_state and device_path in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]:
            cast(list[str], self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]).remove(device_path)
        self.__save_config()
        self.__scan_devices()

    def __save_config(self) -> None:
        with open(DEVICES_CONFIG_FILE_NAME, 'w') as devices_config_file:
            json.dump(self.devices_config, devices_config_file)

    def __is_configured_capturing_device(self, device_id: str) -> bool:
        if device_id in self.devices_config:
            if CAPTURE_ELEMENT in self.devices_config[device_id]:
                return self.devices_config[device_id][CAPTURE_ELEMENT]
        return False

    def __get_configured_device_filter(self, device_id: str) -> HIDMessageFilter:
        if device_id in self.devices_config:
            if FILTER_ELEMENT in self.devices_config[device_id]:
                filter_id = self.devices_config[device_id][FILTER_ELEMENT]
                return FILTER_INSTANCES[filter_id]
        return FILTER_INSTANCES["Default"]

    def get_hid_devices_with_config(self) -> _HIDDevices:
        for device in self.devices:
            if device["id"] in self.devices_config:
                device[CAPTURE_ELEMENT] = self.devices_config[device["id"]].get(CAPTURE_ELEMENT, False)
                if FILTER_ELEMENT in self.devices_config[device["id"]]:
                    device[FILTER_ELEMENT] =  self.devices_config[device["id"]][FILTER_ELEMENT]
        return {"devices": self.devices, "filters": FILTERS, "input_devices": self.input_devices}
