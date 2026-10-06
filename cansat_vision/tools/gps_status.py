"""ETAPA 2: GPS parseado (fix, lat, lon, sats). Util para esperar el fix antes de volar."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comms.uart import open_uart
from sensors.gps import GPSReader

gps = GPSReader(open_uart())
gps.start()
try:
    while True:
        f = gps.get()
        print(f"valid={f.valid} lat={f.lat:.6f} lon={f.lon:.6f} alt={f.alt:.1f} sats={f.sats} "
              f"vel={f.speed_kmh:.1f}km/h edad={f.age_s:.1f}s")
        time.sleep(1)
except KeyboardInterrupt:
    gps.stop()
