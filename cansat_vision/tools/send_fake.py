"""ETAPA 3: manda coordenadas FALSAS al ESP32 (sin necesitar fix). Si en el receptor LoRa aparecen
LAT/LON con estos valores, el enlace Pi TXD -> ESP32 funciona. Parar con Ctrl+C: tras 3 s pasa a NA."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comms.uart import open_uart
from comms.esp32_link import ESP32Link

link = ESP32Link(open_uart())
lat, lon = -31.420100, -64.188800
n = 0
try:
    while True:
        link.send_gps(True, lat + n * 1e-5, lon, 420.0)
        print(f"enviado lat={lat + n * 1e-5:.6f} lon={lon:.6f}")
        n += 1
        time.sleep(1)
except KeyboardInterrupt:
    pass
