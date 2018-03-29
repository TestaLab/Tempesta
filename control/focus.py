# -*- coding: utf-8 -*-
"""
Created on Wed Oct  1 13:41:48 2014

@authors: Federico Barabas, Luciano Masullo, Shusei Masuda
"""

import numpy as np
import time
import scipy.ndimage as ndi
from skimage.feature import peak_local_max

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime

from lantz import Q_
import control.pi as pi

from instrumental import u


class FocusWidget(QtGui.QFrame):

    def __init__(self, scanZ, webcam, main=None, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setMinimumSize(2, 350)

        self.main = main  # main va a ser RecordingWidget de control.py
        self.z = scanZ
        self.webcam = webcam
        self.setPoint = 0
        self.calibrationResult = [0, 0]
        self.locked = False
        self.n = 1
        self.max_dev = 0
        self.twoFociVar = False

        self.V = Q_(1, 'V')
        self.um = Q_(1, 'um')
        self.nm = Q_(1, 'nm')

        # Focus lock widgets
        self.kpEdit = QtGui.QLineEdit('0.008')
        self.kpEdit.textChanged.connect(self.unlockFocus)
        self.kpLabel = QtGui.QLabel('kp')
        self.kiEdit = QtGui.QLineEdit('0.0006')
        self.kiEdit.textChanged.connect(self.unlockFocus)
        self.kiLabel = QtGui.QLabel('ki')
        self.lockButton = QtGui.QPushButton('Lock')
        self.lockButton.setCheckable(True)
        self.lockButton.clicked.connect(self.toggleFocus)
        self.lockButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                      QtGui.QSizePolicy.Expanding)
        self.focusDataBox = QtGui.QCheckBox('Save focus data')
        self.twoFociBox = QtGui.QCheckBox('Two foci')

        # PZT position widgets
        time.sleep(0.1)
        self.positionLabel = QtGui.QLabel('Position[um]')
        self.positionEdit = QtGui.QLineEdit(str(
            self.z.position).split(' ')[0])
        self.positionSetButton = QtGui.QPushButton('Set')
        self.positionSetButton.clicked.connect(self.movePZT)

        # focus calibration widgets
        self.CalibFromLabel = QtGui.QLabel('from [um]')
        self.CalibFromEdit = QtGui.QLineEdit('49')
        self.CalibToLabel = QtGui.QLabel('to [um]')
        self.CalibToEdit = QtGui.QLineEdit('51')
        self.focusCalibThread = FocusCalibThread(self)
        self.focusCalibButton = QtGui.QPushButton('Calib')
        self.focusCalibButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                            QtGui.QSizePolicy.Expanding)
        self.focusCalibButton.clicked.connect(self.focusCalibThread.start)
        self.CalibCurveButton = QtGui.QPushButton('See Calib')
        self.CalibCurveButton.clicked.connect(self.showCalibCurve)
        self.CalibCurveWindow = CaribCurveWindow(self)
        try:
            prevCal = np.around(np.loadtxt('calibration')[0]/10)
            text = '1 px --> {} nm'.format(prevCal)
            self.calibrationDisplay = QtGui.QLineEdit(text)
        except:
            self.calibrationDisplay = QtGui.QLineEdit('0 px --> 0 nm')
        self.calibrationDisplay.setReadOnly(False)

        # focus lock graph widget
        self.focusLockGraph = FocusLockGraph(self, main)
        self.webcamGraph = WebcamGraph()

        # Thread for getting the data and processing it
        self.processDataThread = ProcessDataThread(self)
        self.processDataThread.start()

        # GUI layout
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.focusLockGraph, 0, 0, 1, 8)
        grid.addWidget(self.webcamGraph, 1, 0, 1, 8)
        grid.addWidget(self.focusCalibButton, 2, 2, 2, 1)
        grid.addWidget(self.calibrationDisplay, 4, 0, 1, 2)
        grid.addWidget(self.kpLabel, 2, 3)
        grid.addWidget(self.kpEdit, 2, 4)
        grid.addWidget(self.kiLabel, 3, 3)
        grid.addWidget(self.kiEdit, 3, 4)
        grid.addWidget(self.lockButton, 2, 5, 2, 1)
        grid.addWidget(self.focusDataBox, 4, 4, 1, 2)
        grid.addWidget(self.twoFociBox, 4, 6)
        grid.addWidget(self.CalibFromLabel, 2, 0)
        grid.addWidget(self.CalibFromEdit, 2, 1)
        grid.addWidget(self.CalibToLabel, 3, 0)
        grid.addWidget(self.CalibToEdit, 3, 1)
        grid.addWidget(self.CalibCurveButton, 4, 2)
        grid.addWidget(self.positionLabel, 2, 6)
        grid.addWidget(self.positionEdit, 2, 7)
        grid.addWidget(self.positionSetButton, 3, 6, 1, 2)

