# Copyright (c) 2020 ruundii. All rights reserved.

from dasbus.connection import SystemMessageBus
import dasbus.typing as dt
import sys
from dasbus.server.interface import dbus_interface
#from dasbus.loop import EventLoop
from agent import Agent
import socket
import threading

import asyncio, gbulb
gbulb.install()
#import asyncio_glib
#asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())

# UUID for HID service (1124)
# https://www.bluetooth.com/specifications/assigned-numbers/service-discovery
UUID = '00001124-0000-1000-8000-00805f9b34fb'
DBUS_PATH_PROFILE = '/ruundii/btkb_profile'
DBUS_PATH_AGENT = '/ruundii/btkb_agent'
ADAPTER_OBJECT = '/org/bluez/hci0'
DEVICE_NAME = 'Bluetooth HID Hub - Ubuntu'
PORT_CTRL = 0x11  # Service port - must match port configured in SDP record
PORT_INTR = 0x13  # Service port - must match port configured in SDP record#Interrrupt port

bus = SystemMessageBus()
loop = asyncio.get_event_loop()


@dbus_interface("org.bluez.Profile1")
class MyProfile(object):
    connection = None

    def Release(self):
        print("Release")

    def Cancel(self):
        print("Cancel")

    def NewConnection(self, path:dt.ObjPath, fd:dt.File, properties:dt.Dict[dt.Str, dt.Variant]):
        print("New Connection",path,fd,properties)
        sckt = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        sckt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to a port - port zero to select next available
        sckt.bind((socket.BDADDR_ANY, PORT_INTR))
        # Start listening on the server sockets
        sckt.listen(5)
        self.cinterrupt, cinfo = sckt.accept()
        print("Got a connection on the interrupt channel from %s " % cinfo[0])
        asyncio.ensure_future(self.loop_of_fun())
        print("NewConnection finish")
        print("NewConnection thread",threading.currentThread().getName())

    def RequestDisconnection(self, path:dt.Str):
        print("RequestDisconnection")

    async def loop_of_fun(self):
        print("loop_of_fun")
        await asyncio.sleep(5)
        for i in range(1, 100):
            print("sending Hi")
            self.cinterrupt.send(bytes(bytearray([0xA1, 0x01, 0x00, 0x00, 0x0B, 0x0C, 0x00, 0x00, 0x00, 0x00])))
            # cinterrupt.send(bytes(bytearray([0xA1, 0x01, 0x00, 0x00, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])))
            self.cinterrupt.send(bytes(bytearray([0xA1, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])))
            self.cinterrupt.send(bytes(bytearray([0xA1, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])))
            await asyncio.sleep(10)

class BluetoothAdapter:
    def __init__(self):
        self.om = bus.get_proxy(service_name= "org.bluez", object_path="/", interface_name="org.freedesktop.DBus.ObjectManager")
        self.om.InterfacesAdded.connect(self.interfaces_added)
        self.om.InterfacesRemoved.connect(self.interfaces_removed)

        self.agent = Agent()
        bus.publish_object(DBUS_PATH_AGENT, self.agent)
        agent_manager = bus.get_proxy(service_name="org.bluez", object_path="/org/bluez",
                                      interface_name="org.bluez.AgentManager1")
        agent_manager.RegisterAgent(DBUS_PATH_AGENT, "KeyboardOnly")

        objs = self.om.GetManagedObjects()
        if ADAPTER_OBJECT in objs:
            print("Adapter ",ADAPTER_OBJECT, " found")
            self.init_adapter()
        else:
            print("Adapter ",ADAPTER_OBJECT, " not found. Please make sure you have Bluetooth Adapter installed and plugged in")
            self.adapter = None

    def init_adapter(self):
        self.adapter = bus.get_proxy(service_name="org.bluez", object_path=ADAPTER_OBJECT,
                                     interface_name="org.bluez.Adapter1")

        if self.adapter is None:
            print("Adapter not found")
            return
        if not self.powered:
            print("Bluetooth adapter is turned off. Trying to turn on")
            try:
                self.powered = True
                if(self.powered):
                    print("Successfully turned on")
                else:
                    print("Failed to turn on. Please turn on Bluetooth in the system")
                    return

            except Exception:
                print("Failed to turn on. Please turn on Bluetooth in the system")
                return
        agent_manager = bus.get_proxy(service_name="org.bluez", object_path="/org/bluez",
                                      interface_name="org.bluez.AgentManager1")
        agent_manager.RequestDefaultAgent(DBUS_PATH_AGENT)
        print("Agent registered")
        self.alias = DEVICE_NAME
        self.discoverable = True
        self.discoverable_timeout = 0

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


    def interfaces_added(self, interface_name, properties):
        if(interface_name==ADAPTER_OBJECT):
            print("Bluetooth adapter added. Starting")
            self.init_adapter()

    def interfaces_removed(self, interface_name, properties):
        if(interface_name==ADAPTER_OBJECT):
            self.adapter = None
            print("Bluetooth adapter removed. Stopping")


def read_sdp_service_record():
    """
    Read and return SDP record from a file
    :return: (string) SDP record
    """
    print('Reading service record')
    try:
        fh = open("sdp_record.xml", 'r')
    except OSError:
        sys.exit('Could not open the sdp record. Exiting...')

    return fh.read()



opts = {
    'Name':  dt.get_variant(dt.Str,DEVICE_NAME),
    'Role':  dt.get_variant(dt.Str,'server'),
    'RequireAuthentication': dt.get_variant(dt.Bool, False),
    'RequireAuthorization': dt.get_variant(dt.Bool, True),
    'PSM': dt.get_variant(dt.UInt16, PORT_CTRL),
    'AutoConnect': dt.get_variant(dt.Bool, True),
    'ServiceRecord': dt.get_variant(dt.Str, read_sdp_service_record()),
    'HIDProfileId' :dt.get_variant(dt.UInt16, 1),
}
if __name__ == "__main__":

    #bus.publish_object(DBUS_PATH_PROFILE,p)
    #profile_manager = bus.get_proxy(service_name= "org.bluez", object_path="/org/bluez", interface_name="org.bluez.ProfileManager1")
    #profile_manager.RegisterProfile(DBUS_PATH_PROFILE, UUID, opts)
    #print('Profile registered')

    a = BluetoothAdapter()
    loop.run_forever()


#print(proxy)