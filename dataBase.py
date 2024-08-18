import time
import csv


class data_base():
    def __init__(self):
        self.state = False
        self.mission = False

    def guardar(self, data):
        if self.state == True:
            data.append(time.asctime())
            with open("flight_data.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(data)
        if self.mission == True:
            data.append(time.asctime())
            with open("mission_data.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(data)

    def start(self):
        self.state = True
        print('starting storage in csv')

    def stop(self):
        self.state = False
        print('stopping storage in csv')

    def mission_start(self):
        self.mission = True
        print('starting mission')
        data = 'Tiempo Mision,' + \
        'altitud (m),' + \
        'caída libre,' + \
        'temperatura (°C),' + \
        'presión,' + \
        'giro,' + \
        'giro,' + \
        'giro,' + \
        'velocidad (m/s),' + \
        'velocidad (m/s),' + \
        'velocidad (m/s),' + \
        'humedad,' + \
        'co,' + \
        'latitud,' + \
        'longitud,' + \
        'nivel de batería,' + \
        'fecha\n'
        with open("mission_data.csv", "w") as f:
            f.write(data)
 
    def mission_stop(self):
        self.mission = False
        print('stopping mission')
        data = '\nMision Finalizada - ' + time.asctime()
        with open("mission_data.csv", "a") as f:
            f.write(data)