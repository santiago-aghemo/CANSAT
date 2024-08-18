import pyqtgraph as pg
import numpy as np

class graph_pm25(pg.PlotItem):

    def __init__(self, parent=None, name=None, labels=None, title='Partículas PM2.5', viewBox=None, axisItems=None, enableMenu=True, **kargs):
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)
        self.pm25_plot = self.plot(pen=(29, 185, 84))
        self.pm25_data = np.linspace(0, 0, 30)
        self.ptr1 = 0

    def update(self, value):
        self.pm25_plot, self.pm25_data,  self.ptr1
        self.pm25_data[:-1] = self.pm25_data[1:]
        self.pm25_data[-1] = float(value)
        self.ptr1 += 1
        self.pm25_plot.setData(self.pm25_data)
        self.pm25_plot.setPos(self.ptr1, 0)