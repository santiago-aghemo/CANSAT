"""Envio de datos al ESP32 por el TXD de la Pi (comparte el puerto con el GPS)."""
import serial

from .protocol import build_gps_frame


class ESP32Link:
    def __init__(self, ser: serial.Serial):
        self.ser = ser

    def send_gps(self, fix: bool, lat: float, lon: float, alt: float) -> None:
        self.ser.write(build_gps_frame(fix, lat, lon, alt))
