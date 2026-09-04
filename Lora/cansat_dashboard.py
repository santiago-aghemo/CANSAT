"""
CanSat 2026 - Dashboard de Estacion Terrena
=============================================

Lee por puerto serie los datos que imprime receiver_esqueleto.ino y los
muestra en un dashboard en tiempo real con Dear PyGui.

Formato esperado por linea, tal como lo imprime el .ino modificado:
    DATA:#1,T:23.50,P:101325.00,ALT:123.45
    META:rssi=-42,snr=9,len=31
    EVENT:RX_TIMEOUT
    EVENT:RX_ERROR

NOTA: el formato del paquete DATA (los campos despues de "#N,") tiene que
coincidir con lo que arma el sender via sprintf/snprintf. Por ahora este
dashboard solo espera T (temperatura), P (presion) y ALT (altitud), que
son los campos que ya estan en senderv1.ino. Cuando agregues los sensores
MQ, GPS, etc. al paquete, hay que sumar el parseo correspondiente en
parse_data_line() y agregar los widgets/plots que quieras.

Como correrlo:
    pip install dearpygui pyserial
    python cansat_dashboard.py

Todo el estado compartido entre el hilo de lectura serial y la UI vive en
la clase SharedState, protegida con un Lock. La UI hace polling de ese
estado en cada frame (render_callback), no hay actualizaciones directas
desde el hilo serial hacia dearpygui (evita condiciones de carrera).
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
MAX_POINTS = 300          # cuantos puntos mantenemos en cada grafico (ventana deslizante)
RECONNECT_DELAY = 2.0     # segundos entre reintentos de reconexion si se corta el puerto
SERIAL_READ_TIMEOUT = 1.0 # timeout de lectura serial, para que el hilo pueda chequear "seguir corriendo"

# Regex para el paquete de datos. Ajustar aca si cambia el formato del sprintf.
# Ejemplo de linea esperada (despues de sacar el prefijo "DATA:"):
#   #1,T:23.50,P:101325.00,ALT:123.45
DATA_PATTERN = re.compile(
    r"#(?P<packet_id>\d+),T:(?P<temp>-?\d+\.?\d*),P:(?P<pres>-?\d+\.?\d*),ALT:(?P<alt>-?\d+\.?\d*)"
)
META_PATTERN = re.compile(
    r"rssi=(?P<rssi>-?\d+),snr=(?P<snr>-?\d+),len=(?P<len>\d+)"
)


# ==========================================================
# ESTADO COMPARTIDO (hilo serial <-> hilo de UI)
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

    # ultimos valores puntuales (para las tarjetas de texto grande)
    last_temp: float = 0.0
    last_pres: float = 0.0
    last_alt: float = 0.0
    last_rssi: int = 0
    last_snr: int = 0

    # series de tiempo (ventana deslizante de MAX_POINTS) para los graficos
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
    """Parsea el contenido de una linea DATA: (sin el prefijo).
    Devuelve un dict con los campos, o None si no matchea el formato esperado."""
    match = DATA_PATTERN.search(payload)
    if not match:
        return None
    return {
        "packet_id": int(match.group("packet_id")),
        "temp": float(match.group("temp")),
        "pres": float(match.group("pres")),
        "alt": float(match.group("alt")),
    }


def parse_meta_line(payload: str):
    """Parsea el contenido de una linea META: (sin el prefijo)."""
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
    """Corre en un hilo aparte. Se conecta al puerto, lee linea por linea,
    actualiza SharedState, y reintenta la conexion si se corta (por ejemplo
    si se desconecta el cable USB de la estacion terrena en pleno vuelo).

    NOTA sobre el orden DATA/META: el .ino imprime primero la linea DATA y
    RECIEN DESPUES la linea META del mismo paquete (ver OnRxDone). Por eso
    la asociacion correcta es: al llegar DATA, agregamos un placeholder a
    rssi_series/snr_series (mismo indice que el t_axis de ese paquete); al
    llegar el META siguiente, pisamos ese placeholder con el valor real.
    Esto mantiene las 3 series (t_axis, rssi_series, snr_series) siempre
    con la MISMA longitud, evitando el desfasaje de graficar rssi/snr
    contra un eje de tiempo que no les corresponde."""

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
                        # se desconecto el puerto (ej: cable USB) -> salimos del with
                        # y el loop externo va a reintentar conectar
                        with state.lock:
                            state.connected = False
                            state.last_error = f"Puerto desconectado: {exc}"
                        break

                    if not raw:
                        continue  # timeout de lectura, normal, seguimos esperando

                    line = raw.decode(errors="ignore").strip()
                    if not line:
                        continue

                    now = time.time()

                    if line.startswith("DATA:"):
                        parsed = parse_data_line(line[len("DATA:"):])
                        if parsed is None:
                            continue
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

                            # placeholder: se pisa cuando llegue la linea META
                            # de este mismo paquete (llega justo despues, ver
                            # OnRxDone en el .ino). Usamos el ultimo rssi/snr
                            # conocido como placeholder en vez de 0 para no
                            # meter un salto falso en el grafico.
                            state.rssi_series.append(state.last_rssi)
                            state.snr_series.append(state.last_snr)

                    elif line.startswith("META:"):
                        parsed = parse_meta_line(line[len("META:"):])
                        if parsed is None:
                            continue
                        with state.lock:
                            state.last_rssi = parsed["rssi"]
                            state.last_snr = parsed["snr"]
                            # pisamos el placeholder que dejo el ultimo DATA,
                            # asi rssi_series/snr_series quedan siempre del
                            # mismo largo que t_axis, sin desfasajes
                            if state.rssi_series:
                                state.rssi_series[-1] = parsed["rssi"]
                                state.snr_series[-1] = parsed["snr"]

                    elif line.startswith("EVENT:RX_TIMEOUT"):
                        with state.lock:
                            state.timeout_count += 1

                    elif line.startswith("EVENT:RX_ERROR"):
                        with state.lock:
                            state.error_count += 1

                    # cualquier otra linea (ej. prints de debug sueltos) se ignora

        except serial.SerialException as exc:
            with state.lock:
                state.connected = False
                state.last_error = f"No se pudo abrir {port}: {exc}"

        if not stop_event.is_set():
            time.sleep(RECONNECT_DELAY)  # esperamos antes de reintentar conectar


# ==========================================================
# HELPERS DE UI
# ==========================================================

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports] or ["(ninguno detectado)"]


def connect_callback(sender, app_data):
    selected_port = dpg.get_value("port_combo")
    if not selected_port or selected_port == "(ninguno detectado)":
        dpg.set_value("connection_status_text", "Elegi un puerto valido antes de conectar")
        return

    # si ya habia un hilo corriendo, lo paramos primero
    stop_event.set()
    time.sleep(0.1)
    stop_event.clear()

    with state.lock:
        state.connected = False

    thread = threading.Thread(target=serial_worker, args=(selected_port,), daemon=True)
    thread.start()


def refresh_ports_callback(sender, app_data):
    dpg.configure_item("port_combo", items=list_available_ports())


# ==========================================================
# CONSTRUCCION DE LA UI
# ==========================================================

def build_ui():
    dpg.create_context()
    dpg.create_viewport(title="CanSat 2026 - Estacion Terrena", width=1000, height=700)

    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (18, 20, 24), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
    dpg.bind_theme(global_theme)

    with dpg.window(tag="main_window"):
        # --- Barra superior: conexion ---
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

        # --- Tarjetas de valores actuales ---
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

        # --- Contadores / diagnostico ---
        with dpg.group(horizontal=True):
            dpg.add_text("Paquetes: 0", tag="stat_packets")
            dpg.add_text("   Timeouts: 0", tag="stat_timeouts")
            dpg.add_text("   Errores: 0", tag="stat_errors")
            dpg.add_text("   Ultimo paquete: --", tag="stat_last_seen")

        dpg.add_separator()

        # --- Graficos en tiempo real ---
        with dpg.group(horizontal=True):
            with dpg.plot(label="Temperatura (C)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="temp_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="C", tag="temp_y_axis"):
                    dpg.add_line_series([], [], tag="temp_series", parent="temp_y_axis")

            with dpg.plot(label="Presion (Pa)", height=250, width=480):
                dpg.add_plot_axis(dpg.mvXAxis, label="t (s)", tag="pres_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="Pa", tag="pres_y_axis"):
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


# ==========================================================
# LOOP DE RENDER: refresca la UI con el SharedState en cada frame
# ==========================================================

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

    # --- estado de conexion ---
    if connected:
        dpg.set_value("connection_status_text", f"Conectado a {port_name}")
    elif last_error:
        dpg.set_value("connection_status_text", last_error)
    else:
        dpg.set_value("connection_status_text", "Desconectado")

    # --- tarjetas ---
    dpg.set_value("card_temp", f"{last_temp:.2f} C")
    dpg.set_value("card_pres", f"{last_pres:.2f} Pa")
    dpg.set_value("card_alt", f"{last_alt:.2f} m")
    dpg.set_value("card_signal", f"{last_rssi} dBm / {last_snr} dB")

    # --- contadores ---
    dpg.set_value("stat_packets", f"Paquetes: {packet_count}")
    dpg.set_value("stat_timeouts", f"   Timeouts: {timeout_count}")
    dpg.set_value("stat_errors", f"   Errores: {error_count}")
    if last_packet_time:
        seconds_ago = time.time() - last_packet_time
        dpg.set_value("stat_last_seen", f"   Ultimo paquete: hace {seconds_ago:.1f}s")
    else:
        dpg.set_value("stat_last_seen", "   Ultimo paquete: --")

    # --- graficos ---
    if t_axis:
        dpg.set_value("temp_series", [t_axis, temp_series])
        dpg.set_value("pres_series", [t_axis, pres_series])
        dpg.set_value("alt_series", [t_axis, alt_series])
        dpg.fit_axis_data("temp_x_axis")
        dpg.fit_axis_data("temp_y_axis")
        dpg.fit_axis_data("pres_x_axis")
        dpg.fit_axis_data("pres_y_axis")
        dpg.fit_axis_data("alt_x_axis")
        dpg.fit_axis_data("alt_y_axis")

    if rssi_series and t_axis:
        # rssi_series/snr_series siempre tienen el mismo largo que t_axis
        # (ver comentario en serial_worker sobre el placeholder de META)
        dpg.set_value("rssi_series", [t_axis, rssi_series])
        dpg.set_value("snr_series", [t_axis, snr_series])
        dpg.fit_axis_data("signal_x_axis")
        dpg.fit_axis_data("signal_y_axis")


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
