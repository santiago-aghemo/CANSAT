import pyqtgraph as pg
import numpy as np

class graph_co(pg.PlotItem):

    def __init__(self, parent=None, name=None, labels=None, title='Nivel de CO', viewBox=None, axisItems=None, enableMenu=True, **kargs):
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)
        self.co_plot = self.plot(pen=(29, 185, 84))
        self.co_data = np.linspace(0, 0, 30)
        self.ptr1 = 0

    def update(self, value):
        self.co_plot, self.co_data,  self.ptr1
        self.co_data[:-1] = self.co_data[1:]
        self.co_data[-1] = float(value)
        self.ptr1 += 1
        self.co_plot.setData(self.co_data)
        self.co_plot.setPos(self.ptr1, 0)