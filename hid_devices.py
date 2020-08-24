# Copyright (c) 2020 ruundii. All rights reserved.

import os
import re
import json
from watchgod import awatch, AllWatcher
import asyncio
import evdev
from hid_message_filter import HIDMessageFilter
from a1314_message_filter import A1314MessageFilter
from mouse_message_filter import MouseMessageFilter
from typing import Dict, List
from compatibility_device import CompatibilityModeDevice

DEVICES_CONFIG_FILE_NAME = 'devices_config.json'
DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY = 'compatibility_devices'
CAPTURE_ELEMENT = 'capture'
FILTER_ELEMENT = 'filter'

FILTERS = [
    {"id":"Default", "name":"Default"},
    {"id":"Mouse", "name":"Mouse"},
    {"id":"A1314", "name":"A1314"}
]

FILTER_INSTANCES = {
"Default" : HIDMessageFilter(), "Mouse":MouseMessageFilter(), "A1314":A1314MessageFilter()
}

class HIDDevice:
    def __init__(self, device, filter, loop: asyncio.AbstractEventLoop, device_registry):
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
        self.hidraw_file = os.open('/dev/'+self.hidraw, os.O_RDWR | os.O_NONBLOCK)
        loop.add_reader(self.hidraw_file, self.hidraw_event)
        print("HID Device ",self.device_id," created")

    def set_device_filter(self, filter):
        self.filter = filter

    def hidraw_event(self):
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
        else:
            self.device_registry.bluetooth_devices.send_message(tm, True, False)

    async def send_message(self, msg):
        tm = self.filter.filter_message_from_host(msg)
        if tm is not None and self.hidraw_file is not None:
            try:
                await os.write(self.hidraw_file, tm)
            except:
                pass

    def __eq__(self, other):
        return self.device_id == other.device_id

    def finalise(self):
        #close file
        for event_device in self.events_devices:
            try:
                event_device.ungrab()
            except:
                pass
        try:
            self.loop.remove_reader(self.hidraw_file)
            os.close(self.hidraw_file)
            self.hidraw_file = None
        except:
            pass
        print("HID Device ",self.device_id," finalised")

    def __del__(self):
        print("HID Device ",self.device_id," removed")

class DeviceDirWatcher(AllWatcher):
    def should_watch_dir(self, entry):
        return entry.path.count('/') == 3

class HIDDeviceRegistry:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        if os.path.exists(DEVICES_CONFIG_FILE_NAME):
            with open(DEVICES_CONFIG_FILE_NAME, 'r') as devices_config:
                self.devices_config = json.loads(devices_config.read())
        else: self.devices_config = {}
        self.devices = []
        self.capturing_devices = {}
        self.input_devices = []
        self.compatibility_mode_devices = {}
        asyncio.run_coroutine_threadsafe(self.__watch_device_changes(), loop=self.loop)
        self.on_devices_changed_handler = None
        self.__scan_devices()
        self.bluetooth_devices = None

    def set_bluetooth_devices(self, bluetooth_devices):
        self.bluetooth_devices = bluetooth_devices

    def set_on_devices_changed_handler(self, handler):
        self.on_devices_changed_handler = handler

    async def send_message_to_devices(self, msg):
        for device in self.capturing_devices.values():
            await device.send_message(msg)

    async def __watch_device_changes(self):
        async for changes in awatch('/dev/input', watcher_cls=DeviceDirWatcher):
            self.__scan_devices()
            if self.on_devices_changed_handler is not None:
                await self.on_devices_changed_handler()

    def __scan_devices(self):
        #input_devices
        self.input_devices = []
        evdevs = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in filter(lambda d: 1 in d.capabilities().keys() and 1 in d.capabilities()[1] and d.info.bustype!=0x06, #filter out devices without key capability and without esc button
                                             [evdev.InputDevice(path) for path in evdev.list_devices()]):
            compatibility_mode = DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY in self.devices_config and dev.path in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]
            self.input_devices.append({"name": dev.name, "path": dev.path, "phys": dev.phys, "compatibility_mode":compatibility_mode})
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

        devs = []
        devs_dict = {}
        devs_in_compatibility_mode = []
        for device in os.listdir('/sys/bus/hid/devices'):
            with open('/sys/bus/hid/devices/'+device+'/uevent', 'r') as uevent:
                name = re.search('HID_NAME\s*=(.+)', uevent.read()).group(1)
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
        devs_to_remove = []
        for dev in self.capturing_devices:
            if dev not in devs_dict or not self.__is_configured_capturing_device(devs_dict[dev]) or dev in devs_in_compatibility_mode:
                #remove capturing device
                devs_to_remove.append(dev)

        for dev in devs_to_remove:
            hid_device = self.capturing_devices[dev]
            del self.capturing_devices[dev]
            hid_device.finalise()
            del hid_device

        for dev in devs:
            if dev["instance"] not in self.capturing_devices and self.__is_configured_capturing_device(dev["id"]) and dev not in devs_in_compatibility_mode:
                #create capturing device
                self.capturing_devices[dev["instance"]] = HIDDevice(dev, self.__get_configured_device_filter(dev["id"]), self.loop, self)
        self.devices = devs


    def set_device_capture(self, device_id, capture):
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][CAPTURE_ELEMENT] = capture
        self.__save_config()
        self.__scan_devices()

    def set_device_filter(self, device_id, filter_id):
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][FILTER_ELEMENT] = filter_id
        self.__save_config()
        filter = self.__get_configured_device_filter(device_id)
        for dev in self.capturing_devices:
            if self.capturing_devices[dev].device_class == device_id:
                self.capturing_devices[dev].set_device_filter(filter)

    def set_compatibility_device(self, device_path, compatibility_state):
        if DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY not in self.devices_config:
            self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY] = []
        if compatibility_state and device_path not in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]:
            self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY].append(device_path)
        elif not compatibility_state and device_path in self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY]:
            self.devices_config[DEVICES_CONFIG_COMPATIBILITY_DEVICE_KEY].remove(device_path)
        self.__save_config()
        self.__scan_devices()

    def __save_config(self):
        with open(DEVICES_CONFIG_FILE_NAME, 'w') as devices_config_file:
            devices_config_file.write(json.dumps(self.devices_config))

    def __is_configured_capturing_device(self, device_id):
        if device_id in self.devices_config:
            if CAPTURE_ELEMENT in self.devices_config[device_id]:
                return self.devices_config[device_id][CAPTURE_ELEMENT]
        return False

    def __get_configured_device_filter(self, device_id):
        if device_id in self.devices_config:
            if FILTER_ELEMENT in self.devices_config[device_id]:
                filter_id = self.devices_config[device_id][FILTER_ELEMENT]
                return FILTER_INSTANCES[filter_id]
        return FILTER_INSTANCES["Default"]

    def get_hid_devices_with_config(self):
        result = {}
        for device in self.devices:
            if device["id"] in self.devices_config:
                if CAPTURE_ELEMENT in self.devices_config[device["id"]]:
                    device[CAPTURE_ELEMENT] =  self.devices_config[device["id"]][CAPTURE_ELEMENT]
                else:
                    device[CAPTURE_ELEMENT] = False
                if FILTER_ELEMENT in self.devices_config[device["id"]]:
                    device[FILTER_ELEMENT] =  self.devices_config[device["id"]][FILTER_ELEMENT]
        result["devices"] = self.devices
        result["filters"] = FILTERS
        result["input_devices"] = self.input_devices
        return result


