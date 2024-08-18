import pyqtgraph as pg
import numpy as np

class graph_humidity(pg.PlotItem):

    def __init__(self, parent=None, name=None, labels=None, title='Humedad Relativa', viewBox=None, axisItems=None, enableMenu=True, **kargs):
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)
        self.humidity_plot = self.plot(pen=(29, 185, 84))
        self.humidity_data = np.linspace(0, 0, 30)
        self.ptr1 = 0

    def update(self, value):
        self.humidity_plot, self.humidity_data,  self.ptr1
        self.humidity_data[:-1] = self.humidity_data[1:]
        self.humidity_data[-1] = float(value)
        self.ptr1 += 1
        self.humidity_plot.setData(self.humidity_data)
        self.humidity_plot.setPos(self.ptr1, 0)