#        grid.setColumnMinimumWidth(1, 100)
#        grid.setColumnMinimumWidth(2, 40)
#        grid.setColumnMinimumWidth(0, 100)

        self.twoFociBox.stateChanged.connect(self.twoFociVarChange)

    def movePZT(self):
        self.z.moveAbsolute(
            float(self.positionEdit.text().split(' ')[0]) * self.um)

    def toggleFocus(self):
        if self.lockButton.isChecked():
            self.lockFocus()
        else:
            self.unlockFocus()

    def lockFocus(self):
        if not self.locked:
            self.locked = True
            self.lockButton.setChecked(True)
            self.setPoint = self.processDataThread.focusSignal
            self.focusLockGraph.line = self.focusLockGraph.plot.addLine(
                y=self.setPoint, pen='r')
            self.PI = pi.PI(self.setPoint,
                            np.float(self.kpEdit.text()),
                            np.float(self.kiEdit.text()))
            self.initialZ = self.z.position

    def unlockFocus(self):
        if self.locked:
            self.locked = False
            self.lockButton.setChecked(False)
            self.focusLockGraph.plot.removeItem(self.focusLockGraph.line)

    # Toggles between two different formulas for finding the focus signal,
    # use two foci when there are two clear maxima in the focus signal image.
    def twoFociVarChange(self):
        if self.twoFociVar:
            self.twoFociVar = False
        else:
            self.twoFociVar = True
            
    def updatePI(self):
        # TODO: explain ifs
        self.distance = self.z.position - self.initialZ
        #        out = self.PI.update(self.stream.newData)
        out = self.PI.update(self.processDataThread.focusSignal)
        if abs(self.distance) > 10 * self.um or abs(out) > 5:
            self.unlockFocus()
        else:
            self.z.moveRelative(out * self.um)

    def exportData(self):
        self.sizeofData = np.size(self.focusLockGraph.savedDataSignal)
        self.savedData = [np.ones(self.sizeofData)*self.setPoint,
                          self.focusLockGraph.savedDataSignal,
                          self.focusLockGraph.savedDataTime]
        np.savetxt('{}_focusdata'.format(self.main.filename()), self.savedData)
        self.focusLockGraph.savedDataSignal = []
        self.focusLockGraph.savedDataTime = []

    def analizeFocus(self):
        if self.n == 1:
            self.mean = self.processDataThread.focusSignal
            self.mean2 = self.processDataThread.focusSignal**2
        else:
            self.mean += (self.processDataThread.focusSignal -
                          self.mean)/self.n
            self.mean2 += (self.processDataThread.focusSignal**2 -
                           self.mean2)/self.n

        self.std = np.sqrt(self.mean2 - self.mean**2)

        self.max_dev = np.max([self.max_dev,
                              self.processDataThread.focusSignal -
                              self.setPoint])

        statData = 'std = {}    max_dev = {}'.format(np.round(self.std, 3),
                                                     np.round(self.max_dev, 3))
        self.focusLockGraph.statistics.setText(statData)

        self.n += 1

    def showCalibCurve(self):
        self.CalibCurveWindow.run()
        self.CalibCurveWindow.show()

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)


