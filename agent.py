# Copyright (c) 2020 ruundii. All rights reserved.

import dasbus.typing as dt
from dasbus.server.interface import dbus_interface
from dasbus.connection import SystemMessageBus
from datetime import datetime, timedelta
import asyncio

bus = SystemMessageBus()

def ask(prompt):
	return input(prompt)

def set_trusted(device_path):
    device = bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name="org.bluez.Device1")
    device.Trusted = True

def dev_connect(device_path):
    device = bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name="org.bluez.Device1")
    device.Connect()


@dbus_interface("org.bluez.Agent1")
class Agent(object):
    def __init__(self):
        self.on_agent_action_handler = None
        self.request_confirmation_device = None
        self.request_confirmation_passkey = None

    def Release(self):
        self.on_agent_action({'action':'agent_released'})
        print("Agent Release")

    def AuthorizeService(self, device:dt.ObjPath, uuid:dt.Str):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        set_trusted(device)
        self.on_agent_action({'action':'service_autorised', 'device':device})
        # authorize = ask("Authorize connection (yes/no): ")
        # if (authorize == "yes"):
        #     set_trusted(device)
        #     return
        # raise Exception("Connection rejected by user")

    def RequestPinCode(self, device:dt.ObjPath) -> dt.Str:
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    def RequestPasskey(self, device:dt.ObjPath) -> dt.UInt32:
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = int(ask("Enter passkey: "))
        return dt.UInt32(passkey)

    def DisplayPasskey(self, device:dt.ObjPath, passkey:dt.UInt32, entered:dt.UInt16):
        print("DisplayPasskey (%s, %06u entered %u)" %
              (device, passkey, entered))
        self.on_agent_action({'action':'display_passkey', 'passkey':passkey, 'device':device, 'entered':entered})

    def DisplayPinCode(self, device:dt.ObjPath, pincode:dt.Str):
        print("DisplayPinCode (%s, %s)" % (device, pincode))
        self.on_agent_action({'action':'display_pin_code', 'pincode':pincode, 'device':device})

    def RequestConfirmation(self, device:dt.ObjPath, passkey:dt.UInt32):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        self.request_confirmation_device = device
        self.request_confirmation_passkey = str(passkey).zfill(6)
        self.on_agent_action({'action':'confirm_passkey', 'passkey':str(passkey).zfill(6), 'device':device})

    def request_confirmation_response(self, device, passkey, confirmed):
        if self.request_confirmation_device == device and passkey==self.request_confirmation_passkey and confirmed:
            set_trusted(device)
        else:
            self.request_confirmation_device = None
            self.request_confirmation_passkey = None

    def RequestAuthorization(self, device:dt.ObjPath):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if (auth == "yes"):
            return
        raise Exception("Pairing rejected")

    def Cancel(self):
        self.on_agent_action({'action':'agent_cancel'})
        print("Cancel")

    def on_agent_action(self, msg):
        if self.on_agent_action_handler is not None:
            self.on_agent_action_handler(msg)

    def set_on_agent_action_handler(self, handler):
        self.on_agent_action_handler = handler
