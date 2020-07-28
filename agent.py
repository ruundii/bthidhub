# Copyright (c) 2020 ruundii. All rights reserved.

import dasbus.typing as dt
from dasbus.server.interface import dbus_interface
from dasbus.connection import SystemMessageBus

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
    def Release(self):
        print("Agent Release")

    def AuthorizeService(self, device:dt.ObjPath, uuid:dt.Str):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if (authorize == "yes"):
            set_trusted(device)
            return
        raise Exception("Connection rejected by user")

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

    def DisplayPinCode(self, device:dt.ObjPath, pincode:dt.Str):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    def RequestConfirmation(self, device:dt.ObjPath, passkey:dt.UInt32):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("Confirm passkey (yes/no): ")
        if (confirm == "yes"):
            set_trusted(device)
            return
        raise Exception("Passkey doesn't match")

    def RequestAuthorization(self, device:dt.ObjPath):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if (auth == "yes"):
            return
        raise Exception("Pairing rejected")

    def Cancel(self):
        print("Cancel")

