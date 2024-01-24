cd $HOME/bthidhub/install/on_rpi

sudo echo 0 | sudo tee /sys/class/leds/ACT/brightness > /dev/null

systemctl --user stop pulseaudio.socket
systemctl --user stop pulseaudio.service
systemctl --user disable pulseaudio.socket
systemctl --user disable pulseaudio.service
systemctl --user mask pulseaudio.socket
systemctl --user mask pulseaudio.service

sudo systemctl  stop pulseaudio.socket
sudo systemctl  stop pulseaudio.service
sudo systemctl  disable pulseaudio.socket
sudo systemctl  disable pulseaudio.service
sudo systemctl  mask pulseaudio.socket
sudo systemctl  mask pulseaudio.service

systemctl --user stop obex
systemctl --user disable obex
systemctl --user mask obex

sudo apt-get install libcairo2-dev libdbus-1-dev libgirepository1.0-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev autoconf automake libtool python3-pip -y
sudo pip3 install -r $HOME/bthidhub/requirements.txt

cd $HOME/bthidhub/install/on_rpi
git clone https://github.com/Dreamsorcerer/bluez.git
cd $HOME/bthidhub/install/on_rpi/bluez
autoreconf -fvi

./configure --prefix=/usr --mandir=/usr/share/man --sysconfdir=/etc --localstatedir=/var --disable-a2dp --disable-avrcp --disable-network
automake
make -j4

sudo systemctl disable bluetooth
sudo systemctl stop bluetooth
sudo make install
sudo python3 $HOME/bthidhub/install/on_rpi/config_replacer.py
sudo cp $HOME/bthidhub/install/on_rpi/sdp_record.xml /etc/bluetooth/sdp_record.xml
sudo cp $HOME/bthidhub/install/on_rpi/input.conf /etc/bluetooth/input.conf
sudo cp $HOME/bthidhub/install/on_rpi/main.conf /etc/bluetooth/main.conf

sudo sed -i "s/\/home\/pi/\/home\/$(basename $HOME)/g" $HOME/bthidhub/install/on_rpi/remapper.service
sudo cp $HOME/bthidhub/install/on_rpi/remapper.service /lib/systemd/system/remapper.service
sudo chmod 644 /lib/systemd/system/remapper.service
sudo systemctl daemon-reload

sudo systemctl enable bluetooth
sudo systemctl start bluetooth
sudo systemctl enable remapper.service
sudo systemctl start remapper.service

sudo hostnamectl set-hostname bthidhub
sudo sed -Ei 's/^127\.0\.1\.1.*$/127.0.1.1\tbthidhub/' /etc/hosts

# Compile some Python modules to reduce lag.
# We do this at the end, as the project is already usable without this step.
cd $HOME/bthidhub/
mypyc

sudo reboot
