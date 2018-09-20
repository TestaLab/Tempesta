# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 14:26:18 2018

@author: MonaLisa
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea

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

        #Abs och angle
        self.magRadio = QtGui.QRadioButton('Magnitude')
        self.magRadio.toggled.connect(self.MagPhaseToggled)
        self.phaseRadio = QtGui.QRadioButton('Phase')
        self.phaseRadio.toggled.connect(self.MagPhaseToggled)
        self.magRadio.setChecked(True)

        # Do FFT button
        self.doButton = QtGui.QPushButton('Do FFT')
        self.doButton.clicked.connect(self.doFFT)

        self.liveUpdate = QtGui.QCheckBox('Liveview')
        self.liveUpdate.clicked.connect(self.startLiveview)
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

        MainDockArea = DockArea()


        imageDock = Dock('Image', size=(1,1))
        imageDock.addWidget(self.cwidget)
        MainDockArea.addDock(imageDock)

        plotDock = Dock('Phase plot', size=(1,1))
        self.phaseplot = PhasePlot()
        plotDock.addWidget(self.phaseplot)
        MainDockArea.addDock(plotDock)

        grid.addWidget(MainDockArea, 0, 0, 1, 6)
        grid.addWidget(self.magRadio, 1, 0, 1, 1)
        grid.addWidget(self.phaseRadio, 1, 1, 1, 1)
        grid.addWidget(self.doButton, 2, 0, 1, 1)
        grid.addWidget(self.liveUpdate, 2, 1, 1, 1)
        grid.addWidget(self.vert_check, 2, 2, 1, 1)
        grid.addWidget(self.hori_check, 2, 3, 1, 1)
        grid.addWidget(self.PeriodText, 3, 0, 1, 1)
        grid.addWidget(self.editPeriod, 3, 1, 1, 1)
        grid.addWidget(self.PxSizeText, 3, 2, 1, 1)
        grid.addWidget(self.editPxSize, 3, 3, 1, 1)
        grid.addWidget(self.showPeriodLines, 3, 4, 1, 1)
        grid.setRowMinimumHeight(0, 300)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.TimeOut)

    def Show_vert_hori(self):
        self.phaseplot.show_hori = self.hori_check.isChecked()
        self.phaseplot.show_vert = self.vert_check.isChecked()

    def startLiveview(self):
        if self.liveUpdate.isChecked():
            self.viewtimer.start(30)
        else:
            self.viewtimer.stop()

    def MagPhaseToggled(self):
        if self.magRadio.isChecked():
            self.f = None #So that it autoscales

    def TimeOut(self):
        self.doFFT()
        values = [self.getPhaseValues(self.f[i]) for i in range(len(self.f))]
        self.phaseplot.update(values)


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = self.addPlot(row=1, col=0)
        self.plot.setYRange(-np.pi, np.pi)
        self.plot.showGrid(x=False, y=False)

        self.show_hori = True
        self.show_vert = True

        self.seq_images = False
        self.sig_size = 1000
        self.signals = [{'vertical': np.zeros(self.sig_size),
        'horizontal': np.zeros(self.sig_size)},
        {'vertical': np.zeros(self.sig_size),
        'horizontal': np.zeros(self.sig_size)}]

        self.plots = [{'vertical': self.plot.plot(pen=pg.mkPen(255,0,0)),
        'horizontal': self.plot.plot(pen=pg.mkPen(0,0,255))},
        {'vertical': self.plot.plot(pen=pg.mkPen(255,100,100)),
        'horizontal': self.plot.plot(pen=pg.mkPen(100,100,255))}]

    def reset_signals(self):
        for i in [0,1]:
            for key in ['vertical', 'horizontal']:
                plot = self.plots[i][key]
                self.signals[i][key] = np.zeros(self.sig_size)
                plot.setData(self.signals[i][key])

    def update(self, values):
        """Updates the values in the plot, can recieve either 2 or 4 values."""
        for i in range(len(values)):
            self.signals[i]['vertical'] = np.roll(self.signals[i]['vertical'], -1)
            self.signals[i]['vertical'][-1] = np.angle(values[i][0])
            self.signals[i]['horizontal'] = np.roll(self.signals[i]['horizontal'], -1)
            self.signals[i]['horizontal'][-1] = np.angle(values[i][1])

            if self.show_vert:
                self.plots[i]['vertical'].setData(self.signals[i]['vertical'])
            else:
                self.plots[i]['vertical'].setData(np.zeros(self.sig_size))

            if self.show_hori:
                self.plots[i]['horizontal'].setData(self.signals[i]['horizontal'])
            else:
                self.plots[i]['horizontal'].setData(np.zeros(self.sig_size))
















