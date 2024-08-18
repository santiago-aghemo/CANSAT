import sys
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
from communication import Communication
from dataBase import data_base
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 
from graphs.graph_pm25 import graph_pm25
from graphs.graph_acceleration import graph_acceleration
from graphs.graph_altitude import graph_altitude
from graphs.graph_battery import graph_battery
from graphs.graph_free_fall import graph_free_fall
from graphs.graph_pressure import graph_pressure
from graphs.graph_speed import graph_speed
from graphs.graph_temperature import graph_temperature
from graphs.graph_time import graph_time
from graphs.graph_humidity import graph_humidity
from graphs.graph_co import graph_co
from graphs.graph_coordinates import graph_coordinates
from time import sleep
pg.setConfigOption('background', (33, 33, 33))
pg.setConfigOption('foreground', (0, 170, 228))

# Global variables 
latitude = -31.381949
longitude = -64.272233

# Interface variables
app = QtWidgets.QApplication(sys.argv)
app.setStyleSheet('QLabel{color: 104, 57, 171;} QPushButton{background-color: 104, 57, 171; color: 104, 57, 171}')
view = pg.GraphicsView()
main = QtWidgets.QMainWindow()
main.setStyleSheet("background-color: rgb(104, 57, 171);")
main_layout = QVBoxLayout()

# header 
header_layout = QHBoxLayout()
header_title = QLabel()
header_title.setFont(QFont('Tahoma', 38))
header_title.setText('NOVATIONES')
header_subtitle = QLabel()
header_subtitle.setFont(QFont('Smalle', 24))
text = """
Estación terrena de la misión Dustbusters - Mod de<br>
los alumnos del Colegio Nacional de Monserrat 
"""
header_subtitle.setText(text)
header_layout.addWidget(header_title)
header_layout.addWidget(header_subtitle)
header_widget = QWidget()
header_widget.setLayout(header_layout)

# Add main layout widgets 
main_layout.addWidget(header_widget)
main_layout.addWidget(view)
main_widget = QWidget()
main_widget.setLayout(main_layout)
main.setCentralWidget(main_widget)
main.show()
Layout = pg.GraphicsLayout()
view.setCentralItem(Layout)
main.setWindowTitle('Monitoreo de misión CANSAT')
main.resize(1280, 720)

# declare object for serial Communication
ser = Communication()
# declare object for storage in CSV
data_base = data_base()
# Fonts for text items
font = QtGui.QFont()
font.setPixelSize(50)
font2 = QtGui.QFont()
font2.setPixelSize(30)
font3 = QtGui.QFont()
font3.setPixelSize(18)

# buttons style
style_green = "background-color:rgb(29, 185, 84);color:rgb(0,0,0);font-size:18px;"
style_red = "background-color:rgb(242, 69, 69);color:rgb(0,0,0);font-size:18px;"
style_yellow = "background-color:rgb(216, 220, 76);color:rgb(0,0,0);font-size:18px;"
style_grey = "background-color:rgb(137, 137, 137);color:rgb(0,0,0);font-size:18px;"

# Declare graphs
# Button Ready to launch 
proxy_ready = QtWidgets.QGraphicsProxyWidget()
ready_button = QtWidgets.QPushButton('Listo despegar')
ready_button.setStyleSheet(style_grey)
ready_button.clicked.connect(ser.ready_to_launch)
proxy_ready.setWidget(ready_button)

# Button Start mission 
proxy0 = QtWidgets.QGraphicsProxyWidget()
start_button = QtWidgets.QPushButton('Iniciar Misión')
start_button.setStyleSheet(style_grey)
start_button.clicked.connect(data_base.mission_start)
start_button.clicked.connect(ser.mission_start)
proxy0.setWidget(start_button)

# Button End mission 
proxy1 = QtWidgets.QGraphicsProxyWidget()
end_button = QtWidgets.QPushButton('Finalizar Misión')
end_button.setStyleSheet(style_red)
end_button.clicked.connect(data_base.mission_stop)
end_button.clicked.connect(ser.mission_end)
proxy1.setWidget(end_button)

# Button save
proxy2 = QtWidgets.QGraphicsProxyWidget()
save_button = QtWidgets.QPushButton('Guardar datos')
save_button.setStyleSheet(style_green)
save_button.clicked.connect(data_base.start)
proxy2.setWidget(save_button)

# Button stop
proxy3 = QtWidgets.QGraphicsProxyWidget()
end_save_button = QtWidgets.QPushButton('Detener datos')
end_save_button.setStyleSheet(style_red)
end_save_button.clicked.connect(data_base.stop)
proxy3.setWidget(end_save_button)

# Button reset
proxy_reset = QtWidgets.QGraphicsProxyWidget()
reset_button = QtWidgets.QPushButton('Restart Botones')
reset_button.setStyleSheet(style_red)
reset_button.clicked.connect(ser.resetBtns)
proxy_reset.setWidget(reset_button)

# Button reset eeprom 
proxy_reset_eeprom = QtWidgets.QGraphicsProxyWidget()
reset_eeprom_button = QtWidgets.QPushButton('Reset EEPROM')
reset_eeprom_button.setStyleSheet(style_grey)
reset_eeprom_button.clicked.connect(ser.reset_eeprom)
proxy_reset_eeprom.setWidget(reset_eeprom_button)

