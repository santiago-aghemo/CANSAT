"""Protocolo Pi -> ESP32 (ASCII, checksum XOR estilo NMEA).

Frame:  $GPS,<fix>,<lat>,<lon>,<alt>*HH\n
  fix : 1 si hay fix valido, 0 si no
  lat, lon : grados decimales (6 decimales)
  alt : altura GPS en metros (solo respaldo/log, no se usa para el GSD)
  HH  : XOR de todos los caracteres entre '$' y '*' (sin incluirlos), 2 hex mayusculas
"""
from functools import reduce


def checksum(body: str) -> int:
    return reduce(lambda a, c: a ^ ord(c), body, 0)


def build_gps_frame(fix: bool, lat: float, lon: float, alt: float) -> bytes:
    if not fix:
        lat = lon = alt = 0.0
    body = f"GPS,{1 if fix else 0},{lat:.6f},{lon:.6f},{alt:.1f}"
    return f"${body}*{checksum(body):02X}\n".encode("ascii")


def parse_gps_frame(frame: bytes):
    """Inverso de build_gps_frame (para tests). Devuelve (fix, lat, lon, alt) o None si es invalido."""
    s = frame.decode("ascii", errors="ignore").strip()
    if not s.startswith("$") or "*" not in s:
        return None
    body, _, cs = s[1:].rpartition("*")
    try:
        if checksum(body) != int(cs, 16):
            return None
        tag, fix, lat, lon, alt = body.split(",")
        if tag != "GPS":
            return None
        return bool(int(fix)), float(lat), float(lon), float(alt)
    except ValueError:
        return None
