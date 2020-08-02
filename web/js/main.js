const views = {
    DEVICES: 'devices',
    SETTINGS: 'settings'
}

class Main{
    constructor() {
        this.activeView = views.DEVICES;
    }

    init(){
        var that = this;
        this.setActiveView(views.DEVICES);
        $('#settingsNavButton').on('click', e => {that.setActiveView(views.SETTINGS);});
        $('#devicesNavButton').on('click', e => {that.setActiveView(views.DEVICES);});
        $('#startScanningButton').on('click', e => {that.changeScanningMode(true);});
        $('#stopScanningButton').on('click', e => {that.changeScanningMode(false);});
        $('#startDiscoverableButton').on('click', e => {that.changeDiscoverableMode(true);});
        $('#stopDiscoverableButton').on('click', e => {that.changeDiscoverableMode(false);});

        this.scanning = false;
        this.setScanningState();
        this.discoverable = false;
        this.setDiscoverableState();

        $(document).on('submit', '#changePasswordForm',  e => {that.changePassword();return false;});
        $('.fixed-action-btn').floatingActionButton();
        $('#refreshHIDDevices').on('click', e => {that.updateHIDDevices();});
        $('.tabs').tabs();
        this.updateHIDDevices();
        this.updateListOfBluetoothDevices();
        this.agent = new Agent(this);
        this.webSocketManager = new WebSocketManager(this.agent, this);
    }

    updateHIDDevices(){
        var that = this;
        $.ajax({
            type: 'GET',
            dataType: 'json',
            url: 'http://' + location.hostname + ':8080/hiddevices',
            timeout: 5000,
            //async: false,
            success: function (response) {
                var trHTML = '';
                $.each(response.devices, function (i, device) {
                    var captureText = '';
                    var filterText = '<div class="input-field col s12"><select name="filterSelect" device="'+device.id+'">';
                    $.each(response.filters, function (j, filter) {
                        var selected = '';
                        if(device.filter == filter.id) selected = ' selected';
                        filterText+='<option value="'+filter.id+'"'+selected+'>' +filter.name+ '</option>';
                    });
                    filterText+='</select></div>';
                    if(device.capture) captureText = ' checked="checked"'
                    trHTML += '<tr><td>' + device.name + '</td><td class="capture-check"><p><label><input name="captureCheckbox" device="'+device.id+'" type="checkbox"'+captureText+'/><span> </span></label></p></td><td>'+filterText+'</td></tr>';
                });
                $('#hidDevicesList').html(trHTML);
                $('select').formSelect();

                $('input[type=checkbox][name=captureCheckbox]').on('change', function (data) {
                    that.setCapture($(this).attr("device"), $(this).prop("checked"));
                });
                $('select[name=filterSelect]').on('change', function (data) {
                    that.setFilter($(this).attr("device"), $(this).val());
                });
            },
            error: function (jqXHR, textStatus, errorThrown){
                M.toast({html: "Failed to load connected devices list. "+errorThrown, classes:"red"});
            }
        });
    }

    setCapture(device, state){
        var that = this;
        var formData = new FormData();
        formData.append("device_id", device);
        formData.append("capture", state);
        $.ajax({
            url: "http://" + location.hostname + ":8080/setdevicecapture",
            data: formData,
            type: 'POST', datatype: 'json', cache:false, contentType: false, processData: false,
            success: function (data, textStatus, jqXHR) {
                that.updateHIDDevices();
            },
            error: function (jqXHR, textStatus, errorThrown){
                that.updateHIDDevices();
                M.toast({html: "Could not set capture. "+errorThrown, classes:"red"});
            }
        });
    }

    setFilter(device, filter){
        var that = this;
        var formData = new FormData();
        formData.append("device_id", device);
        formData.append("filter", filter);
        $.ajax({
            url: "http://" + location.hostname + ":8080/setdevicefilter",
            data: formData,
            type: 'POST', datatype: 'json', cache:false, contentType: false, processData: false,
            success: function (data, textStatus, jqXHR) {
                that.updateHIDDevices();
            },
            error: function (jqXHR, textStatus, errorThrown){
                that.updateHIDDevices();
                M.toast({html: "Could not set filter. "+errorThrown, classes:"red"});
            }
        });
    }

    changePassword(){
        if($('#newPassword1')[0].value != $('#newPassword2')[0].value) {
            $('#newPassword1')[0].setCustomValidity("New passwords must match");
            $('#newPassword2')[0].setCustomValidity("New passwords must match");
        }
        else{
            $('#newPassword1')[0].setCustomValidity("");
            $('#newPassword2')[0].setCustomValidity("");
        }
        var isValid = $('#changePasswordForm')[0].checkValidity();
        $('#changePasswordForm')[0].reportValidity();
        if(!isValid) return;

        var formData = new FormData();
        formData.append("current_password", $('#currentPassword')[0].value);
        formData.append("new_password", $('#newPassword1')[0].value);
        $.ajax({
            url: "http://" + location.hostname + ":8080/changepassword",
            data: formData,
            type: 'POST', datatype: 'json', cache:false, contentType: false, processData: false,
            success: function (data, textStatus, jqXHR) {
                $('#currentPassword')[0].value = '';
                $('#newPassword1')[0].value = '';
                $('#newPassword2')[0].value = '';
                M.toast({html: "Successfully changed password"});
            },
            error: function (jqXHR, textStatus, errorThrown){
                M.toast({html: "Failed to change password. "+errorThrown, classes:"red"});
            }
        });
        return false;
    }