# Button reset_cansat
proxy_reset_cansat = QtWidgets.QGraphicsProxyWidget()
reset_cansat_button = QtWidgets.QPushButton('Reset Cansat')
reset_cansat_button.setStyleSheet(style_red)
reset_cansat_button.clicked.connect(ser.reset_cansat)
proxy_reset_cansat.setWidget(reset_cansat_button)

# Input location
latit = QLineEdit()
longit = QLineEdit()
longit.setText(str(longitude))
longit.setStyleSheet("color: white;background-color: rgb(33, 33, 33);")
latit.setText(str(latitude))
latit.setStyleSheet("color: white;background-color: rgb(33, 33, 33);")

def set_pos():
    ser.set_coordinates(latit.text(), longit.text())

proxy_loc = QtWidgets.QGraphicsProxyWidget()
flo = QFormLayout()
flo.addRow("Latitud", latit)
flo.addRow("Longitud", longit)
set_pos_button = QtWidgets.QPushButton('Definir aterrizaje')
set_pos_button.setStyleSheet(style_grey)
set_pos_button.clicked.connect(set_pos)
flo.addRow(set_pos_button)
form = QWidget()
form.setStyleSheet("background-color: rgb(33, 33, 33);")
form.setLayout(flo)
proxy_loc.setWidget(form)

# Altitude graph
altitude = graph_altitude()
# Speed graph acceleration
speed = graph_speed()
# pm25 graph
pm25 = graph_pm25()
# Acceleration graph
acceleration = graph_acceleration()
# Pressure Graph
pressure = graph_pressure()
# Temperature graph
temperature = graph_temperature()
# Time graph
total_time = graph_time(font=font)
# Battery graph
battery = graph_battery()
# Free fall graph
free_fall = graph_free_fall(font=font)
# Humidity graph
humidity = graph_humidity()
# CO graph
co = graph_co()
# Coordinate graph
coordinates = graph_coordinates(font=font3)


## Setting the graphs in the layout 

# Buttons
lb = Layout.addLayout(colspan=21)
lb.addItem(proxy_ready)
lb.nextCol()
lb.addItem(proxy0)
lb.nextCol()
lb.addItem(proxy1)
lb.nextCol()
lb.addItem(proxy_reset_eeprom)
lb.nextCol()
lb.addItem(proxy_reset_cansat)
lb.nextCol()
lb.addItem(proxy_reset)
Layout.nextRow()

l1 = Layout.addLayout(colspan=60, rowspan=2)
l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))
l11.addLabel('Misión Primaria', size='15pt', angle=-90)

# Altitude, temperature, pressure 
l11.addItem(temperature)
l11.addItem(altitude)
l11.addItem(pressure)
l1.nextRow()

# Acceleration, gyro, speed 
l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))
l12.addLabel('Misión Secundaria', size='15pt', angle=-90)
l12.addItem(pm25)
l12.addItem(acceleration)
l12.addItem(humidity)
l12.addItem(co)

# Time, battery and free fall graphs
l2 = Layout.addLayout(border=(83, 83, 83), colspan=1)
l2.setFixedWidth(250)
l2.addItem(proxy_loc)
l2.nextRow()
l2.addItem(battery)
l2.nextRow()
l2.addItem(total_time)
l2.nextRow()
l2.addItem(free_fall)

# you have to put the position of the CSV stored in the value_chain list
# that represent the date you want to visualize
def update(data):
    try:
        value_chain = []
        value_chain = data
        print(value_chain)
        humidity.update(value_chain[4])
        temperature.update(value_chain[6])
        pressure.update(value_chain[7])
        pm25.update(value_chain[3])
        co.update(value_chain[2])
        altitude.update(value_chain[8])
        acceleration.update(value_chain[9])
        battery.update(value_chain[10])
        free_fall.update(value_chain[11])
        total_time.update(value_chain[12])
        data_base.guardar(value_chain)
    except IndexError:
        print('starting, please wait a moment')

def btnsUpdate(stat):
    if(stat):
        if(stat[0]):
            ready_button.setStyleSheet(style_green)
        else:
            ready_button.setStyleSheet(style_grey)
        if(stat[1]):
            start_button.setStyleSheet(style_green)
        else:
            start_button.setStyleSheet(style_grey)
        if(stat[2]):
            set_pos_button.setStyleSheet(style_green)
        else:
            set_pos_button.setStyleSheet(style_grey)
        if(stat[3]):
            reset_eeprom_button.setStyleSheet(style_green)
        else:
            reset_eeprom_button.setStyleSheet(style_grey)

def getCommand():
    command = ser.getCommand()
    if(command):
        if(command.type == 1 and \
            command.operation == 1 and \
            command.code == 4):
            update(command.data)

def sendCommand():
    ser.sendCommand()

def getBtnStatus():
    btn_status = ser.getBtnStatus()
    if(btn_status):
        btnsUpdate(btn_status)

def getAndSendCommand():
    getCommand()
    sleep(0.050)
    sendCommand()
    getBtnStatus()

if(ser.isOpen()) or (ser.dummyMode()):
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(getAndSendCommand)
    timer.start(100)
else:
    print("something is wrong with the update call")
# Start Qt event loop unless running in interactive mode.

if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
