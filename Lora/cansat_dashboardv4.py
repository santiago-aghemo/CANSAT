"""
CanSat 2026 - Dashboard de Estacion Terrena (Corregido y Adaptado)
==================================================================
"""

import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import serial
import serial.tools.list_ports
import dearpygui.dearpygui as dpg

# ==========================================================
# CONFIGURACION
# ==========================================================

BAUD_RATE = 115200
MAX_POINTS = 300          # ventana deslizante de puntos
RECONNECT_DELAY = 2.0     # reintentos de conexion
SERIAL_READ_TIMEOUT = 1.0 
X_WINDOW_SECONDS = 30.0   # Ventana visible en segundos para el scroll horizontal

# Regex adaptada para la trama actual: "T: 20.75 C, P: 972.86 hPa, A: 330.67 m"
DATA_PATTERN = re.compile(
    r"T:\s*(?P<temp>-?\d+\.?\d*)\s*C,\s*P:\s*(?P<pres>-?\d+\.?\d*)\s*hPa,\s*A:\s*(?P<alt>-?\d+\.?\d*)\s*m",
    re.IGNORECASE
)

META_PATTERN = re.compile(
    r"rssi\s*=\s*(?P<rssi>-?\d+)\s*,\s*snr\s*=\s*(?P<snr>-?\d+)\s*,\s*len\s*=\s*(?P<len>\d+)",
    re.IGNORECASE
)


# ==========================================================
# ESTADO COMPARTIDO
# ==========================================================

@dataclass
class SharedState:
    lock: threading.Lock = field(default_factory=threading.Lock)

    connected: bool = False
    port_name: str = ""
    last_packet_time: float = 0.0
    last_error: str = ""

    packet_count: int = 0
    timeout_count: int = 0
    error_count: int = 0

    last_temp: float = 0.0
    last_pres: float = 0.0
    last_alt: float = 0.0
    last_rssi: int = 0
    last_snr: int = 0

    t_axis: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))
    temp_series: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))
    pres_series: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))
    alt_series: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))
    rssi_series: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))
    snr_series: deque = field(default_factory=lambda: deque(maxlen=MAX_POINTS))

    start_time: float = field(default_factory=time.time)


state = SharedState()
stop_event = threading.Event()


# ==========================================================
# PARSEO DE LINEAS
# ==========================================================

def parse_data_line(payload: str):
    match = DATA_PATTERN.search(payload)
    if not match:
        return None
    return {
        "temp": float(match.group("temp")),
        "pres": float(match.group("pres")),
        "alt": float(match.group("alt")),
    }


def parse_meta_line(payload: str):
    match = META_PATTERN.search(payload)
    if not match:
        return None
    return {
        "rssi": int(match.group("rssi")),
        "snr": int(match.group("snr")),
        "len": int(match.group("len")),
    }


# ==========================================================
# HILO DE LECTURA SERIAL
# ==========================================================

def serial_worker(port: str):
    while not stop_event.is_set():
        try:
            with serial.Serial(port, BAUD_RATE, timeout=SERIAL_READ_TIMEOUT) as ser:
                with state.lock:
                    state.connected = True
                    state.port_name = port
                    state.last_error = ""

                while not stop_event.is_set():
                    try:
                        raw = ser.readline()
                    except serial.SerialException as exc:
                        with state.lock:
                            state.connected = False
                            state.last_error = f"Puerto desconectado: {exc}"
                        break

                    if not raw:
                        continue

                    line = raw.decode(errors="ignore").strip()
                    if not line:
                        continue

                    now = time.time()

                    if line.startswith("DATA:"):
                        payload = line[len("DATA:"):].strip()
                        parsed = parse_data_line(payload)
                        
                        print(f"[RAW RECEIVE] DATA: {payload}")
                        
                        if parsed is None:
                            print(f"[ERROR PARSE] La linea DATA no coincide con el patron regex!")
                            continue
                        
                        print(f"[SUCCESS] Datos extraídos -> Temp:{parsed['temp']} Pres:{parsed['pres']} Alt:{parsed['alt']}")

                        with state.lock:
                            state.last_packet_time = now
                            state.packet_count += 1
                            state.last_temp = parsed["temp"]
                            state.last_pres = parsed["pres"]
                            state.last_alt = parsed["alt"]

                            elapsed = now - state.start_time
                            state.t_axis.append(elapsed)
                            state.temp_series.append(parsed["temp"])
                            state.pres_series.append(parsed["pres"])
                            state.alt_series.append(parsed["alt"])

                            state.rssi_series.append(state.last_rssi)
                            state.snr_series.append(state.last_snr)

                    elif line.startswith("META:"):
                        payload = line[len("META:"):].strip()
                        parsed = parse_meta_line(payload)
                        if parsed is None:
                            continue
                        with state.lock:
                            state.last_rssi = parsed["rssi"]
                            state.last_snr = parsed["snr"]
                            if state.rssi_series:
                                state.rssi_series[-1] = parsed["rssi"]
                                state.snr_series[-1] = parsed["snr"]

                    elif line.startswith("EVENT:RX_TIMEOUT"):
                        with state.lock:
                            state.timeout_count += 1

                    elif line.startswith("EVENT:RX_ERROR"):
                        with state.lock:
                            state.error_count += 1

        except serial.SerialException as exc:
            with state.lock:
                state.connected = False
                state.last_error = f"No se pudo abrir {port}: {exc}"

        if not stop_event.is_set():
            time.sleep(RECONNECT_DELAY)


