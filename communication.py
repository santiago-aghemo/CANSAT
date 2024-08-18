from datetime import datetime
from distutils.cmd import Command
import random
import serial
import serial.tools.list_ports
import queue

q = queue.Queue()

class mCALCANCommand:
    type = None
    code = None
    operation = None
    data = []
def __init__(self):
    self.type = None
    self.code = None
    self.operation = None
    self.data = []

class Communication:
    baudrate = ''
    portName = ''
    dummyPlug = False
    ports = serial.tools.list_ports.comports()
    ser = serial.Serial()
    time = datetime.now()
    q = queue.Queue()
    qrcv = []
    btnStatus = [False, False, False, False]

    def __init__(self):
        self.baudrate = 115200
        print("the available ports are (if none appear, press any letter): ")
        for port in sorted(self.ports):
            # obtener la lista de puetos: https://stackoverflow.com/a/52809180
            print(("{}".format(port)))
        self.portName = input("write serial port name (ex: /dev/ttyUSB0): ")
        try:
            self.ser = serial.Serial(self.portName, self.baudrate, timeout=0.2, write_timeout=0.2)
        except serial.serialutil.SerialException:
            print("Can't open : ", self.portName)
            self.dummyPlug = True
            print("Dummy mode activated")

    def close(self):
        if(self.ser.isOpen()):
            self.ser.close()
        else:
            print(self.portName, " it's already closed")
    
    def mission_start(self):
        command = mCALCANCommand()
        command.type = 0
        command.operation = 2
        command.code = 0
        q.put(command)

    def mission_end(self):
        command = mCALCANCommand()
        command.type = 1
        command.operation = 2
        command.code = 6
        q.put(command)

    def set_coordinates(self, lat, long):
        command = mCALCANCommand()
        command.type = 0
        command.operation = 1
        command.code = 2
        command.data = [lat, long]
        q.put(command)
        print('set coordinates')

    def ready_to_launch(self):
        command = mCALCANCommand()
        command.type = 0
        command.operation = 0
        command.code = 3
        q.put(command)
        print('ready to launch')

    def reset_eeprom(self):
        command = mCALCANCommand()
        command.type = 0
        command.operation = 3
        command.code = 5
        q.put(command)
        print('reset eeprom')

    def reset_cansat(self):
        command = mCALCANCommand()
        command.type = 1
        command.operation = 3
        command.code = 7
        q.put(command)
        print('reset cansat')

    def sendCommand(self):
        while(q.qsize() > 0):
            command = q.get()
            command_chain = []
            command_chain.append('gvie')
            command_chain.append(str(command.type))
            command_chain.append(str(command.operation) + str(command.code))
            if(command.data):
                for value in command.data:
                    command_chain.append(str(value))
            command_str = ','
            command_str = command_str.join(command_chain) + '\n\r'
            if(command.type == 0):
                flag = False
                action = 'Sending'
                command.time = datetime.now()
                if(hasattr(command, 'retries') and command.retries < 3):
                    action = 'Retrying'
                    for rcv in self.qrcv:
                        if(command.operation == rcv.operation and \
                            command.code == rcv.code):
                            flag = True
                if (not hasattr(command, 'retries')):
                    flag = True
                    command.retries = 0
                    self.qrcv.append(command)
                if(flag and self.ser.isOpen()):
                    print(action + ' command ' + command_str)
                    try:
                        self.ser.write(command_str.encode("utf-8"))
                    except serial.SerialTimeoutException:
                        print('ERROR: unable to send command')
            else:
                if(self.ser.isOpen()):
                    print('Sending command ' + command_str)
                    try:
                        self.ser.write(command_str.encode("utf-8"))
                    except serial.SerialTimeoutException:
                        print('ERROR: unable to send command')

    def setBtnStatus(self, command):
        if(command.operation == 0 and \
            command.code == 3 ):
            self.btnStatus[0] = True
        if(command.operation == 2 and \
            command.code == 0 ):
            self.btnStatus[1] = True
        if(command.operation == 1 and \
            command.code == 2 ):
            self.btnStatus[2] = True
        if(command.operation == 3 and \
            command.code == 5 ):
            self.btnStatus[3] = True

    def resetBtns(self):
        self.btnStatus = [False, False, False, False]

    def getCommand(self):
        command = mCALCANCommand()
        if(self.dummyPlug == False):
            value = self.ser.readline()  # read line (single value) from the serial port
            #print(value)
            decoded_bytes = str(value[0:len(value) - 2].decode("utf-8"))
            print(decoded_bytes)
            i = 0
            for rcv in self.qrcv:
                actual_time = datetime.now()
                timeout = actual_time - rcv.time
                # response time expired 
                if(timeout.total_seconds() > 2 and \
                    rcv.retries < 3):
                    rcv.retries = rcv.retries + 1
                    rcv.time = datetime.now()
                    self.qrcv[i] = rcv
                    rcv.type = 0
                    q.put(rcv)
                # retries expired
                if(rcv.retries > 3):
                    self.qrcv.pop(i)
                i = i + 1
            command_chain = decoded_bytes.split(",")
            if(command_chain[0] != 'gvie'):
                return None
            try:
                command.type = int(command_chain[1])
                command.operation = int(command_chain[2][0])
                command.code = int(command_chain[2][1])
            except IndexError:
                print('ERROR: Invalid command received')
            
            if(len(command_chain) > 3):
                try:
                    command.data = command_chain[3:len(command_chain)]
                except IndexError:
                    print('ERROR: unable to get command data')
            if(command.type == 2):
                i = 0
                for rcv in self.qrcv:
                    # response is ok
                    if(command.operation == rcv.operation and \
                        command.code == rcv.code):
                        self.setBtnStatus(command)
                        self.qrcv.pop(i)
                        return command
                    i = i + 1
        else:
            command.type = 1
            command.operation = 1
            command.code = 4
            command.data = self.getData()
        return command


    def getData(self):
        actual_time = datetime.now()
        seconds = actual_time - self.time
        milisec = seconds.total_seconds() * 1000
        value_chain = [milisec] + random.sample(range(0, 300), 1) + \
            [random.getrandbits(1)] + random.sample(range(0, 20), 10) + \
                random.sample(range(1000, 3000), 2) +  random.sample(range(1, 8), 2)
        return value_chain

    def getBtnStatus(self):
        return self.btnStatus

    def isOpen(self):
        return self.ser.isOpen()

    def dummyMode(self):
        return self.dummyPlug 
