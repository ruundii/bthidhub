# Copyright (c) 2020 ruundii. All rights reserved.

from aiohttp import web,WSMessage
from password import *
import json
from hid_devices import *
from bluetooth_devices import *
import asyncio
import concurrent.futures
import sys
import subprocess

from aiohttp_session import SimpleCookieStorage, session_middleware
from aiohttp_security import check_authorized, \
    is_anonymous, authorized_userid, remember, forget, \
    setup as setup_security, SessionIdentityPolicy
from aiohttp_security.abc import AbstractAuthorizationPolicy

PI_USER = 'pi'

class PiAuthorizationPolicy(AbstractAuthorizationPolicy):
    async def authorized_userid(self, identity):
        """Retrieve authorized user id.
        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        if identity == PI_USER:
            return identity

    async def permits(self, identity, permission, context=None):
        """Check user permissions.
        Return True if the identity is allowed the permission
        in the current context, else return False.
        """
        return identity == PI_USER

class Web:
    def __init__(self, loop: asyncio.AbstractEventLoop, adapter, bluetooth_devices:BluetoothDeviceRegistry, hid_devices: HIDDeviceRegistry):
        self.loop = loop
        self.adapter = adapter
        self.adapter.set_on_agent_action_handler(self.on_agent_action)
        self.adapter.set_on_interface_changed_handler(self.on_adapter_interface_changed)
        self.hid_devices = hid_devices
        self.hid_devices.set_on_devices_changed_handler(self.on_hid_devices_change)
        self.bluetooth_devices = bluetooth_devices
        self.bluetooth_devices.set_on_devices_changed_handler(self.on_bluetooth_devices_change)
        middleware = session_middleware(SimpleCookieStorage())
        self.app = web.Application(middlewares=[middleware])
        self.app.router.add_route('*', '/', self.root_handler)
        self.app.router.add_route('POST', '/changepassword', self.change_password_handler)
        self.app.router.add_route('POST', '/restartservice', self.restart_service_handler)
        self.app.router.add_route('POST', '/reboot', self.reboot_handler)
        self.app.router.add_route('POST', '/login', self.handler_login)
        self.app.router.add_route('GET', '/authorised', self.handler_is_authorised)
        self.app.router.add_route('POST', '/setdevicecapture', self.set_device_capture)
        self.app.router.add_route('POST', '/setdevicefilter', self.set_device_filter)
        self.app.router.add_route('POST', '/setcompatibilitydevice', self.set_compatibility_device)
        self.app.router.add_route('POST', '/startscanning', self.start_scanning)
        self.app.router.add_route('POST', '/stopscanning', self.stop_scanning)
        self.app.router.add_route('POST', '/startdiscoverable', self.start_discoverable)
        self.app.router.add_route('POST', '/stopdiscoverable', self.stop_discoverable)
        self.app.router.add_route('GET', '/hiddevices', self.get_hid_devices_handler)
        self.app.router.add_route('GET', '/bluetoothdevices', self.get_bluetooth_devices)
        self.app.router.add_routes([web.get('/ws', self.websocket_handler)])
        self.app.router.add_static('/',"web/")# add_routes([web.get('/', self.hello)])

        policy = SessionIdentityPolicy()
        setup_security(self.app, policy, PiAuthorizationPolicy())

        self.runner = None
        self.site = None
        self.ws = set()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        #web.run_app(self.app)
        asyncio.run_coroutine_threadsafe(self.start_server(), loop=self.loop)

    async def handler_login(self, request):
        data = await request.post()
        password = data['password']
        if(is_valid_current_password(PI_USER, password)):
            redirect_response = web.HTTPFound('/')
            await remember(request, redirect_response, PI_USER)
            raise redirect_response
        else:
            raise web.HTTPUnauthorized()

    async def handler_is_authorised(self, request):
        await check_authorized(request)
        return web.Response()

    async def on_hid_devices_change(self):
        for ws in self.ws:
            try:
                await asyncio.wait_for(ws.send_json({"msg": "hid_devices_updated"}), 5)
            except (asyncio.TimeoutError, RuntimeError):
                self.ws.discard(ws)
                await ws.close()

    async def on_bluetooth_devices_change(self):
        for ws in self.ws:
            await ws.send_json({'msg': 'bt_devices_updated'})

    async def start_server(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, None, 8080)
        await self.site.start()

    async def root_handler(self, request):
        return web.HTTPFound('/index.html')

    async def change_password_handler(self, request):
        await check_authorized(request)
        data = await request.post()
        current_password = data['current_password']
        new_password = data['new_password']
        if not is_valid_current_password(PI_USER, current_password):
            return web.HTTPUnauthorized()
        if not set_new_password(PI_USER, new_password):
            return web.HTTPError
        return web.Response(text="Password successfully changed")

    async def restart_service_handler(self, request):
        await check_authorized(request)
        sys.exit(1)

    async def reboot_handler(self, request):
        await check_authorized(request)
        subprocess.Popen(['reboot'])

    async def get_hid_devices_handler(self, request):
        await check_authorized(request)
        return web.Response(text=json.dumps(self.hid_devices.get_hid_devices_with_config()))

    async def set_device_capture(self, request):
        await check_authorized(request)
        data = await request.post()
        device_id = data['device_id']
        capture_state = data['capture'].lower() == 'true'
        self.hid_devices.set_device_capture(device_id, capture_state)
        return web.Response()

    async def set_device_filter(self, request):
        await check_authorized(request)
        data = await request.post()
        device_id = data['device_id']
        filter = data['filter']
        self.hid_devices.set_device_filter(device_id, filter)
        return web.Response()

    async def set_compatibility_device(self, request):
        await check_authorized(request)
        data = await request.post()
        device_path = data['device_path']
        compatibility_state = data['compatibility_state'].lower() == 'true'
        self.hid_devices.set_compatibility_device(device_path, compatibility_state)
        return web.Response()


    async def start_scanning(self, request):
        await check_authorized(request)
        try:
            self.adapter.start_scan()
        except Exception as exc:
            return web.HTTPError(reason=str(exc))
        return web.Response()

    async def stop_scanning(self, request):
        await check_authorized(request)
        try:
            self.adapter.stop_scan()
        except Exception as exc:
            return web.HTTPError(reason=str(exc))
        return web.Response()


    async def start_discoverable(self, request):
        await check_authorized(request)
        try:
            self.adapter.start_discoverable()
        except Exception as exc:
            return web.HTTPError(reason=str(exc))
        return web.Response()

    async def stop_discoverable(self, request):
        await check_authorized(request)
        try:
            self.adapter.stop_discoverable()
        except Exception as exc:
            return web.HTTPError(reason=str(exc))
        return web.Response()

    async def get_bluetooth_devices(self, request):
        await check_authorized(request)
        return web.Response(text=json.dumps(self.adapter.get_devices()))

    async def on_agent_action(self, msg):
        for ws in self.ws:
            asyncio.run_coroutine_threadsafe(ws.send_json({'msg': 'agent_action', 'data':msg}), loop=self.loop)

    async def on_adapter_interface_changed(self):
        for ws in self.ws:
            asyncio.run_coroutine_threadsafe(ws.send_json({'msg': 'bt_devices_updated'}), loop=self.loop)

    async def websocket_handler(self, request):
        await check_authorized(request)
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.ws.add(ws)
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if 'msg' in data:
                        if data['msg'] == 'close' or data['msg'] == 'shutdown':
                            await ws.close()
                        elif data['msg'] == 'connect':
                            await ws.send_json({'msg':'connected'})
                            print('websocket connection opened')
                        elif data['msg'] == 'cancel_pairing':
                            self.adapter.cancel_pairing(data['device'])
                        elif data['msg'] == 'request_confirmation_response':
                            self.adapter.agent_request_confirmation_response(data['device'], data['passkey'], data['confirmed'])
                        elif data['msg'] == 'pair_device':
                            print("pairing")
                            self.loop.run_in_executor(self.executor, self.adapter.device_action, 'pair', data['device'])
                            print("pairing end")
                        elif data['msg'] == 'connect_device':
                            self.loop.run_in_executor(self.executor, self.adapter.device_action, 'connect', data['device'])
                        elif data['msg'] == 'disconnect_device':
                            self.loop.run_in_executor(self.executor, self.adapter.device_action, 'disconnect', data['device'])
                        elif data['msg'] == 'remove_device':
                            self.loop.run_in_executor(self.executor, self.adapter.remove_device, data['device'])
                        else:
                            pass
                            #await ws.send_json({'msg':'connected'})
                elif msg.type == web.WSMsgType.ERROR:
                    print('ws connection closed with exception %s' %
                          ws.exception())
        finally:
            self.ws.discard(ws)
        print('websocket connection closed')
        return ws
