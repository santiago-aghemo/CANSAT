"""ETAPA 1: muestra el NMEA crudo del GPS. Si ves lineas $GPGGA/$GPRMC, el cableado GPS->RX y el UART estan OK."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comms.uart import open_uart

ser = open_uart()
try:
    while True:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(line)
except KeyboardInterrupt:
    pass
