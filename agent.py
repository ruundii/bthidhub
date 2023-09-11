# Copyright (c) 2020 ruundii. All rights reserved.

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional, TypedDict

import dasbus.typing as dt
from dasbus.server.interface import dbus_interface
from dasbus.connection import SystemMessageBus


class Action(TypedDict, total=False):
    action: str
    device: dt.ObjPath
    entered: dt.UInt16
    passkey: str
    pincode: str


bus = SystemMessageBus()

def ask(prompt: str) -> str:
	return input(prompt)

def set_trusted(device_path: str) -> None:
    device = bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name="org.bluez.Device1")
    device.Trusted = True

def dev_connect(device_path: str) -> None:
    device = bus.get_proxy(service_name="org.bluez", object_path=device_path, interface_name="org.bluez.Device1")
    device.Connect()


# Decorator won't work with compiled class as it depends on introspection.
# If you update anything in this class, then uncomment the below line, and add a
# print(self.__dbus_xml__) into the init method. Then copy and paste the updated string
# to replace the hardcoded one below.
#@dbus_interface("org.bluez.Agent1")
class Agent:
    def __init__(self) -> None:
        self.on_agent_action_handler: Optional[Callable[[Action], None]] = None
        self.request_confirmation_device: Optional[dt.ObjPath] = None
        self.request_confirmation_passkey: Optional[str] = None
        self.__dbus_xml__ = '<node><!--Specifies Agent--><interface name="org.bluez.Agent1"><method name="AuthorizeService"><arg name="device" type="o" direction="in" /><arg name="uuid" type="s" direction="in" /></method><method name="Cancel" /><method name="DisplayPinCode"><arg name="device" type="o" direction="in" /><arg name="pincode" type="s" direction="in" /></method><method name="Release" /><method name="RequestAuthorization"><arg name="device" type="o" direction="in" /></method><method name="RequestConfirmation"><arg name="device" type="o" direction="in" /><arg name="passkey" type="u" direction="in" /></method><method name="RequestPasskey"><arg name="device" type="o" direction="in" /><arg name="return" type="u" direction="out" /></method><method name="RequestPinCode"><arg name="device" type="o" direction="in" /><arg name="return" type="s" direction="out" /></method></interface></node>'

    def Release(self) -> None:
        self.on_agent_action({'action':'agent_released'})
        print("Agent Release")

    def AuthorizeService(self, device: dt.ObjPath, uuid: dt.Str) -> None:
        print("AuthorizeService (%s, %s)" % (device, uuid))
        set_trusted(device)
        self.on_agent_action({'action':'service_autorised', 'device':device})
        # authorize = ask("Authorize connection (yes/no): ")
        # if (authorize == "yes"):
        #     set_trusted(device)
        #     return
        # raise Exception("Connection rejected by user")

    def RequestPinCode(self, device: dt.ObjPath) -> dt.Str:
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    def RequestPasskey(self, device: dt.ObjPath) -> dt.UInt32:
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = int(ask("Enter passkey: "))
        return dt.UInt32(passkey)

    def DisplayPinCode(self, device: dt.ObjPath, pincode: dt.Str) -> None:
        print("DisplayPinCode (%s, %s)" % (device, pincode))
        self.on_agent_action({'action':'display_pin_code', 'pincode':pincode, 'device':device})

    def RequestConfirmation(self, device: dt.ObjPath, passkey: dt.UInt32) -> None:
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        self.request_confirmation_device = device
        self.request_confirmation_passkey = str(passkey).zfill(6)
        self.on_agent_action({'action':'confirm_passkey', 'passkey':str(passkey).zfill(6), 'device':device})

    def request_confirmation_response(self, device: str, passkey: str, confirmed: bool) -> None:
        if self.request_confirmation_device == device and passkey==self.request_confirmation_passkey and confirmed:
            set_trusted(device)
        else:
            self.request_confirmation_device = None
            self.request_confirmation_passkey = None

    def RequestAuthorization(self, device: dt.ObjPath) -> None:
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if (auth != "yes"):
            raise Exception("Pairing rejected")

    def Cancel(self) -> None:
        self.on_agent_action({'action':'agent_cancel'})
        print("Cancel")

    def on_agent_action(self, msg: Action) -> None:
        if self.on_agent_action_handler is not None:
            self.on_agent_action_handler(msg)

    def set_on_agent_action_handler(self, handler: Callable[[Action], None]) -> None:
        self.on_agent_action_handler = handler
