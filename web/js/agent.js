class Agent{
    constructor(main) {
        this.main=main;
        this.webSocketManager = null;
        this.currentDevice = null;
        this.passkey=null;
        var that = this;
        $('#modalConfirmButton').on('click', e => {
            that.webSocketManager.sendMessage({'msg':'request_confirmation_response', 'device':that.currentDevice, 'passkey':that.passkey,'confirmed':true });
            this.currentDevice = null;
            var instance = M.Modal.getInstance($('#modalPopup'))
            instance.close();
        });
        $('#modalRejectButton').on('click', e => {
            that.webSocketManager.sendMessage({'msg':'request_confirmation_response', 'device':that.currentDevice, 'passkey':that.passkey, 'confirmed':false });
            this.currentDevice = null;
            var instance = M.Modal.getInstance($('#modalPopup'))
            instance.close();
        });
    }

    setWebSocketManager(webSocketManager){
        this.webSocketManager = webSocketManager;
    }

    action_triggered(data){
        var that = this;
        if(data['action'] === 'display_pin_code'){
            $('.modal').modal({dismissible:false,
                onOpenStart: function () {
                    that.currentDevice = data['device'];
                    $('#modalPopupHeader')[0].innerHTML = "Pair?";
                    $('#modalPopupTextBefore')[0].innerHTML = "Type in the pin code and hit Enter:";
                    $('#modalPopupLargeText')[0].innerHTML = data['pincode'];
                    $('#modalPopupTextAfter')[0].innerHTML= "Device "+data['device'].split('/')[4]. replace("dev_","").replaceAll("_",":");
                    $('#modalCancelButton').show();
                    $('#modalConfirmButton').hide();
                    $('#modalRejectButton').hide();
                },
                onCloseEnd: function(){
                    that.webSocketManager.sendMessage({'msg':'cancel_pairing', 'device':that.currentDevice });
                    this.currentDevice = null;
                }

            });
            var instance = M.Modal.getInstance($('#modalPopup'))
            instance.open();
        }
        else if(data['action'] === 'confirm_passkey'){
            $('.modal').modal({dismissible:false,
                onOpenStart: function () {
                    that.currentDevice = data['device'];
                    this.passkey= data['passkey'];
                    $('#modalPopupHeader')[0].innerHTML = "Pair to host?";
                    $('#modalPopupTextBefore')[0].innerHTML = "Confirm you see the same passkey on host:";
                    $('#modalPopupLargeText')[0].innerHTML = data['passkey'];
                    $('#modalPopupTextAfter')[0].innerHTML= "Device "+data['device'].split('/')[4]. replace("dev_","").replaceAll("_",":");
                    $('#modalCancelButton').hide();
                    $('#modalConfirmButton').show();
                    $('#modalRejectButton').show();
                }
            });
            var instance = M.Modal.getInstance($('#modalPopup'))
            instance.open();
        }
        else if(data['action'] === 'service_authorised') {
            var instance = M.Modal.getInstance($('#modalPopup'))
            instance.close();
            this.main.updateListOfDevices();
        }
    }

    devices_updated(devices){
        if(this.currentDevice==null) return;

        $.each(devices, function (i, device) {
            if (!device.path == this.currentDevice) return;
            if(device.paired) {
                //close
                this.currentDevice = null;
                var instance = M.Modal.getInstance($('#modalPopup'))
                instance.close();
            }
        });

    }
}