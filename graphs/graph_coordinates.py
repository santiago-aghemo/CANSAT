import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 

class graph_coordinates(pg.PlotItem):
        
    def __init__(self, parent=None, name=None, labels=None, title='Coordenadas', viewBox=None, axisItems=None, enableMenu=True, font = None,**kargs):
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)

        self.hideAxis('bottom')
        self.hideAxis('left')
        self.hideButtons()
        self.enableAutoScale()
        self.invertX(False)
        self.invertY(True)
        self.proxy = QtWidgets.QGraphicsProxyWidget()
        self.label = QLabel()
        self.label.setFont(QFont('Arial', 10))
        self.label.setStyleSheet("width: 100%;margin-right: 5px;margin-left: 5px;color: white;background-color: rgb(33, 33, 33);")
        self.label.setText("lat: 230.9870\nlong: 123.8888")
        self.proxy.setWidget(self.label)
        if font != None:
            self.label.setFont(font)
        self.addItem(self.proxy)

    def update(self, latitude, longitude):
        self.label.setText("lat: " + str(latitude) + "\nlong: " + str(longitude))