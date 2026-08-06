sudo systemctl stop evoduino
sleep 2
sudo avrdude -v -p atmega328p -C /etc/avrdude.conf -c arduino -P /dev/ttyUSB0 -D -U flash:w:evodog.ino.hex:i
sleep 2
sudo systemctl start evoduino
sleep 2