# ==========================================================
# HELPERS DE UI Y LOOP
# ==========================================================

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports] or ["(ninguno detectado)"]


def connect_callback(sender, app_data):
    selected_port = dpg.get_value("port_combo")
    if not selected_port or selected_port == "(ninguno detectado)":
        dpg.set_value("connection_status_text", "Elegi un puerto valido antes de conectar")
        return

    stop_event.set()
    time.sleep(0.1)
    stop_event.clear()

    with state.lock:
        state.connected = False

    thread = threading.Thread(target=serial_worker, args=(selected_port,), daemon=True)
    thread.start()


def refresh_ports_callback(sender, app_data):
    dpg.configure_item("port_combo", items=list_available_ports())


def update_x_axis(axis_tag, t_axis, window_size=X_WINDOW_SECONDS):
    """Mantiene una ventana de tiempo visible moviendo el grafico hacia la izquierda."""
    if not t_axis:
        return
    t_latest = t_axis[-1]
    t_min = max(0.0, t_latest - window_size)
    t_max = max(window_size, t_latest)
    dpg.set_axis_limits(axis_tag, t_min, t_max)


def update_y_axis(axis_tag, data_series, min_span=5.0, margin=0.5):
    """Ajusta el eje Y garantizando un rango minimo para evitar saltos exagerados por pequeas variaciones."""
    if not data_series:
        return
    y_min = min(data_series)
    y_max = max(data_series)
    center = (y_min + y_max) / 2.0
    
    # Mantiene la escala con al menos min_span de diferencia entre min y max
    span = max(y_max - y_min + 2 * margin, min_span)
    
    dpg.set_axis_limits(axis_tag, center - (span / 2.0), center + (span / 2.0))


def build_ui():
    dpg.create_context()
    dpg.create_viewport(title="CanSat 2026 - Estacion Terrena", width=1000, height=700)

    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (18, 20, 24), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
    dpg.bind_theme(global_theme)

    with dpg.window(tag="main_window"):
        with dpg.group(horizontal=True):
            dpg.add_text("Puerto:")
            dpg.add_combo(
                items=list_available_ports(),
                tag="port_combo",
                width=180,
                default_value=list_available_ports()[0],
            )
            dpg.add_button(label="Refrescar", callback=refresh_ports_callback)
            dpg.add_button(label="Conectar", callback=connect_callback)
            dpg.add_text("", tag="connection_status_text")

        dpg.add_separator()

        with dpg.group(horizontal=True):
            with dpg.child_window(width=220, height=100):
                dpg.add_text("TEMPERATURA")
                dpg.add_text("-- C", tag="card_temp")
            with dpg.child_window(width=220, height=100):
                dpg.add_text("PRESION")
                dpg.add_text("-- Pa", tag="card_pres")
            with dpg.child_window(width=220, height=100):
                dpg.add_text("ALTITUD")
                dpg.add_text("-- m", tag="card_alt")
            with dpg.child_window(width=220, height=100):
                dpg.add_text("SENAL (RSSI / SNR)")
                dpg.add_text("-- dBm / -- dB", tag="card_signal")

        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text("Paquetes: 0", tag="stat_packets")
            dpg.add_text("   Timeouts: 0", tag="stat_timeouts")
            dpg.add_text("   Errores: 0", tag="stat_errors")
            dpg.add_text("   Ultimo paquete: --", tag="stat_last_seen")

        dpg.add_separator()

        with dpg.group(horizontal=True):
            with dpg.plot(label="Temperatura (C)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="temp_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="C", tag="temp_y_axis"):
                    dpg.add_line_series([], [], tag="temp_series", parent="temp_y_axis")

            with dpg.plot(label="Presion (hPa)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="pres_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="hPa", tag="pres_y_axis"):
                    dpg.add_line_series([], [], tag="pres_series", parent="pres_y_axis")

        with dpg.group(horizontal=True):
            with dpg.plot(label="Altitud (m)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="alt_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="m", tag="alt_y_axis"):
                    dpg.add_line_series([], [], tag="alt_series", parent="alt_y_axis")

            with dpg.plot(label="Calidad de senal (RSSI / SNR)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="signal_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="dBm / dB", tag="signal_y_axis"):
                    dpg.add_line_series([], [], label="RSSI", tag="rssi_series", parent="signal_y_axis")
                    dpg.add_line_series([], [], label="SNR", tag="snr_series", parent="signal_y_axis")
                dpg.add_plot_legend()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)


