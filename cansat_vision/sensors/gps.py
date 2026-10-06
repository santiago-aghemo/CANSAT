"""Lector de GPS NEO-6M en un hilo. Parsea GGA (posicion/fix) y RMC (velocidad) con pynmea2."""
import csv
import os
import threading
import time
from dataclasses import dataclass

import pynmea2
import serial


@dataclass
class GPSFix:
    valid: bool = False      # fix valido Y dato fresco (no stale)
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0         # altura GPS (respaldo; el GSD usa el BMP280)
    sats: int = 0            # solo para log local, NO se transmite
    speed_kmh: float = 0.0
    age_s: float = float("inf")


class GPSReader(threading.Thread):
    def __init__(self, ser: serial.Serial, csv_path: str | None = None, stale_s: float = 3.0):
        super().__init__(daemon=True)
        self.ser = ser
        self.stale_s = stale_s
        self._lock = threading.Lock()
        self._stop_evt = threading.Event()
        self._fix = False
        self._lat = self._lon = self._alt = self._speed = 0.0
        self._sats = 0
        self._last_gga = 0.0
        self._csv = None
        self._writer = None
        if csv_path:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            new = not os.path.exists(csv_path)
            self._csv = open(csv_path, "a", newline="")
            self._writer = csv.writer(self._csv)
            if new:
                self._writer.writerow(["t_unix", "fix", "lat", "lon", "alt_gps", "sats", "speed_kmh"])

    def run(self):
        while not self._stop_evt.is_set():
            try:
                raw = self.ser.readline().decode("ascii", errors="ignore").strip()
                if not raw.startswith("$"):
                    continue
                msg = pynmea2.parse(raw)
            except (pynmea2.ParseError, serial.SerialException, UnicodeDecodeError):
                continue
            if isinstance(msg, pynmea2.types.talker.GGA):
                self._on_gga(msg)
            elif isinstance(msg, pynmea2.types.talker.RMC):
                try:
                    with self._lock:
                        self._speed = float(msg.spd_over_grnd or 0.0) * 1.852
                except ValueError:
                    pass

    def _on_gga(self, msg):
        try:
            fix = int(msg.gps_qual or 0) > 0
            lat = float(msg.latitude) if fix else 0.0
            lon = float(msg.longitude) if fix else 0.0
            alt = float(msg.altitude or 0.0) if fix else 0.0
            sats = int(msg.num_sats or 0)
        except (ValueError, TypeError):
            return
        with self._lock:
            self._fix, self._lat, self._lon, self._alt, self._sats = fix, lat, lon, alt, sats
            self._last_gga = time.monotonic()
            speed = self._speed
        if self._writer:
            self._writer.writerow([f"{time.time():.2f}", int(fix), f"{lat:.6f}", f"{lon:.6f}",
                                   f"{alt:.1f}", sats, f"{speed:.1f}"])
            self._csv.flush()

    def get(self) -> GPSFix:
        with self._lock:
            age = time.monotonic() - self._last_gga if self._last_gga else float("inf")
            return GPSFix(valid=self._fix and age < self.stale_s, lat=self._lat, lon=self._lon,
                          alt=self._alt, sats=self._sats, speed_kmh=self._speed, age_s=age)

    def stop(self):
        self._stop_evt.set()
        if self._csv:
            self._csv.close()
