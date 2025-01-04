# Copyright (c) 2020 ruundii. All rights reserved.

from __future__ import annotations

import array
import asyncio
import fcntl
import importlib
import os
import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Awaitable, Callable, Literal, Optional, TypedDict, Union, cast

import evdev
from watchfiles import awatch

from bluetooth_devices import BluetoothDeviceRegistry
from compatibility_device import CompatibilityModeDevice

HIDMessageFilter = Callable[[bytes], Optional[bytes]]


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
    filters: tuple[dict[str, str], ...]
    input_devices: list[_InputDevice]


class _DeviceConfig(TypedDict, total=False):
    capture: bool
    descriptor: str
    filter: str
    mapped_ids: dict[Union[int, Literal["_"]], int]


class FilterDict(TypedDict):
    name: str
    func: HIDMessageFilter


DEVICES_CONFIG_FILE_NAME = 'devices_config.json'
DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY = 'compatibility_devices'
CAPTURE_ELEMENT: Literal['capture'] = 'capture'
FILTER_ELEMENT: Literal['filter'] = 'filter'
FILTERS_PATH = Path(__file__).parent / "filters"
REPORT_ID_PATTERN = re.compile(r"(a10185)(..)")
SDP_TEMPLATE_PATH = Path(__file__).with_name("sdp_record_template.xml")
SDP_OUTPUT_PATH = Path("/etc/bluetooth/sdp_record.xml")

FILTERS: dict[str, FilterDict] = {"_": {"name": "No filter", "func": lambda m: m}}
for mod_path in FILTERS_PATH.glob("*.py"):
    if mod_path.stem == "__init__":
        continue
    mod = importlib.import_module("filters." + mod_path.stem)
    name = mod.__doc__ or mod_path.stem.replace("_", " ").capitalize()
    FILTERS[mod_path.stem] = {"name": name, "func": mod.message_filter}


# https://github.com/bentiss/hid-tools/blob/59a0c4b153dbf7d443e63bf68ff830b8353f5f7a/hidtools/hidraw.py#L33-L104

_IOC_READ = 2
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

def _IORH(nr: int, size: int) -> int:
    return (
        (_IOC_READ << _IOC_DIRSHIFT)
        | (ord("H") << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )

def _IOC_HIDIOCGRDESCSIZE(length: int) -> int:
    return _IORH(0x01, length)

def _ioctl_desc_size(fd: int) -> tuple[int]:
    size = struct.calcsize("i")
    abs = fcntl.ioctl(fd, _IOC_HIDIOCGRDESCSIZE(size), size * b"\x00")
    return cast(tuple[int], struct.unpack("i", abs))

def _IOC_HIDIOCGRDESC(length: int) -> int:
    return _IORH(0x02, length)

def _HIDIOCGRDESC(fd: int) -> "array.array[int]":
    """Get report descriptor."""
    size = int(*_ioctl_desc_size(fd))

    _buffer = array.array("B", struct.pack("i", size) + bytes(4096))
    fcntl.ioctl(fd, _IOC_HIDIOCGRDESC(struct.calcsize("I4096c")), _buffer)
    (size,) = cast(tuple[int], struct.unpack("i", _buffer[:4]))
    return _buffer[4 : size + 4]



class HIDDevice:
    mapped_ids: dict[Union[int, Literal["_"]], bytes]

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
        desc = "".join(f"{b:02x}" for b in _HIDIOCGRDESC(self.hidraw_file))
        # Replace report IDs, so they can be remapped later.
        self.internal_ids = tuple(m[1] for m in cast(list[str], REPORT_ID_PATTERN.findall(desc)))
        self.descriptor, found = REPORT_ID_PATTERN.subn(r"\1{}", desc)
        # Or insert one if no report ID exists.
        if found == 0:
            self.descriptor = re.sub(r"(a101)", r"\g<1>85{}", self.descriptor, count=1)

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
        tm = self.filter(msg)
        if tm is None or self.device_registry.bluetooth_devices is None:
            return
        if tm == b'\xff':
            self.device_registry.bluetooth_devices.switch_host()
            self.indicate_switch_with_mouse_movement()
        else:
            if self.internal_ids:
                tm = b"\xa1" + self.mapped_ids[tm[0]] + tm[1:]
            else:
                tm = b"\xa1" + self.mapped_ids["_"] + tm
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
        if self.hidraw_file is not None:
            os.write(self.hidraw_file, msg[1:])

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

                        device_id = device.split(".")[0]
                        devs.append({"id": device_id, "instance": device,
                                     "name": name, "hidraw": hidraw, "events": events,
                                     "compatibility_mode": compatibility_mode})
                        devs_dict[device] = device_id
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

        recreate_sdp = False
        # Refresh or create config details for currently connected devices.
        for hid_dev in self.capturing_devices.values():
            dev_config = self.devices_config.get(hid_dev.device_class)
            if not dev_config:
                dev_config = {}
                self.devices_config[hid_dev.device_class] = dev_config
                recreate_sdp = True

            dev_config["descriptor"] = hid_dev.descriptor
            # TODO(PY311): Use to_bytes() defaults.
            # Need tuple to retain order (set is unordered, but dict is ordered).
            keys: tuple[Union[int, Literal["_"]], ...] = tuple(int(i, base=16) for i in hid_dev.internal_ids) if hid_dev.internal_ids else ("_",)
            if dev_config.get("mapped_ids", {}).keys() != set(keys):
                dev_config["mapped_ids"] = {i: 0 for i in keys}
                recreate_sdp = True

        # We need to avoid editing the SDP when possible as this requires restarting
        # bluez (therefore disconnecting all BT devices).
        if recreate_sdp:
            report_desc = ""
            report_id = 1
            for dev_config in self.devices_config.values():
                for k in dev_config["mapped_ids"]:
                    dev_config["mapped_ids"][k] = report_id
                    report_id += 1
                report_desc += dev_config["descriptor"]
            report_desc = report_desc.format(*(f"{i:02x}" for i in range(1, report_id)))

            sdp = SDP_TEMPLATE_PATH.read_text().format(report_desc)
            SDP_OUTPUT_PATH.write_text(sdp)
            self.__save_config()
            # TODO: Try reconnecting devices after restart.
            subprocess.Popen(("systemctl", "restart", "bluetooth"), stderr=sys.stderr)

        # Update the mapped IDs based on latest information.
        for hid_dev in self.capturing_devices.values():
            config_ids = self.devices_config[hid_dev.device_class]["mapped_ids"]
            hid_dev.mapped_ids = {k: v.to_bytes(1, "big") for k,v in config_ids.items()}
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
                return FILTERS[filter_id]["func"]
        return FILTERS["_"]["func"]

    def get_hid_devices_with_config(self) -> _HIDDevices:
        for device in self.devices:
            if device["id"] in self.devices_config:
                device[CAPTURE_ELEMENT] = self.devices_config[device["id"]].get(CAPTURE_ELEMENT, False)
                if FILTER_ELEMENT in self.devices_config[device["id"]]:
                    device[FILTER_ELEMENT] =  self.devices_config[device["id"]][FILTER_ELEMENT]
        f = tuple({"id": k, "name": v["name"]} for k,v in FILTERS.items())
        return {"devices": self.devices, "filters": f, "input_devices": self.input_devices}
