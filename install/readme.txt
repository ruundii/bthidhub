At time of writing this setup has been tested on the Bullseye release, with a 32-bit Raspberry Pi Zero.

## Install Instructions

1) Flash Raspberry Pi OS (32-bit) Lite (https://www.raspberrypi.org/downloads/raspberry-pi-os/) to an SD card.
2) If you didn't configure user, network and SSH via the Pi Imager, then mount the SD card as a drive.
  a) Copy wpa_supplicant.conf, ssh and userconf files to the root of the boot partition.
  b) Update Wifi network/password in wpa_supplicant.conf.
  c) Optionally, update username/password in userconf (A password hash can be produced with: `echo 'mypassword' | openssl passwd -6 -stdin`).
3) Plug SD card into the RPi and start it.
4) Get the IP address of the newly booted RPi.

Windows:
  5) Install putty: https://www.putty.org/
  6) Edit install_windows.bat and update the IP address and password.
  7) Run install_windows.bat, follow prompts until complete.
Linux/Mac:
  5) Run: ssh pi@[rpi-ip-address] 'bash -s' < setup.sh
     Password, if not change above, is 'raspberry'.

That last step could take an hour to complete.
When the RPi reboots, the LED will switch off once the service is ready to use.

Finally, go to the [rpi-ip-address]:8080 for the web configuration interface
