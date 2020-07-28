import sys
import os
import tempfile

tmp = tempfile.mkstemp()

with open('/lib/systemd/system/bluetooth.service') as fd1, open(tmp[1], 'w') as fd2:
    for line in fd1:
        if line.startswith("ExecStart"):
            line = "ExecStart=/usr/libexec/bluetooth/bluetoothd -p time,input,autopair,policy,scanparam,deviceinfo"
        fd2.write(line)

os.rename(tmp[1], '/lib/systemd/system/bluetooth.service')