def update_ui_from_state():
    with state.lock:
        connected = state.connected
        port_name = state.port_name
        last_error = state.last_error
        last_packet_time = state.last_packet_time
        packet_count = state.packet_count
        timeout_count = state.timeout_count
        error_count = state.error_count

        last_temp = state.last_temp
        last_pres = state.last_pres
        last_alt = state.last_alt
        last_rssi = state.last_rssi
        last_snr = state.last_snr

        t_axis = list(state.t_axis)
        temp_series = list(state.temp_series)
        pres_series = list(state.pres_series)
        alt_series = list(state.alt_series)
        rssi_series = list(state.rssi_series)
        snr_series = list(state.snr_series)

    if connected:
        dpg.set_value("connection_status_text", f"Conectado a {port_name}")
    elif last_error:
        dpg.set_value("connection_status_text", last_error)
    else:
        dpg.set_value("connection_status_text", "Desconectado")

    dpg.set_value("card_temp", f"{last_temp:.2f} C")
    dpg.set_value("card_pres", f"{last_pres:.2f} hPa")
    dpg.set_value("card_alt", f"{last_alt:.2f} m")
    dpg.set_value("card_signal", f"{last_rssi} dBm / {last_snr} dB")

    dpg.set_value("stat_packets", f"Paquetes: {packet_count}")
    dpg.set_value("stat_timeouts", f"   Timeouts: {timeout_count}")
    dpg.set_value("stat_errors", f"   Errores: {error_count}")
    if last_packet_time:
        seconds_ago = time.time() - last_packet_time
        dpg.set_value("stat_last_seen", f"   Ultimo paquete: hace {seconds_ago:.1f}s")
    else:
        dpg.set_value("stat_last_seen", "   Ultimo paquete: --")

    if t_axis:
        dpg.set_value("temp_series", [t_axis, temp_series])
        dpg.set_value("pres_series", [t_axis, pres_series])
        dpg.set_value("alt_series", [t_axis, alt_series])

        # Actualización de límites horizontales (desplazamiento suave a la izquierda)
        update_x_axis("temp_x_axis", t_axis)
        update_x_axis("pres_x_axis", t_axis)
        update_x_axis("alt_x_axis", t_axis)

        # Actualización de límites verticales (amortiguación de variaciones mínimas)
        update_y_axis("temp_y_axis", temp_series, min_span=5.0)  # Mínimo 5 C de escala
        update_y_axis("pres_y_axis", pres_series, min_span=10.0)
        update_y_axis("alt_y_axis", alt_series, min_span=10.0)

    if rssi_series and t_axis:
        dpg.set_value("rssi_series", [t_axis, rssi_series])
        dpg.set_value("snr_series", [t_axis, snr_series])
        update_x_axis("signal_x_axis", t_axis)
        update_y_axis("signal_y_axis", rssi_series, min_span=20.0)


def main():
    build_ui()
    try:
        while dpg.is_dearpygui_running():
            update_ui_from_state()
            dpg.render_dearpygui_frame()
    finally:
        stop_event.set()
        dpg.destroy_context()


if __name__ == "__main__":
    main()