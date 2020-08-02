var socket = null;
var connected = false;
var isAttemptingToConnect = false;
var isRefreshing = false;


var STATE_CONNECTING = "connecting";
var STATE_CONNECTED = "connected";
var STATE_DISCONNECTED = "disconnected";


class WebSocketManager{
    constructor(agent, main) {
        this.agent = agent;
        this.agent.setWebSocketManager(this);
        this.main = main;
        this.connect();
    }

    async connect(){
        var that = this;
        return new Promise(function(resolve, reject) {
            isAttemptingToConnect = true;
            socket = new WebSocket("ws://" + location.hostname + ":8080/ws");
            socket.onopen = function () {
                that.changeConnectedState(true);
                console.log('client side socket open');
                socket.send(JSON.stringify({"msg": "connect"}));
                resolve();
            };
            socket.onerror = function (e) {
                M.toast({html: "Cannot connect to the websocket server", classes:"red"});
                reject();
            }
            socket.onmessage = function (message) {
                var msg = JSON.parse(message.data);

                if (msg['msg'] === 'connected') {
                    connected = true;
                }
                else if(msg['msg'] === 'agent_action'){
                    that.agent.action_triggered(msg['data']);
                }
                else if(msg['msg'] === 'bt_devices_updated'){
                    that.main.updateListOfBluetoothDevices();
                }
                else if(msg['msg'] === 'hid_devices_updated'){
                    that.main.updateHIDDevices();
                }
                else {
                }
            };
            socket.onclose = function (e) {
                console.log('client side socket onclose');
                socket = null;
                that.changeConnectedState(false);
                isAttemptingToConnect = false;
            };
        });
    }

    sendMessage(msg) {
        if(socket!=null && connected){
            socket.send(JSON.stringify(msg));
        }
    }

    changeConnectedState(isConnected) {
        if(isConnected){
            connected = true;
        }
        else{
            connected = false;
            if(!isAttemptingToConnect){
                M.toast({html: "Server closed connection", classes:"red"});
            }
        }
        //codeRunner.handleConnectionStateChanged(isConnected);
    }

    async refreshConnection(){
        isRefreshing = true;
        if(socket !=null && connected){
            var msg = JSON.stringify({"msg": "shutdown"});
            try {
                socket.send(msg);
                socket.close();
            }
            catch(e){

            }
            socket==null;
            connected=false;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
        isRefreshing = false;
        return this.connect();
    }

}

