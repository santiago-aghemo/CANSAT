"""UART unico de la Pi (/dev/serial0 = PL011).

Un solo puerto fisico, dos cables:
  - RXD (GPIO15, pin 10) <- TX del GPS
  - TXD (GPIO14, pin 8)  -> RX del ESP32
Por eso el objeto Serial se abre UNA vez y se comparte: el GPSReader lee, ESP32Link escribe.
"""
import serial

UART_PORT = "/dev/serial0"
UART_BAUD = 9600  # el NEO-6M viene a 9600 de fabrica; el ESP32 escucha a 9600 tambien


def open_uart(port: str = UART_PORT, baud: int = UART_BAUD) -> serial.Serial:
    return serial.Serial(port, baud, timeout=1)
