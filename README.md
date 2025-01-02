# Bluetooth HID hub

<img src="bthidhuboverall.png" width="700" alt="BT HID Hub Diagram"/>

<img src="bthidhubarchitecture.png" width="700" alt="BT HID Hub Architecture Diagram"/>

This hub uses a modified version of the Bluez linux bluetooth protocol stack (https://github.com/ruundii/bluez).
The modified version extends bluetooth input profile to be able to **simultaneously** support host and device
connections (vs default input device connections only).  With this you can e.g. retransmit Bluetooth input devices to other machines.

The **Bluetooth HID hub** presents itself to a host computer as a Bluetooth multifunctional device.
The hub receives events from multiple input devices (wired and BT) and then transmits them to the host,
essentially acting as a proxy. This has been tested on a **Raspberry Pi Zero W**.

## Install Instructions

The install script is for the bullseye release. If a newer version of Raspberry Pi OS is available you can
either find an older release or test and fix the install script (and then send us a PR with the fixes).

1) Flash Raspberry Pi OS (32-bit) Lite (https://www.raspberrypi.org/downloads/raspberry-pi-os/) to an SD card.
2) If you didn't configure user, network and SSH via the Pi Imager, then mount the SD card as a drive.
  a) Copy wpa_supplicant.conf, ssh and userconf files from the install/ directory to the root of the boot partition.
  b) Update Wifi network/password in wpa_supplicant.conf.
  c) Optionally, update username/password in userconf (A password hash can be produced with: `echo 'mypassword' | openssl passwd -6 -stdin`).
3) Plug SD card into the RPi and start it.
4) Get the IP address of the newly booted RPi.

Windows:
  5) Install putty: https://www.putty.org/
  6) Edit install_windows.bat and update the IP address and password.
  7) Run install_windows.bat, follow prompts until complete.
Linux/Mac:
  5) Run: ``ssh pi@[rpi-ip-address] 'bash -s' < setup.sh``
     Password, if not change above, is 'raspberry'.

That last step could take an hour to complete.
When the RPi reboots, the LED will switch off once the service is ready to use.

Finally, go to the [rpi-ip-address]:8080 for the web configuration interface.

## Usage

From the Bluetooth devices tab you can pair each device you want to use. Any laptop/phone
should appear as a 'Paired Host'.

<img src="bt-hid-hub-bt-devices.png" width="500" alt="Bluetooth devices screen"/>

Back on the HID devices tab, you should see all the currently connected devices (wired and BT).
Click the capture checkbox for each device you want to start proxying events to.
Note that the BT will restart each time a new device is enabled.

<img src="bt-hid-hub-devices.png" width="500" alt="HID devices screen"/>


Added an ability to switch hosts with a keyboard (Fn+Cmd+Tab on Apple A1314 keyboard). Now can use the hub as an input for several computers, easily switching which one is currently active.

## Upgrading

To upgrade to the latest release without reinstalling from scratch, you'll need to SSH into the RPi
(as done in the install instructions). Then run:

```
cd /home/pi/bthidhub/
git pull
mypyc
sudo systemctl restart remapper
```

The `mypyc` command may take several minutes to an hour to run, but will optimise the performance.

Additionally, you should check if there were any changes in the install/ directory
(https://github.com/ruundii/bthidhub/commits/master/install).
You may need to manually make changes to the system to match the changes in the installation.

## Misc

Inspired by [RaspiKey](https://github.com/samartzidis/RaspiKey), but wanted the solution to stay wireless, as this is why I bought Apple wireless keyboard in the first place. By doing this it allowed to turn my wired mouse to wireless as well and have one keyboard+mouse for two machines. Also, Python implementation should allow people to easily customize their mappings. 
If you want to do this, check out [hid-tools](https://gitlab.freedesktop.org/libevdev/hid-tools) to monitor raw hid reports from your device.

[This post](http://who-t.blogspot.com/2018/12/understanding-hid-report-descriptors.html) is super helpful in getting your head around HID descriptors.
