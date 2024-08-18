import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 

class graph_free_fall(pg.PlotItem):
    
    def __init__(self, parent=None, name=None, labels=None, title='Caída libre', viewBox=None, axisItems=None, enableMenu=True, font = None,**kargs):    
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)

        self.hideAxis('bottom')
        self.hideAxis('left')
        self.invertX(False)
        self.invertY(True)
        self.proxy = QtWidgets.QGraphicsProxyWidget()
        self.label = QLabel()
        self.label.setFont(QFont('Arial', 10))
        self.label.setStyleSheet("inline-size: min-content;margin: 3px;text-align: center;color: white;background-color: rgb(33, 33, 33);")
        self.label.setText("No")
        self.proxy.setWidget(self.label)
        if font != None:
            self.label.setFont(font)
        self.addItem(self.proxy)

    def update(self, value):
        self.label.setText("")
        if(int(value) == 0):
            self.label.setText('No')
        else:
            self.label.setText('Si')