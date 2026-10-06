#!/bin/bash
# Correr UNA VEZ en la Pi (Pi OS Lite 64-bit recien instalada):  bash setup_pi.sh  y luego  sudo reboot
set -e
sudo apt update
sudo apt install -y python3-serial python3-pynmea2 psmisc git

# UART de hardware libre para GPS+ESP32: sin consola serie, UART habilitado, Bluetooth fuera
sudo raspi-config nonint do_serial_cons 1   # desactiva login shell por serie
sudo raspi-config nonint do_serial_hw 0     # habilita el puerto serie de hardware
CFG=/boot/firmware/config.txt
grep -q '^enable_uart=1' $CFG        || echo 'enable_uart=1' | sudo tee -a $CFG
grep -q '^dtoverlay=disable-bt' $CFG || echo 'dtoverlay=disable-bt' | sudo tee -a $CFG
sudo systemctl disable --now hciuart 2>/dev/null || true
echo "Listo. Reinicia con: sudo reboot   (despues: ls -l /dev/serial0  ->  deberia apuntar a ttyAMA0)"
