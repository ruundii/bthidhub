# Copyright (c) 2020 ruundii. All rights reserved.

import os
import re
import json

DEVICES_CONFIG_FILE_NAME = 'devices_config.json'
CAPTURE_ELEMENT = 'capture'
FILTER_ELEMENT = 'filter'

FILTERS = [
    {"id":"Default", "name":"No Filter"},
    {"id":"A1314", "name":"A1314"}
]

class MachineDevices:
    def __init__(self):
        if os.path.exists(DEVICES_CONFIG_FILE_NAME):
            with open(DEVICES_CONFIG_FILE_NAME, 'r') as devices_config:
                self.devices_config = json.loads(devices_config.read())
        else: self.devices_config = {}

    def __get_hid_devices(self):
        devs = []
        for device in os.listdir('/sys/bus/hid/devices'):
            with open('/sys/bus/hid/devices/'+device+'/uevent', 'r') as uevent:
                name = re.search('HID_NAME\s*=(.+)', uevent.read()).group(1)
                hidraw = os.listdir('/sys/bus/hid/devices/'+device+'/hidraw')[0]
                inputs = os.listdir('/sys/bus/hid/devices/'+device+'/input')
                devs.append({"id":device.split('.')[0], "name":name, "hidraw": hidraw, "inputs":inputs})
        return devs

    def set_device_capture(self, device_id, capture):
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][CAPTURE_ELEMENT] = capture
        self.__save_config()

    def set_device_filter(self, device_id, filter_id):
        if device_id not in self.devices_config: self.devices_config[device_id] = {}
        self.devices_config[device_id][FILTER_ELEMENT] = filter_id
        self.__save_config()

    def __save_config(self):
        with open(DEVICES_CONFIG_FILE_NAME, 'w') as devices_config_file:
            devices_config_file.write(json.dumps(self.devices_config))

    def get_hid_devices_with_config(self):
        result = {}
        devs = self.__get_hid_devices()
        for device in devs:
            if device["id"] in self.devices_config:
                if CAPTURE_ELEMENT in self.devices_config[device["id"]]:
                    device[CAPTURE_ELEMENT] =  self.devices_config[device["id"]][CAPTURE_ELEMENT]
                else:
                    device[CAPTURE_ELEMENT] = False
                if FILTER_ELEMENT in self.devices_config[device["id"]]:
                    device[FILTER_ELEMENT] =  self.devices_config[device["id"]][FILTER_ELEMENT]
        result["devices"] = devs
        result["filters"] = FILTERS
        return result

# m = MachineDevices()
# devs = m.get_hid_devices_with_config()
# print(devs)

