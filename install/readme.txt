1) in the wpa_supplicant.conf set your wifi network and password
2) After flashing Raspberry Pi OS (32-bit) Lite (https://www.raspberrypi.org/downloads/raspberry-pi-os/) to SD card, open it as a drive and copy wpa_supplicant.conf and ssh file to the root of the boot partition
3) Plug SD card into the RPi and start it
4) get an IP address of the newly booted RPi

Windows:
  5) install putty https://www.putty.org/
  6) edit install_windows.bat and enter this ip address
  7) run install_windows.bat, follow prompts until complete
Linux/Mac:
  5) Run: ssh pi@[rpi-ip-address] 'bash -s' < setup.sh
     Default password is 'raspberry'

Finally, go to the [rpi-ip-address]:8080 for the web configuration interface