class ProcessDataThread(QtCore.QThread):

    def __init__(self, focusWidget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.focusWidget = focusWidget
        # set the camera
        """
        uc480 camera

        default exposureTime: 10 ms
                vsub: 1024 pix
                hsub: 1280 pix
        """
        self.webcam = self.focusWidget.webcam
        self.ws = {'vsub': 4, 'hsub': 4,
                   'top': None, 'bot': None,
                   'exposure_time': 10*u.ms}
        self.image = self.webcam.grab_image(vsub=self.ws['vsub'],
                                            hsub=self.ws['hsub'],
                                            top=self.ws['top'],
                                            bot=self.ws['bot'],
                                            exposure_time=self.ws[
                                            'exposure_time'])

        self.sensorSize = np.array(self.image.shape)

        self.focusSignal = 0

        self.scansPerS = 10
        self.focusTime = 1000 / self.scansPerS
        self.focusBoxSize = 150

    def run(self):
        while True:
            self.update()
            self.msleep(int(self.focusTime))

    def update(self):
        self.updateFS()
        self.focusWidget.webcamGraph.update(self.image)
        self.focusWidget.focusLockGraph.update(self.focusSignal)
        # update the PI control
        if self.focusWidget.locked:
            self.focusWidget.updatePI()

    def updateFS(self):
        try:
            self.image = self.webcam.grab_image()
        except:
            pass
        
        #Take a sub-part of the image and gaussian filter it, to remove strong
        # reflections that can interfere and to lower the influence of noise
        # in the case of a low signal especially.
        imagearray = np.array(self.image)
        imagearray = imagearray[:, :]
        imagearraygf = ndi.filters.gaussian_filter(imagearray, 5)

        # If there are two strong maxima in the image, follow only the top one. 
        if self.focusWidget.twoFociVar:
            allmaxcoords = peak_local_max(imagearraygf, min_distance=100)
            size = allmaxcoords.shape
            maxvals = np.zeros(size[0])
            maxvalpos = np.zeros(2)
            for n in range(0, size[0]):
                if imagearraygf[allmaxcoords[n][0], allmaxcoords[n][1]] > maxvals[0]:
                    if imagearraygf[allmaxcoords[n][0], allmaxcoords[n][1]] > maxvals[1]:
                        tempval = maxvals[1]
                        maxvals[0] = tempval
                        maxvals[1] = imagearraygf[allmaxcoords[n][0], allmaxcoords[n][1]]
                        tempval = maxvalpos[1]
                        maxvalpos[0] = tempval
                        maxvalpos[1] = n
                    else:
                        maxvals[0] = imagearraygf[allmaxcoords[n][0], allmaxcoords[n][1]]
                        maxvalpos[0] = n
            xcenter = allmaxcoords[maxvalpos[0]][0]
            ycenter = allmaxcoords[maxvalpos[0]][1]
            if allmaxcoords[maxvalpos[1]][1] < ycenter:
                xcenter = allmaxcoords[maxvalpos[1]][0]
                ycenter = allmaxcoords[maxvalpos[1]][1]
            centercoords2 = np.array([xcenter, ycenter])
        else:
            centercoords = np.where(imagearraygf == np.array(imagearraygf.max()))
            centercoords2 = np.array([centercoords[0][0], centercoords[1][0]])

        # Calculate the center of mass on only a small sub box with the max,
        # to remove influence of noise outside the maximum.
        xlow = max(0, (centercoords2[0] - self.focusBoxSize / 2))
        xhigh = min(1024, (centercoords2[0] + self.focusBoxSize / 2))
        ylow = max(0, (centercoords2[1] - self.focusBoxSize / 2))
        yhigh = min(1280, (centercoords2[1] + self.focusBoxSize / 2))
        imagearraygfsub = imagearraygf[xlow:xhigh,ylow:yhigh]
        self.image = imagearraygf
        self.massCenter = np.array(ndi.measurements.center_of_mass(imagearraygfsub))
        self.massCenter[0] = self.massCenter[0] + centercoords2[0] - self.focusBoxSize / 2 - self.sensorSize[0] / 2
        self.massCenter[1] = self.massCenter[1] + centercoords2[1] - self.focusBoxSize / 2 - self.sensorSize[1] / 2
        self.focusSignal = self.massCenter[1]

class FocusLockGraph(pg.GraphicsWindow):

    def __init__(self, focusWidget, main=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.focusWidget = focusWidget
        self.main = main
        self.analize = self.focusWidget.analizeFocus
        self.focusDataBox = self.focusWidget.focusDataBox
        self.savedDataSignal = []
        self.savedDataTime = []
        self.savedDataPosition = []

        self.setWindowTitle('Focus')
        self.setAntialiasing(True)

        self.npoints = 400
        self.data = np.zeros(self.npoints)
        self.ptr = 0

        # Graph without a fixed range
        self.statistics = pg.LabelItem(justify='right')
        self.addItem(self.statistics)
        self.statistics.setText('---')
        self.plot = self.addPlot(row=1, col=0)
        self.plot.setLabels(bottom=('Tiempo', 's'),
                            left=('Laser position', 'px'))
        self.plot.showGrid(x=True, y=True)
        self.focusCurve = self.plot.plot(pen='y')

        self.time = np.zeros(self.npoints)
        self.startTime = ptime.time()

        if self.main is not None:
            self.recButton = self.main.recButton

    def update(self, focusSignal):
        """ Update the data displayed in the graphs"""
        self.focusSignal = focusSignal

        if self.ptr < self.npoints:
            self.data[self.ptr] = self.focusSignal
            self.time[self.ptr] = ptime.time() - self.startTime
            self.focusCurve.setData(self.time[1:self.ptr + 1],
                                    self.data[1:self.ptr + 1])

        else:
            self.data[:-1] = self.data[1:]
            self.data[-1] = self.focusSignal
            self.time[:-1] = self.time[1:]
            self.time[-1] = ptime.time() - self.startTime

            self.focusCurve.setData(self.time, self.data)

        self.ptr += 1

        if self.main is not None:

            if self.recButton.isChecked():
                self.savedDataSignal.append(self.focusSignal)
                self.savedDataTime.append(self.time[-1])
#               self.savedDataPosition.append(self.DAQ.position)

            if self.recButton.isChecked():
                self.analize()


class WebcamGraph(pg.GraphicsWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pg.ImageItem(border='w')
        self.view = self.addViewBox(invertY=True, invertX=False)
        self.view.setAspectLocked(True)  # square pixels
        self.view.addItem(self.image)

    def update(self, image):
        self.image.setImage(image)


class FocusCalibThread(QtCore.QThread):

    def __init__(self, focusWidget, *args, **kwargs):

        super().__init__(*args, **kwargs)

#        self.stream = mainwidget.stream
        self.z = focusWidget.z
        self.focusWidget = focusWidget  # mainwidget será FocusLockWidget
        self.um = Q_(1, 'micrometer')

    def run(self):
        self.signalData = []
        self.positionData = []
        self.start = np.float(self.focusWidget.CalibFromEdit.text())
        self.end = np.float(self.focusWidget.CalibToEdit.text())
        self.scan_list = np.round(np.linspace(self.start, self.end, 20), 2)
        for x in self.scan_list:
            self.z.moveAbsolute(x * self.um)
            time.sleep(0.5)
            self.focusCalibSignal = \
                self.focusWidget.processDataThread.focusSignal
            self.signalData.append(self.focusCalibSignal)
            self.positionData.append(self.z.position.magnitude)

        self.poly = np.polyfit(self.positionData, self.signalData, 1)
        self.calibrationResult = np.around(self.poly, 4)
        self.export()

    def export(self):

        np.savetxt('calibration', self.calibrationResult)
        cal = self.poly[0]
        calText = '1 px --> {} nm'.format(np.round(1000/cal, 1))
        self.focusWidget.calibrationDisplay.setText(calText)
        d = [self.positionData, self.calibrationResult[::-1]]
        self.savedCalibData = [self.positionData,
                               self.signalData,
                               np.polynomial.polynomial.polyval(d[0], d[1])]
        np.savetxt('calibrationcurves', self.savedCalibData)


class CaribCurveWindow(QtGui.QFrame):
    def __init__(self, focusWidget):
        super().__init__()
        self.main = focusWidget
        self.FocusCalibGraph = FocusCalibGraph(focusWidget)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.FocusCalibGraph, 0, 0)

    def run(self):
        self.FocusCalibGraph.draw()


class FocusCalibGraph(pg.GraphicsWindow):

    def __init__(self, focusWidget, main=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.focusWidget = focusWidget

        # Graph without a fixed range
        self.plot = self.addPlot(row=1, col=0)
        self.plot.setLabels(bottom=('Piezo position', 'um'),
                            left=('Laser position', 'px'))
        self.plot.showGrid(x=True, y=True)

    def draw(self):
        self.plot.clear()
        self.signalData = self.focusWidget.focusCalibThread.signalData
        self.positionData = self.focusWidget.focusCalibThread.positionData
        self.poly = self.focusWidget.focusCalibThread.poly
        self.plot.plot(self.positionData,
                       self.signalData, pen=None, symbol='o')
        self.plot.plot(self.positionData,
                       np.polyval(self.poly, self.positionData), pen='r')


# class daqStream(QtCore.QObject):
#     """This stream only takescare of getting data from the Labjack device."""
#     """This object is not used in the current version of the focuslock """
#     def __init__(self, DAQ, scansPerS, *args, **kwargs):
#
#         super(daqStream, self).__init__(*args, **kwargs)
#
#         self.DAQ = DAQ
#         self.scansPerS = scansPerS
#         self.port = 'AIN0'
#         names = [self.port + "_NEGATIVE_CH", self.port + "_RANGE",
#                  "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
#         # single-ended, +/-1V, 0, 0 (defaults)
#         # Voltage Ranges: ±10V, ±1V, ±0.1V, and ±0.01V
#         values = [self.DAQ.constants.GND, 0.1, 0, 0]
#         self.DAQ.writeNames(names, values)
#         self.newData = 0.0
#
#     def start(self):
#         scanRate = 5000
#         scansPerRead = int(scanRate/self.scansPerS)
#         portAddress = self.DAQ.address(self.port)[0]
#         scanRate = self.DAQ.streamStart(scansPerRead, [portAddress],
#                                                              scanRate)
#         self.newData = np.mean(self.DAQ.streamRead()[0])
#         self.timer = QtCore.QTimer()
#         self.timer.timeout.connect(self.update)
#         self.timer.start(1)
#
#     def stop(self):
#         pass
#         # TODO: stop
#
#     def update(self):
#         self.newData = np.mean(self.DAQ.streamRead()[0])
