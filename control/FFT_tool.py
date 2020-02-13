# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 14:26:18 2018

@author: MonaLisa
"""
import os
import sys

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea

if not os.environ['PY_UTILS_PATH'] in sys.path:
    sys.path.append(os.environ['PY_UTILS_PATH'])
import DataIO_tools
import Pattern_finder

# taken from https://www.mrao.cam.ac.uk/~dag/CUBEHELIX/cubehelix.py
def cubehelix(gamma=1.0, s=0.5, r=-1.5, h=1.0):
    def get_color_function(p0, p1):
        def color(x):
            xg = x ** gamma
            a = h * xg * (1 - xg) / 2
            phi = 2 * np.pi * (s / 3 + r * x)
            return xg + a * (p0 * np.cos(phi) + p1 * np.sin(phi))
        return color

    array = np.empty((256, 3))
    abytes = np.arange(0, 1, 1/256.)
    array[:, 0] = get_color_function(-0.14861, 1.78277)(abytes) * 255
    array[:, 1] = get_color_function(-0.29227, -0.90649)(abytes) * 255
    array[:, 2] = get_color_function(1.97294, 0.0)(abytes) * 255
    return array

class FFTWidget(QtGui.QFrame):
    """ FFT Transform window for alignment """
    def __init__(self, main, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.main = main
        self.f = None #Variable where the future FFT is saved.
        self.initLines = False
        self.double_exposure = False
        self.frame_type = 'Even'

        # Vertical and horizontal lines
        self.vline = pg.InfiniteLine()
        self.hline = pg.InfiniteLine()
        self.rvline = pg.InfiniteLine()
        self.lvline = pg.InfiniteLine()
        self.uhline = pg.InfiniteLine()
        self.dhline = pg.InfiniteLine()

        self.vline.hide()
        self.hline.hide()
        self.rvline.hide()
        self.lvline.hide()
        self.uhline.hide()
        self.dhline.hide()

        self.pat_finder = Pattern_finder.pattern_finder()

        #Abs och angle
        self.magRadio = QtGui.QRadioButton('Magnitude')
        self.magRadio.toggled.connect(self.MagPhaseToggled)
        self.phaseRadio = QtGui.QRadioButton('Phase')
        self.phaseRadio.toggled.connect(self.MagPhaseToggled)
        self.magRadio.setChecked(True)

        #Extracted period and phase
        self.extr_per_hori_label = QtGui.QLabel('Estimated horizontal period:')
        self.extr_per_hori_val = QtGui.QLabel('-')
        self.extr_phase_hori_label = QtGui.QLabel('Estimated horizontal phase:')
        self.extr_phase_hori_val = QtGui.QLabel('-')
        self.extr_per_vert_label = QtGui.QLabel('Estimated vertical period:')
        self.extr_per_vert_val = QtGui.QLabel('-')
        self.extr_phase_vert_label = QtGui.QLabel('Estimated vertical phase:')
        self.extr_phase_vert_val = QtGui.QLabel('-')


        # Do FFT button
        self.doButton = QtGui.QPushButton('Do FFT')
        self.doButton.clicked.connect(self.Update_All)

        self.liveUpdate = QtGui.QCheckBox('Liveview')
        self.hori_check = QtGui.QCheckBox('Show horizontal')
        self.hori_check.clicked.connect(self.Show_vert_hori)
        self.hori_check.setChecked(True)
        self.vert_check = QtGui.QCheckBox('Show vertical')
        self.vert_check.clicked.connect(self.Show_vert_hori)
        self.vert_check.setChecked(True)


        # Period button and text for changing the vertical lines
        self.showPeriodLines = QtGui.QCheckBox('Show period lines')
        self.showPeriodLines.clicked.connect(self.togglePeriodLines)

        self.PeriodText= QtGui.QLabel('Period')
        self.editPeriod = QtGui.QSpinBox()
        self.editPeriod.setRange(1, 10000)
        self.editPeriod.setValue(750)
        self.editPeriod.editingFinished.connect(self.changePeriod)

        self.editPxSize = QtGui.QSpinBox()
        self.editPxSize.setRange(1,1000)
        self.editPxSize.setValue(65)
        self.editPxSize.editingFinished.connect(self.changePeriod)
        self.PxSizeText= QtGui.QLabel('Pixel Size')

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        self.cwidget = pg.GraphicsLayoutWidget()

        self.vb = self.cwidget.addViewBox(row=0, col=0)
        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.vb.setLimits(yMin=0, yMax=66000)
        self.cubehelixCM = pg.ColorMap(np.arange(0, 1, 1/256), cubehelix().astype(int))
        self.hist.gradient.setColorMap(self.cubehelixCM)
        for tick in self.hist.gradient.ticks:
            tick.hide()
        self.cwidget.addItem(self.hist, row=0, col=1)

        self.p = 1 / (self.editPeriod.value() / self.editPxSize.value())

        self.vb.addItem(self.vline)
        self.vb.addItem(self.hline)
        self.vb.addItem(self.lvline)
        self.vb.addItem(self.rvline)
        self.vb.addItem(self.uhline)
        self.vb.addItem(self.dhline)

        self.peaks_scatter = pg.ScatterPlotItem()
        self.peaks_scatter.setData(pen=pg.mkPen(color=(255, 0, 0), width=0.5,
                         style=QtCore.Qt.SolidLine, antialias=True),
            brush=pg.mkBrush(color=(255, 0, 0), antialias=True), size=5,
            pxMode=False)

        self.vb.addItem(self.peaks_scatter)

        MainDockArea = DockArea()


        imageDock = Dock('Image', size=(1,1))
        imageDock.addWidget(self.cwidget)
        MainDockArea.addDock(imageDock)

        plotDock = Dock('Phase plot', size=(1,1))
        self.phaseplot = PhasePlot(4, [pg.mkPen(255,0,0),
                                       pg.mkPen(255,255,0),
                                       pg.mkPen(0,255,0),
                                       pg.mkPen(0,255,255)])
        plotDock.addWidget(self.phaseplot)
        MainDockArea.addDock(plotDock)

        grid.addWidget(MainDockArea, 0, 0, 1, 6)
        grid.addWidget(self.magRadio, 1, 0, 1, 1)
        grid.addWidget(self.phaseRadio, 1, 1, 1, 1)
        grid.addWidget(self.extr_per_hori_label, 1, 2, 1, 1)
        grid.addWidget(self.extr_per_hori_val, 1, 3, 1, 1)
        grid.addWidget(self.extr_phase_hori_label, 1, 4, 1, 1)
        grid.addWidget(self.extr_phase_hori_val, 1, 5, 1, 1)
        grid.addWidget(self.extr_per_vert_label, 2, 2, 1, 1)
        grid.addWidget(self.extr_per_vert_val, 2, 3, 1, 1)
        grid.addWidget(self.extr_phase_vert_label, 2, 4, 1, 1)
        grid.addWidget(self.extr_phase_vert_val, 2, 5, 1, 1)
        grid.addWidget(self.doButton, 3, 0, 1, 1)
        grid.addWidget(self.liveUpdate, 3, 1, 1, 1)
        grid.addWidget(self.vert_check, 3, 2, 1, 1)
        grid.addWidget(self.hori_check, 3, 3, 1, 1)
        grid.addWidget(self.PeriodText, 4, 0, 1, 1)
        grid.addWidget(self.editPeriod, 4, 1, 1, 1)
        grid.addWidget(self.PxSizeText, 4, 2, 1, 1)
        grid.addWidget(self.editPxSize, 4, 3, 1, 1)
        grid.addWidget(self.showPeriodLines, 4, 4, 1, 1)
        grid.setRowMinimumHeight(0, 300)


    def Show_vert_hori(self):
        self.phaseplot.show_hori = self.hori_check.isChecked()
        self.phaseplot.show_vert = self.vert_check.isChecked()


    def MagPhaseToggled(self):
        if self.magRadio.isChecked():
            self.f = None #So that it autoscales

    def Update_All(self):
        self.doFFT()
        self.est_values = self.pat_finder.find_pattern(self.images)
#        values = [self.getPhaseValues(self.f[i]) for i in range(len(self.f))]
#        self.phaseplot.update2(np.multiply(self.est_values, self.editPxSize.value()))
        self.phaseplot.update(0, self.est_values[0])
        self.phaseplot.update(1, self.est_values[1])
        self.phaseplot.update(2, self.est_values[2])
        self.phaseplot.update(3, self.est_values[3])

        self.UpdateEstimatedValues()

    def UpdateEstimatedValues(self):

        vert_center = len(self.f[0])*0.5
        hori_center = len(self.f[0][0])*0.5
        peak_coords_vert = vert_center + 2*vert_center/self.est_values[2]
        peak_coords_hori = hori_center + 2*hori_center/self.est_values[3]

        self.peaks_scatter.setData([{'pos': (peak_coords_hori, vert_center)},
                                     {'pos': (hori_center, peak_coords_vert)}])

        self.extr_per_hori_val.setText("{:.2f}".format(self.est_values[3]*self.editPxSize.value()))
        self.extr_phase_hori_val.setText("{:.2f}".format(self.est_values[1]*self.editPxSize.value()))
        self.extr_per_vert_val.setText("{:.2f}".format(self.est_values[2]*self.editPxSize.value()))
        self.extr_phase_vert_val.setText("{:.2f}".format(self.est_values[0]*self.editPxSize.value()))


    def getPhaseValues(self, im):
        if not self.f is None:
            coord_hori = int(0.5+self.p*im.shape[1])
            coord_vert = int(0.5+self.p*im.shape[0])
            v1 = im[0, coord_hori]
            v2 = im[coord_vert, 0]
            return [v1, v2]

    def doFFT(self):
        " FFT of the latest liveview image, centering (0, 0) in the middle with fftshift "

        autoL = self.f is None
        if self.double_exposure:
            self.images = self.main.curr_images.get_latest(self.main.currCamIdx, 'Both')
            self.f = [np.fft.fft2(self.images[i]) for i in range(len(self.images))]
            disp_im = self.f[self.frame_type == 'Odd']
        else:
            self.images = self.main.curr_images.get_latest(self.main.currCamIdx, 'All')
            self.f = [np.fft.fft2(self.images)]
            disp_im = self.f[0]

        if self.magRadio.isChecked():
            self.img.setImage(np.fft.fftshift(np.log10(abs(disp_im))), autoLevels=autoL)
        else:
            self.img.setImage(np.pi+np.fft.fftshift(np.angle(disp_im)), levels=[0, 6.28])

        # By default F = 0.25, period of T = 4 pixels
        self.vb.setAspectLocked()
        self.vb.setLimits(xMin=-0.5, xMax=self.img.width(), minXRange=4,
                  yMin=-0.5, yMax=self.img.height(), minYRange=4)

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)

    def changePeriod(self):
        print('changing period')
        self.p = 1 / (self.editPeriod.value() / self.editPxSize.value())
        self.vline.setValue(0.5*self.img.width())
        self.hline.setAngle(0)
        self.hline.setValue(0.5*self.img.height())
        self.rvline.setValue((0.5+self.p)*self.img.width())
        self.lvline.setValue((0.5-self.p)*self.img.width())
        self.dhline.setAngle(0)
        self.dhline.setValue((0.5-self.p)*self.img.height())
        self.uhline.setAngle(0)
        self.uhline.setValue((0.5+self.p)*self.img.height())

    def togglePeriodLines(self):
        print('toggling lines')
        if not self.initLines:
            self.changePeriod()

        if self.showPeriodLines.isChecked():
            self.vline.show()
            self.hline.show()
            self.rvline.show()
            self.lvline.show()
            self.uhline.show()
            self.dhline.show()
        else:
            self.vline.hide()
            self.hline.hide()
            self.rvline.hide()
            self.lvline.hide()
            self.uhline.hide()
            self.dhline.hide()

class PhasePlot(pg.GraphicsWindow):
    """Creates the plot that plots the preview of the pulses.
    Fcn update() updates the plot of "device" with signal "signal"."""
    def __init__(self, nr_graphs, pens, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert nr_graphs == len(pens)
        self.nr_graphs = nr_graphs
        self.plot = self.addPlot(row=1, col=0)
#        self.plot.setYRange(-np.pi, np.pi)
#        self.plot.setYRange(0, 1000)
        self.plot.showGrid(x=False, y=False)

        self.show_hori = True
        self.show_vert = True

#        self.seq_images = False
        self.sig_size = 1000
        self.signals = np.zeros([self.nr_graphs, self.sig_size])

        self.plots = [self.plot.plot(pen=pens[i]) for i in range(self.nr_graphs)]

    def reset_signals(self):
        for i in range(self.nr_graphs):
            self.signals[i] = np.zeros(self.sig_size)
            self.plots[i].setData(self.signals[i])

    def update(self, graph_nr, value):

        self.signals[graph_nr] = np.roll(self.signals[graph_nr], -1)
        self.signals[graph_nr][-1] = value
        self.plots[graph_nr].setData(self.signals[graph_nr])

#    def update2(self, values):
#        """Simply plots 2 phase values given in values"""
#
#        self.signals[0]['vertical'] = np.roll(self.signals[0]['vertical'], -1)
#        self.signals[0]['vertical'][-1] = values[0]
#        self.signals[0]['horizontal'] = np.roll(self.signals[0]['horizontal'], -1)
#        self.signals[0]['horizontal'][-1] = values[1]
#
#        if self.show_vert:
#            self.plots[0]['vertical'].setData(self.signals[0]['vertical'])
#        else:
#            self.plots[0]['vertical'].setData(np.zeros(self.sig_size))
#
#        if self.show_hori:
#            self.plots[0]['horizontal'].setData(self.signals[0]['horizontal'])
#        else:
#            self.plots[0]['horizontal'].setData(np.zeros(self.sig_size))
#
#    def update(self, values):
#        """Updates the values in the plot, can recieve either 2 or 4 values."""
#        for i in range(len(values)):
#            self.signals[i]['vertical'] = np.roll(self.signals[i]['vertical'], -1)
#            self.signals[i]['vertical'][-1] = np.angle(values[i][0])
#            self.signals[i]['horizontal'] = np.roll(self.signals[i]['horizontal'], -1)
#            self.signals[i]['horizontal'][-1] = np.angle(values[i][1])
#
#            if self.show_vert:
#                self.plots[i]['vertical'].setData(self.signals[i]['vertical'])
#            else:
#                self.plots[i]['vertical'].setData(np.zeros(self.sig_size))
#
#            if self.show_hori:
#                self.plots[i]['horizontal'].setData(self.signals[i]['horizontal'])
#            else:
#                self.plots[i]['horizontal'].setData(np.zeros(self.sig_size))
















