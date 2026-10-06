"""Loop principal de la Pi: GPS -> ESP32 (1 Hz). Un solo proceso, un solo UART.
La camara IMX500 y el BMP280 propio se suman en las proximas etapas.
"""
import os
import signal
import time

from comms.esp32_link import ESP32Link
from comms.uart import open_uart
from sensors.gps import GPSReader

BASE = os.path.dirname(os.path.abspath(__file__))
SEND_PERIOD_S = 1.0
running = True


def _stop(*_):
    global running
    running = False


def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    ser = open_uart()
    gps = GPSReader(ser, csv_path=os.path.join(BASE, "data", "logs", "gps_log.csv"))
    gps.start()
    link = ESP32Link(ser)

    next_t = time.monotonic()
    while running:
        try:
            f = gps.get()
            link.send_gps(f.valid, f.lat, f.lon, f.alt)
        except Exception as e:  # un error transitorio no debe tirar abajo el loop
            print(f"[main] error: {e}", flush=True)
        next_t += SEND_PERIOD_S
        time.sleep(max(0.0, next_t - time.monotonic()))

    gps.stop()
    ser.close()


if __name__ == "__main__":
    main()