    updateListOfBluetoothDevices(){
        var that = this;
        $.ajax({
            type: 'GET',
            dataType: 'json',
            url: 'http://' + location.hostname + ':8080/bluetoothdevices',
            timeout: 5000,
            //async: false,
            success: function (response) {
                that.agent.bluetoothDevicesUpdated(response.devices);
                var trHTML = '';
                $.each(response.devices, function (i, device) {
                    if(!device.paired) return;
                    var connectDisconnectButton = '';
                    if(!device.connected){
                        connectDisconnectButton = '<a class="waves-effect waves-light btn-small" device="'+device.path+'" name="connectDeviceButton">Connect</a>';
                    }
                    else{
                        connectDisconnectButton = '<a class="waves-effect waves-light btn-small" device="'+device.path+'" name="disconnectDeviceButton">Disconnect</a>';
                    }
                    var host = '';
                    if(device.host) host = ' Host';
                    trHTML += '<tr><td>' + device.alias + ' (Paired'+host+')</td><td>' + device.address + '</td><td>'+connectDisconnectButton+' <a class="waves-effect waves-light btn-small red" device="'+device.path+'" name="removeDeviceButton">Remove</a></td></tr>';
                });
                $.each(response.devices, function (i, device) {
                    if(device.paired) return;
                    trHTML += '<tr><td>' + device.alias + '</td><td>' + device.address + '</td><td><a class="waves-effect waves-light btn-small" device="'+device.path+'" name="pairDeviceButton">Pair</a></td></tr>';
                });
                $('#bluetoothDevicesList').html(trHTML);
                $('a[name=pairDeviceButton]').on('click', function (data) {
                    that.webSocketManager.sendMessage({'msg':'pair_device','device':$(this).attr("device")})
                });
                $('a[name=connectDeviceButton]').on('click', function (data) {
                    that.webSocketManager.sendMessage({'msg':'connect_device','device':$(this).attr("device")})
                });
                $('a[name=disconnectDeviceButton]').on('click', function (data) {
                    that.webSocketManager.sendMessage({'msg':'disconnect_device','device':$(this).attr("device")})
                });
                $('a[name=removeDeviceButton]').on('click', function (data) {
                    that.webSocketManager.sendMessage({'msg':'remove_device','device':$(this).attr("device")})
                });
                if(!response.scanning){
                    that.scanning = false;
                    that.setScanningState();
                }
            },
            error: function (jqXHR, textStatus, errorThrown){
                M.toast({html: "Failed to load update bluetooth devices list. "+errorThrown, classes:"red"});
            }
        });
    }

    setScanningState(){
        if(this.scanning){
            $('#startScanningButton').hide()
            $('#stopScanningButton').show()
        }
        else{
            $('#startScanningButton').show()
            $('#stopScanningButton').hide()
        }
    }

    changeScanningMode(mode){
        $('#startScanningButton').hide()
        $('#stopScanningButton').hide()
        var that = this;
        $.ajax({
            url: "http://" + location.hostname + ":8080/"+ (mode ? "startscanning" : "stopscanning"),
            type: 'POST', datatype: 'json', cache:false, contentType: false, processData: false,
            success: function (data, textStatus, jqXHR) {
                M.toast({html: "Scan "+ (mode ? "started":"stopped")});
                that.scanning = mode;
                that.setScanningState();
            },
            error: function (jqXHR, textStatus, errorThrown){
                M.toast({html: "Could not "+(mode ? "start":"stop")+" scan. "+errorThrown, classes:"red"});
                if(errorThrown == "Operation already in progress") that.scanning = true;
                else if(errorThrown == "No discovery started") that.scanning = false;
                else that.scanning = !mode;
                that.setScanningState();
            }
        });
    }

    setDiscoverableState(){
        if(this.discoverable){
            $('#startDiscoverableButton').hide()
            $('#stopDiscoverableButton').show()
        }
        else{
            $('#startDiscoverableButton').show()
            $('#stopDiscoverableButton').hide()
        }
    }

    changeDiscoverableMode(mode){
        $('#startDiscoverableButton').hide()
        $('#stopDiscoverableButton').hide()
        var that = this;
        $.ajax({
            url: "http://" + location.hostname + ":8080/"+ (mode ? "startdiscoverable" : "stopdiscoverable"),
            type: 'POST', datatype: 'json', cache:false, contentType: false, processData: false,
            success: function (data, textStatus, jqXHR) {
                M.toast({html: "Discovery mode changed"});
                that.discoverable = mode;
                that.setDiscoverableState();
            },
            error: function (jqXHR, textStatus, errorThrown){
                M.toast({html: "Could not make"+(mode ? "":" not")+" discoverable. "+errorThrown, classes:"red"});
                that.discoverable = !mode;
                that.setDiscoverableState();
            }
        });
    }

    setActiveView(view){
        switch (view){
            case views.SETTINGS:
                $('#settingsPanel').show();
                $('#settingsNavButton').parent().addClass("active");
                $('#devicesPanel').hide();
                $('#devicesNavButton').parent().removeClass("active");
                break;
            case views.DEVICES:
            default:
                $('#devicesPanel').show();
                $('#devicesNavButton').parent().addClass("active");
                $('#settingsPanel').hide();
                $('#settingsNavButton').parent().removeClass("active");
        }
        this.activeView = view;
    }
}
