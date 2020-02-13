# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 10:32:36 2016

@authors: Luciano Masullo, Andreas Bodén, Shusei Masuda, Federico Barabas,
    Aurelién Barbotin.
"""

import os
import numpy as np
import time
import re
import configparser
import copy
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from PyQt4 import QtGui, QtCore

import matplotlib.pyplot as plt
import collections
import nidaqmx

import control.guitools as guitools

#from cv2 import rectangle, goodFeaturesToTrack, moments

# These dictionnaries contain values specific to the different axis of our
# piezo motors.
# They are the movements in µm induced by a command of 1V
convFactors = {'chan0': 2.88, 'chan1': 2.88, 'chan2': 2.88}
# Minimum and maximum voltages for the different piezos
minVolt = {'chan0': 0, 'chan1': 0, 'chan2': 0}
maxVolt = {'chan0': 10, 'chan1': 10, 'chan2': 10}


class Positionner(QtGui.QWidget):
    """This class communicates with the different analog outputs of the nidaq
    card. When not scanning, it drives the 3 axis x, y and z.

    :param ScanWidget main: main scan GUI"""

    def __init__(self, main):
        super().__init__()
        self.inUse = False #Set to false is the positioner is not to be used
        self.scanWidget = main
#        self.focusWgt = self.scanWidget.focusWgt

        # Position of the different devices in V
        self.x = 0.00
        self.y = 0.00
        self.z = 0.00

        # Parameters for the ramp (driving signal for the different channels)
        self.rampTime = 100  # Time for each ramp in ms
        self.sampleRate = 10**5
        self.nSamples = int(self.rampTime * 10**-3 * self.sampleRate)

        # This boolean is set to False when tempesta is scanning to prevent
        # this positionner to access the analog output channels
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]     # Order corresponds to self.channelOrder
        self.activate()


        # Axes control
        self.xLabel = QtGui.QLabel(
            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("+")
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("-")
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("0.05")
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel(
            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("+")
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("-")
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("0.05")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel(
            "<strong>z = {0:.2f} µm</strong>".format(self.z))
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("0.05")
        self.zStepUnit = QtGui.QLabel(" µm")

        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(self.xLabel, 1, 0)
        layout.addWidget(self.xUpButton, 1, 1)
        layout.addWidget(self.xDownButton, 1, 2)
        layout.addWidget(QtGui.QLabel("Step"), 1, 3)
        layout.addWidget(self.xStepEdit, 1, 4)
        layout.addWidget(self.xStepUnit, 1, 5)
        layout.addWidget(self.yLabel, 2, 0)
        layout.addWidget(self.yUpButton, 2, 1)
        layout.addWidget(self.yDownButton, 2, 2)
        layout.addWidget(QtGui.QLabel("Step"), 2, 3)
        layout.addWidget(self.yStepEdit, 2, 4)
        layout.addWidget(self.yStepUnit, 2, 5)
        layout.addWidget(self.zLabel, 3, 0)
        layout.addWidget(self.zUpButton, 3, 1)
        layout.addWidget(self.zDownButton, 3, 2)
        layout.addWidget(QtGui.QLabel("Step"), 3, 3)
        layout.addWidget(self.zStepEdit, 3, 4)
        layout.addWidget(self.zStepUnit, 3, 5)

    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""

        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        initPos = np.array(initPos, dtype=float)[:, np.newaxis]
        fullPos = np.repeat(initPos, self.nSamples, axis=1)

        # make position ramp for moving axis
        ramp = makeRamp(0, dist, self.nSamples)
        fullPos[self.activeChannels.index(axis)] += ramp

        # convert um to V and send signal to piezo
        factors = np.array([i for i in convFactors.values()])[:, np.newaxis]
        fullSignal = fullPos/factors
        self.aotask.write(fullSignal, auto_start=True)
        self.aotask.wait_until_done()
        self.aotask.stop()

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
        newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(newPos)
        getattr(self, axis + "Label").setText(newText)

    def xMoveUp(self):
        self.move('x', float(getattr(self, 'x' + "StepEdit").text()))

    def xMoveDown(self):
        self.move('x', -float(getattr(self, 'x' + "StepEdit").text()))

    def yMoveUp(self):
        self.move('y', float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveDown(self):
        self.move('y', -float(getattr(self, 'y' + "StepEdit").text()))

    def zMoveUp(self):
        self.move('z', float(getattr(self, 'z' + "StepEdit").text()))

    def zMoveDown(self):
        self.move('z', -float(getattr(self, 'z' + "StepEdit").text()))

#Concerning below, Fede wrote the resetChannels function. When using the AOM to
#to control the OFF pattern (Andreas) the activate/deactivate functions were
#written instead and intended to maybe in future be connected to a button in the GUI
#to activa/deactivate the positioner. At the moment the positioner is not used but
#might be useful in the future. The analog AOM modulation was clashing with the
#analog task of the positionner. Not properly tested!!

    def activate(self):
        if self.inUse:
            self.aotask = nidaqmx.Task("positionnerTask")

            for axis in self.activeChannels:
                n = self.AOchans[self.activeChannels.index(axis)]
                channel = "Dev1/ao%s" % n
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel=channel, name_to_assign_to_channel=axis,
                    min_val=minVolt[axis], max_val=maxVolt[axis])

            self.aotask.timing.cfg_samp_clk_timing(
                rate=self.sampleRate,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=self.nSamples)
            self.aotask.start()
            self.isActive = True

    def deactivate(self):
        if self.inUse:
            self.aotask.stop()
            self.aotask.close()
            del self.aotask
            self.isActive = False

#    def resetChannels(self, channels):
#        """Method called when the analog output channels need to be used by
#        another resource, typically for scanning. Deactivates the Positionner
#        when it is active and reactives it when it is not, typically after a
#        scan.
#
#        :param dict channels: the channels which are used or released by
#        another object. The positionner does not touch the other channels"""
#        if(self.isActive):
#            self.aotask.stop()
#            self.aotask.close()
#            del self.aotask
#            totalChannels = ["x", "y", "z"]
#            self.aotask = nidaqmx.Task("positionnerTask")
#
#            # returns a list containing the axis not in use
#            self.activeChannels = [
#                x for x in totalChannels if x not in channels]
#
#            try:
#                axis = self.activeChannels[0]
#                n = self.AOchans[self.activeChannels.index(axis)]
#                channel = "Dev1/ao%s" % n
#                self.aotask.ao_channels.add_ao_voltage_chan(
#                    physical_channel=channel, name_to_assign_to_channel=axis,
#                    min_val=minVolt[axis], max_val=maxVolt[axis])
#            except IndexError:
#                pass
#            self.isActive = False
#
#        else:
#            # Restarting the analog channels
#            self.aotask.stop()
#            self.aotask.close()
#            del self.aotask
#            self.aotask = nidaqmx.Task("positionnerTask")
#
#            totalChannels = ["x", "y", "z"]
#            self.activeChannels = totalChannels
#            for axis in totalChannels:
#                n = self.AOchans[self.activeChannels.index(axis)]
#                channel = "Dev1/ao%s" % n
#                self.aotask.ao_channels.add_ao_voltage_chan(
#                    physical_channel=channel, name_to_assign_to_channel=axis,
#                    min_val=minVolt[axis], max_val=maxVolt[axis])
#
#            self.aotask.timing.cfg_samp_clk_timing(
#                rate=self.sampleRate,
#                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                samps_per_chan=self.nSamples)
#            self.aotask.start()
#            self.isActive = True
#
#        for axis in self.activeChannels:
#            newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(0)
#            getattr(self, axis + "Label").setText(newText)

    def closeEvent(self, *args, **kwargs):
        if(self.isActive):
            # Resets the sliders, which will reset each channel to 0
            self.aotask.wait_until_done(timeout=2)
            self.aotask.stop()
            self.aotask.close()


def saveScan(scanWid):

        config = configparser.ConfigParser()
        config.optionxform = str

        config['pxParValues'] = scanWid.pxParValues
        config['scanParValues'] = scanWid.scanParValues
        config['Modes'] = {'scanMode': scanWid.scanMode.currentText(),
                           'scan_or_not': scanWid.scanRadio.isChecked()}
        fileName = QtGui.QFileDialog.getSaveFileName(scanWid, 'Save scan',
                                                     scanWid.scanDir)
        if fileName == '':
            return

        with open(fileName, 'w') as configfile:
            config.write(configfile)


def loadScan(scanWid):

    config = configparser.ConfigParser()
    config.optionxform = str

    fileName = QtGui.QFileDialog.getOpenFileName(scanWid, 'Load scan',
                                                 scanWid.scanDir)
    if fileName == '':
        return

    config.read(fileName)

    for key in scanWid.pxParValues:
        scanWid.pxParValues[key] = float(config._sections['pxParValues'][key])
        scanWid.pxParameters[key].setText(
            str(1000*float(config._sections['pxParValues'][key])))

    for key in scanWid.scanParValues:
        value = config._sections['scanParValues'][key]
        scanWid.scanParValues[key] = float(value)
        if key == 'seqTime':
            scanWid.scanPar[key].setText(
                str(1000*float(config._sections['scanParValues'][key])))
        else:
            scanWid.scanPar[key].setText(
                config._sections['scanParValues'][key])

    scanOrNot = (config._sections['Modes']['scan_or_not'] == 'True')
    scanWid.setScanOrNot(scanOrNot)
    if scanOrNot:
        scanWid.scanRadio.setChecked(True)
    else:
        scanWid.contLaserPulsesRadio.setChecked(True)

    scanMode = config._sections['Modes']['scanMode']
    scanWid.setScanMode(scanMode)
    scanWid.scanMode.setCurrentIndex(scanWid.scanMode.findText(scanMode))

    scanWid.updateScan(scanWid.allDevices)
    scanWid.graph.update()


class ScanWidget(QtGui.QMainWindow):
    ''' This class is intended as a widget in the bigger GUI, Thus all the
    commented parameters etc. It contain an instance of stageScan and
    pixel_scan which in turn harbour the analog and digital signals
    respectively.
    The function run starts the communication with the Nidaq through the
    Scanner object. This object was initially written as a QThread object but
    is not right now.
    As seen in the commened lines of run() I also tried running in a QThread
    created in run().
    The rest of the functions contain mostly GUI related code.'''
    def __init__(self, device, main, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scanInLiveviewWar = QtGui.QMessageBox()
        self.scanInLiveviewWar.setInformativeText(
            "You need to be in liveview to scan")

        self.digModWarning = QtGui.QMessageBox()
        self.digModWarning.setInformativeText(
            "You need to be in digital laser modulation and external "
            "frame-trigger acquisition mode")

        self.nidaq = device
        self.main = main
#        self.focusWgt = main.FocusLockWidget
#        self.focusLocked = self.focusWgt.locked

        # The port order in the NIDAQ follows this same order.
        # We chose to follow the temporal sequence order

        """Below is where to set the different devices to be used. The signal
         for each device is sent in the channel corresponding to the order of
         the devices. The array after the device name determines the color for
         the device in the graph"""
        self.Device_info = [['ON 405', 0, [130, 0, 200]],
                            ['OFF1 491', 1, [0, 247, 255]],
                            ['OFF2 491', 2, [0, 247, 255]],
                            ['Exc 488', 3, [0, 0, 255]],
                            ['Camera fr 1', 4, [255, 255, 255]],
                            ['Camera fr 2', 5, [255, 255, 255]]]

        self.allDevices = [x[0] for x in self.Device_info]
        self.devicechannels = [x[1] for x in self.Device_info]

        self.channelOrder = ['chan0', 'chan1', 'chan2'] #Just needs to be the same as the order of the channels in StageScan!

        self.saveScanBtn = QtGui.QPushButton('Save Scan')

        self.scanDir = os.path.join(self.main.controlFolder, 'scans')

        if not os.path.exists(self.scanDir):
            os.makedirs(self.scanDir)

        def saveScanFcn(): return saveScan(self)
        self.saveScanBtn.clicked.connect(saveScanFcn)
        self.loadScanBtn = QtGui.QPushButton('Load Scan')

        def loadScanFcn(): return loadScan(self)
        self.loadScanBtn.clicked.connect(loadScanFcn)

        self.sampleRateEdit = QtGui.QLineEdit()

        self.size_dim0Par = QtGui.QLineEdit('2')
        self.size_dim0Par.textChanged.connect(
            lambda: self.scanParameterChanged('size_dim0'))
        self.size_dim1Par = QtGui.QLineEdit('2')
        self.size_dim1Par.textChanged.connect(
            lambda: self.scanParameterChanged('size_dim1'))
        self.size_dim2Par = QtGui.QLineEdit('10')
        self.size_dim2Par.textChanged.connect(
            lambda: self.scanParameterChanged('size_dim2'))
        self.seqTimePar = QtGui.QLineEdit('10')     # ms
        self.seqTimePar.textChanged.connect(
            lambda: self.scanParameterChanged('seqTime'))
        self.nrFramesPar = QtGui.QLabel()
        self.scanDuration = 0
        self.scanDurationLabel = QtGui.QLabel(str(self.scanDuration))
        self.stepSize_dim0Par = QtGui.QLineEdit('0.1')
        self.stepSize_dim0Par.textChanged.connect(
            lambda: self.scanParameterChanged('stepSize_dim0'))
        self.stepSize_dim1Par = QtGui.QLineEdit('0.1')
        self.stepSize_dim1Par.textChanged.connect(
            lambda: self.scanParameterChanged('stepSize_dim1'))
        self.stepSize_dim2Par = QtGui.QLineEdit('1')
        self.stepSize_dim2Par.textChanged.connect(
            lambda: self.scanParameterChanged('stepSize_dim2'))
        self.sampleRate = 100000

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['1D scan', '2D scan', '3D scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(
            lambda: self.setScanMode(self.scanMode.currentText()))

        self.AOchans = ['0', '1', '2']

        self.primScanChan = QtGui.QComboBox()
        self.primScanChans = self.AOchans
        self.primScanChan.addItems(self.primScanChans)
        self.primScanChan.currentIndexChanged.connect(self.setPrimScanChan)

        self.secScanChan = QtGui.QComboBox()
        self.secScanChan.currentIndexChanged.connect(self.setSecScanChan)

        self.scanPar = {'size_dim0': self.size_dim0Par,
                        'size_dim1': self.size_dim1Par,
                        'size_dim2': self.size_dim2Par,
                        'seqTime': self.seqTimePar,
                        'stepSize_dim0': self.stepSize_dim0Par,
                        'stepSize_dim1': self.stepSize_dim1Par,
                        'stepSize_dim2': self.stepSize_dim2Par}

        self.scanParValues = {'size_dim0': float(self.size_dim0Par.text()),
                              'size_dim1': float(self.size_dim1Par.text()),
                              'size_dim2': float(self.size_dim2Par.text()),
                              'seqTime': 0.001*float(self.seqTimePar.text()),
                              'stepSize_dim0': float(self.stepSize_dim0Par.text()),
                              'stepSize_dim1': float(self.stepSize_dim1Par.text()),
                              'stepSize_dim2': float(self.stepSize_dim2Par.text())}


        self.pxParameters = dict()
        self.pxParValues = dict()


        for i in range(0, len(self.allDevices)):
            self.pxParameters['sta'+self.allDevices[i]] = QtGui.QLineEdit('0')
            self.pxParameters['sta'+self.allDevices[i]].textChanged.connect(
                lambda: self.pxParameterChanged())
            self.pxParameters['end'+self.allDevices[i]] = QtGui.QLineEdit('50')
            self.pxParameters['end'+self.allDevices[i]].textChanged.connect(
                lambda: self.pxParameterChanged())

            self.pxParValues['sta'+self.allDevices[i]] = 0.001*float(self.pxParameters['sta'+self.allDevices[i]].text())
            self.pxParValues['end'+self.allDevices[i]] = 0.001*float(self.pxParameters['end'+self.allDevices[i]].text())


        self.stageScan = StageScan(self.sampleRate)
        self.pxCycle = PixelCycle(self.sampleRate, self.allDevices)
        self.graph = GraphFrame(self.pxCycle, self.Device_info)
#        self.graph.plot.getAxis('bottom').setScale(1000/self.sampleRate)
#        self.graph.setFixedHeight(100)
        self.updateScan(self.allDevices)
        self.scanParameterChanged('seqTime')

        self.scanRadio = QtGui.QRadioButton('Scan')
        self.scanRadio.clicked.connect(lambda: self.setScanOrNot(True))
        self.scanRadio.setChecked(True)
        self.contLaserPulsesRadio = QtGui.QRadioButton('Cont. Laser Pulses')
        self.contLaserPulsesRadio.clicked.connect(
            lambda: self.setScanOrNot(False))

        self.scanButton = QtGui.QPushButton('Scan')
        self.scanning = False
        self.scanButton.clicked.connect(self.scanOrAbort)
        self.previewButton = QtGui.QPushButton('Plot scan path')
        self.previewButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                         QtGui.QSizePolicy.Expanding)
        self.previewButton.clicked.connect(self.previewScan)
        self.continuousCheck = QtGui.QCheckBox('Repeat')

        self.cwidget = QtGui.QWidget()
        self.setCentralWidget(self.cwidget)
        grid = QtGui.QGridLayout()
        self.cwidget.setLayout(grid)

        grid.addWidget(self.loadScanBtn, 0, 0)
        grid.addWidget(self.saveScanBtn, 0, 1)
        grid.addWidget(self.scanRadio, 0, 2)
        grid.addWidget(self.contLaserPulsesRadio, 0, 3)
        grid.addWidget(self.scanButton, 0, 4, 1, 2)
        grid.addWidget(self.continuousCheck, 0, 6)

        grid.addWidget(QtGui.QLabel('Size dim 0 (µm):'), 1, 0)
        grid.addWidget(self.size_dim0Par, 1, 1)
        grid.addWidget(QtGui.QLabel('Size dim 1 (µm):'), 2, 0)
        grid.addWidget(self.size_dim1Par, 2, 1)
        grid.addWidget(QtGui.QLabel('Size dim 2 (µm):'), 3, 0)
        grid.addWidget(self.size_dim2Par, 3, 1)
        grid.addWidget(QtGui.QLabel('Step size dim 0 (µm):'), 1, 2)
        grid.addWidget(self.stepSize_dim0Par, 1, 3)
        grid.addWidget(QtGui.QLabel('Step size dim 1 (µm):'), 2, 2)
        grid.addWidget(self.stepSize_dim1Par, 2, 3)
        grid.addWidget(QtGui.QLabel('Step size dim 2 (µm):'), 3, 2)
        grid.addWidget(self.stepSize_dim2Par, 3, 3)

        grid.addWidget(QtGui.QLabel('Mode:'), 1, 4)
        grid.addWidget(self.scanMode, 1, 5)
        grid.addWidget(QtGui.QLabel('Primary channel:'), 2, 4)
        grid.addWidget(self.primScanChan, 2, 5)
        grid.addWidget(QtGui.QLabel('Secondary chanel:'), 3, 4)
        grid.addWidget(self.secScanChan, 3, 5)
        grid.addWidget(QtGui.QLabel('Number of frames:'), 4, 4)
        grid.addWidget(self.nrFramesPar, 4, 5)
        grid.addWidget(self.previewButton, 1, 6, 3, 2)

        grid.addWidget(QtGui.QLabel('Dwell time (ms):'), 6, 0)
        grid.addWidget(self.seqTimePar, 6, 1)
        grid.addWidget(QtGui.QLabel('Total time (s):'), 6, 2)
        grid.addWidget(self.scanDurationLabel, 6, 3)
        grid.addWidget(QtGui.QLabel('Start (ms):'), 7, 1)
        grid.addWidget(QtGui.QLabel('End (ms):'), 7, 2)

        row = 8
        for i in range(0, len(self.allDevices)):
            grid.addWidget(QtGui.QLabel(self.allDevices[i]), row, 0)
            grid.addWidget(self.pxParameters['sta'+self.allDevices[i]], row, 1)
            grid.addWidget(self.pxParameters['end'+self.allDevices[i]], row, 2)
            row += 1

        grid.addWidget(self.graph, row, 0, 1, 9)
#        grid.addWidget(self.multiScanWgt, 14, 0, 4, 9)

        grid.setRowMinimumHeight(row, 200)

        #Set initial values
        self.primScanChan.setCurrentIndex(0)
        self.setPrimScanChan()


    @property
    def scanOrNot(self):
        return self._scanOrNot

    @scanOrNot.setter
    def scanOrNot(self, value):
        self.enableScanPars(value)
        self.scanButton.setCheckable(not value)

    def getParameters(self):

        scan_pars = self.scanParValues
        scan_mode = {'Mode': self.scanMode.currentText(),
                     'Primary chan': self.primScanChan.currentText(),
                     'Secondary chan': self.secScanChan.currentText()}

        pixel_cycle = self.pxParValues

        return {'Scan parameters': scan_pars,
                'Scan mode': scan_mode,
                'Laser cycle': pixel_cycle}

    def enableScanPars(self, value):
        self.size_dim0Par.setEnabled(value)
        self.size_dim1Par.setEnabled(value)
        self.stepSize_dim0Par.setEnabled(value)
        self.stepSize_dim1Par.setEnabled(value)
        self.scanMode.setEnabled(value)
        self.primScanChan.setEnabled(value)
        if value:
            self.scanButton.setText('Scan')
        else:
            self.scanButton.setText('Run')

    def setScanOrNot(self, value):
        self.scanOrNot = value

    def setScanMode(self, mode):
        self.stageScan.setScanMode(mode)
        self.scanParameterChanged('scanMode')

    def setPrimScanChan(self):
        currentText = self.primScanChan.currentText()
        self.stageScan.primScanDim = 'chan'+currentText
        if currentText == self.AOchans[0]:
            self.secScanChan.clear()
            new_possible_sec_dims = [self.AOchans[1], self.AOchans[2]]
            self.secScanChan.addItems(new_possible_sec_dims)
            self.secScanChan.setCurrentIndex(0)
        elif currentText == self.AOchans[1]:
            self.secScanChan.clear()
            new_possible_sec_dims = [self.AOchans[0], self.AOchans[2]]
            self.secScanChan.addItems(new_possible_sec_dims)
            self.secScanChan.setCurrentIndex(0)
        elif currentText == self.AOchans[2]:
            self.secScanChan.clear()
            new_possible_sec_dims = [self.AOchans[0], self.AOchans[1]]
            self.secScanChan.addItems(new_possible_sec_dims)
            self.secScanChan.setCurrentIndex(0)

        self.scanParameterChanged('primScanChan')

    def setSecScanChan(self):
        currentPrimText = self.primScanChan.currentText()
        currentSecText = self.secScanChan.currentText()
        self.stageScan.secScanDim= 'chan'+currentSecText
        if currentPrimText == self.AOchans[0]:
            if currentSecText == self.AOchans[1]:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[2]
            else:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[1]
        elif currentPrimText == self.AOchans[1]:
            if currentSecText == self.AOchans[0]:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[2]
            else:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[0]
        elif currentPrimText == self.AOchans[2]:
            if currentSecText == self.AOchans[0]:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[1]
            else:
                self.stageScan.thiScanDim = 'chan'+self.AOchans[0]

        self.scanParameterChanged('secScanChan')

    def scanParameterChanged(self, p):
        if p not in ('scanMode', 'primScanChan', 'secScanChan'):
            if p == 'seqTime':
                # To get in seconds
                self.scanParValues[p] = 0.001*float(self.scanPar[p].text())
            else:
                self.scanParValues[p] = float(self.scanPar[p].text())

        if p == 'seqTime':
            self.updateScan(self.allDevices)
            self.graph.update(self.allDevices)

        self.stageScan.updateFrames(self.scanParValues)
        self.nrFramesPar.setText(str(self.stageScan.frames))

        dim1 = self.stageScan.scans[self.stageScan.scanMode].steps_dim1
        dim2 = self.stageScan.scans[self.stageScan.scanMode].steps_dim2
        return_ramp_samps = self.stageScan.return_ramp_samps
        self.scanDuration = self.stageScan.frames*self.scanParValues['seqTime'] + dim1*dim2*return_ramp_samps/self.sampleRate
        self.scanDurationLabel.setText(str(np.round(self.scanDuration, 2)))

    def pxParameterChanged(self, dev = None):
        if dev is None: dev = self.allDevices
        for i in range(len(dev)):
            self.pxParValues['sta'+dev[i]] = 0.001*float(self.pxParameters['sta'+dev[i]].text())
            self.pxParValues['end'+dev[i]] = 0.001*float(self.pxParameters['end'+dev[i]].text())
            print('In pxParameterChanged for device :', dev[i])

        self.pxCycle.update(dev, self.pxParValues, self.stageScan.seqSamps)
        self.graph.update(dev)

    def previewScan(self):
        self.updateScan(self.allDevices)
        fig = plt.figure()
        ax0 = fig.add_subplot(311)
        ax0.plot(self.stageScan.sigDict['chan0'] * convFactors['chan0'])
        ax0.plot(self.stageScan.sigDict['chan1'] * convFactors['chan1'])
        ax0.plot(self.stageScan.sigDict['chan2'] * convFactors['chan2'])
        #ax0.plot(self.pxCycle.sigDict['Camera'])
        ax0.grid()
        ax0.set_xlabel('sample')
        ax0.set_ylabel('position [um]')

        devs = list(self.pxCycle.sigDict.keys())

        fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in range(0,len(devs))])

        primSteps = self.stageScan.scans[self.stageScan.scanMode].steps_dim0

        print('primSteps from Scanner.init = ', primSteps)
        # Signal for a single line
        lineSig = np.tile(fullDOsig, primSteps)
        emptySig = np.zeros((len(devs), int(self.stageScan.return_ramp_samps)), dtype=bool)
        fullDOsig = np.concatenate((lineSig, emptySig), axis=1)

        ax1 = fig.add_subplot(312)
        ax1.plot(np.transpose(fullDOsig))
        #ax1.plot(self.pxCycle.sigDict['Camera'])
        ax1.grid()
#        ax1.set_xlabel('sample')
#        ax1.set_ylabel('position [um]')

        ax2 = fig.add_subplot(313)
        ax2.plot(self.stageScan.sigDict['chan0'] * convFactors['chan0'],
                 self.stageScan.sigDict['chan1'] * convFactors['chan1'])
        mx = max(self.scanParValues['size_dim0'], self.scanParValues['size_dim1'])
        ax2.margins(0.1*mx)
        ax2.axis('scaled')
        ax2.set_xlabel("x axis [µm]")
        ax2.set_ylabel("y axis [µm]")

        plt.show()

    def scanOrAbort(self):
        if not self.scanning:
            self.prepAndRun()
        else:
            self.scanner.abort()

    def prepAndRun(self, continuous=False):
        ''' Only called if scanner is not running (See scanOrAbort function).
        '''
        if self.scanRadio.isChecked():
            self.stageScan.update(self.scanParValues)
            self.scanButton.setText('Abort')
#            if not(continuous):
#                self.main.piezoWidget.deactivate()
            self.scanner = Scanner(
               self.nidaq, self.stageScan, self.pxCycle, self.devicechannels, self, continuous)
            self.scanner.finalizeDone.connect(self.finalizeDone)
            self.scanner.scanDone.connect(self.scanDone)
            self.scanning = True
#            if self.focusLocked:
#                self.focusWgt.unlockFocus()

#            self.main.lvworkers[0].startRecording()

            self.scanner.runScan()

        elif self.scanButton.isChecked():
            self.lasercycle = LaserCycle(self.nidaq, self.pxCycle)
            self.scanButton.setText('Stop')
            self.lasercycle.run(self.devicechannels)

        else:
            self.lasercycle.stop()
            self.scanButton.setText('Run')
            del self.lasercycle

    def scanDone(self):
        self.scanButton.setEnabled(False)


    def finalizeDone(self):
        if (not self.continuousCheck.isChecked()) or self.scanner.aborted:
            self.scanButton.setText('Scan')
            self.scanButton.setEnabled(True)
            del self.scanner
            self.scanning = False
#            if self.focusLocked:
#                self.focusWgt.lockFocus()
#            self.main.piezoWidget.activate()
        elif self.continuousCheck.isChecked():
            self.scanButton.setEnabled(True)
            self.prepAndRun(True)
        else:
            self.scanButton.setEnabled(True)
            self.prepAndRun()

    def updateScan(self, devices):
        self.stageScan.update(self.scanParValues)
        self.pxCycle.update(devices, self.pxParValues, self.stageScan.seqSamps)

    def closeEvent(self, *args, **kwargs):
        try:
            self.scanner.waiter.terminate()
        except BaseException:
            pass


class WaitThread(QtCore.QThread):
    waitdoneSignal = QtCore.pyqtSignal()

    def __init__(self, task):
        super().__init__()
        self.task = task
        self.wait = True

    def run(self):
        if self.wait:
            self.task.wait_until_done(nidaqmx.constants.WAIT_INFINITELY)
        self.wait = True
        self.waitdoneSignal.emit()

    def stop(self):
        self.wait = False


class Scanner(QtCore.QObject):
    """This class plays the role of interface between the software and the
    hardware. It writes the different signals to the electronic cards and
    manages the timing of a scan.

    :param nidaqmx.Device device: NiDaq card
    :param StageScan stageScan: object containing the analog signals to drive
    the stage
    :param PixelCycle pxCycle: object containing the digital signals to
    drive the lasers at each pixel acquisition
    :param ScanWidget main: main scan GUI."""

    scanDone = QtCore.pyqtSignal()
    finalizeDone = QtCore.pyqtSignal()

    def __init__(self, device, stageScan, pxCycle, DOchans, main, continuous=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.nidaq = device
        self.stageScan = stageScan
        self.pxCycle = pxCycle
        self.continuous = continuous

        self.sampsInScan = len(self.stageScan.sigDict['chan0'])
        self.main = main

        self.aotask = nidaqmx.Task('aotask')
        self.dotask = nidaqmx.Task('dotask')
        self.waiter = WaitThread(self.aotask)

        self.scanTimeW = QtGui.QMessageBox()
        self.scanTimeW.setInformativeText("Are you sure you want to continue?")
        self.scanTimeW.setStandardButtons(QtGui.QMessageBox.Yes |
                                          QtGui.QMessageBox.No)
        self.channelOrder = main.channelOrder

        self.aborted = False

#        self.focusWgt = self.main.focusWgt

        AOchans = [0, 1, 2]
        # Following loop creates the voltage channels
        for n in range(len(AOchans)):
            self.aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % AOchans[n],
                name_to_assign_to_channel='chan_%s' % self.channelOrder[n],
                min_val=minVolt[self.channelOrder[n]],
                max_val=maxVolt[self.channelOrder[n]])

        print('Shape of sigDigt(0) = ', np.shape(self.stageScan.sigDict[self.channelOrder[0]]))
        self.fullAOsig = np.asarray([self.stageScan.sigDict[self.channelOrder[i]]
             for i in range(len(AOchans))])
        print('Full AO signal shape printed from Scanner init', np.shape(self.fullAOsig))
#        print('Full AO signal printed from Scanner init', self.fullAOsig)
        # Same as above but for the digital signals/devices
        devs = list(self.pxCycle.sigDict.keys())
        for d in DOchans:
            chanstring = 'Dev1/port0/line%s' % d
            self.dotask.do_channels.add_do_chan(
                lines=chanstring, name_to_assign_to_lines='chan%s' % devs[d])

        fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in range(0,len(devs))])

        """When doing unidirectional scan, the time needed for the stage to
        move back to the initial x needs to be filled with zeros/False.
        This time is now set to the time spanned by 1 sequence.
        Therefore, the digital signal is assambled as the repetition of the
        sequence for the whole scan in one row and then append zeros for 1
        sequence time. THIS IS NOW INCOMPATIBLE WITH VOLUMETRIC SCAN, maybe."""

        primSteps = self.stageScan.scans[self.stageScan.scanMode].steps_dim0

        print('primSteps from Scanner.init = ', primSteps)
        # Signal for a single line
        lineSig = np.tile(fullDOsig, primSteps)
        emptySig = np.zeros((len(devs), int(self.stageScan.return_ramp_samps)), dtype=bool)
        self.fullDOsig = np.concatenate((lineSig, emptySig), axis=1)


    def runScan(self):
        self.aborted = False

        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.stageScan.sampleRate,
            source=r'100kHzTimeBase',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)
        self.dotask.timing.cfg_samp_clk_timing(
            rate=self.pxCycle.sampleRate,
            source=r'ao/SampleClock',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)
        self.aotask.write(self.fullAOsig, auto_start=False)
        self.dotask.write(self.fullDOsig, auto_start=False)

        try:
            self.waiter.waitdoneSignal.disconnect(self.done)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.finalize)
        self.dotask.start()
        self.aotask.start()
        self.waiter.start()

    def abort(self):
        self.aborted = True
        self.waiter.stop()
        self.aotask.stop()
        self.dotask.stop()
        self.finalize()

    def finalize(self):
        self.scanDone.emit()
        # Apparently important, otherwise finalize is called again when next
        # waiting finishes.
        try:
            self.waiter.waitdoneSignal.disconnect(self.finalize)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.done)

        """This part used to contain signal for returning the stage to zero"""

        self.waiter.start()

    def done(self):
        self.aotask.stop()
        self.aotask.close()
        self.dotask.stop()
        self.dotask.close()
        self.nidaq.reset_device()
        self.finalizeDone.emit()


#class MultipleScanWidget(QtGui.QFrame):
#
#    def __init__(self, main):
#        super().__init__()
#
#        self.main = main
#
#        illumPlotsDockArea = DockArea()
#
#        # make illumination image widget
#        self.illumWgt = IllumImageWidget()
#        fovDock = Dock("2D scanning")
#        fovDock.addWidget(self.illumWgt)
#
#        self.illumWgt3D = pg.ImageView()
#        pos, rgba = zip(*guitools.cmapToColormap(plt.get_cmap('inferno')))
#        self.illumWgt3D.setColorMap(pg.ColorMap(pos, rgba))
#        for tick in self.illumWgt3D.ui.histogram.gradient.ticks:
#            tick.hide()
#        volDock = Dock("3D scanning")
#        volDock.addWidget(self.illumWgt3D)
#
#        illumPlotsDockArea.addDock(volDock)
#        illumPlotsDockArea.addDock(fovDock, 'above', volDock)
#
#        self.makeImgBox = QtGui.QCheckBox('Build scan image')
#
#        # Crosshair
#        self.crosshair = guitools.Crosshair(self.illumWgt.vb)
#        self.crossButton = QtGui.QPushButton('Crosshair')
#        self.crossButton.setCheckable(True)
#        self.crossButton.pressed.connect(self.crosshair.toggle)
#
#        # make worker
#        self.worker = MultiScanWorker(self, self.main)
#
#        # make other GUI components
#        self.analysis_btn = QtGui.QPushButton('Analyze')
#        self.analysis_btn.clicked.connect(self.worker.analyze)
#        self.analysis_btn.setSizePolicy(QtGui.QSizePolicy.Preferred,
#                                        QtGui.QSizePolicy.Expanding)
#        self.show_beads_btn = QtGui.QPushButton('Show beads')
#        self.show_beads_btn.clicked.connect(self.worker.find_fp)
#        self.quality_label = QtGui.QLabel('Quality level of points')
#        self.quality_edit = QtGui.QLineEdit('0.05')
#        self.quality_edit.editingFinished.connect(self.worker.find_fp)
#        self.win_size_label = QtGui.QLabel('Window size [px]')
#        self.win_size_edit = QtGui.QLineEdit('10')
#        self.win_size_edit.editingFinished.connect(self.worker.find_fp)
#
#        self.beads_label = QtGui.QLabel('Bead number')
#        self.beadsBox = QtGui.QComboBox()
#        self.beadsBox.activated.connect(self.change_illum_image)
#        self.change_beads_button = QtGui.QPushButton('Change')
#        self.change_beads_button.clicked.connect(self.nextBead)
#        self.overlayBox = QtGui.QComboBox()
#        self.overlayBox.activated.connect(self.worker.overlay)
#        self.overlay_check = QtGui.QCheckBox('Overlay')
#        self.overlay_check.stateChanged.connect(self.worker.overlay)
#        self.clear_btn = QtGui.QPushButton('Clear')
#        self.clear_btn.clicked.connect(self.clear)
#
#        grid = QtGui.QGridLayout()
#        self.setLayout(grid)
#
#        grid.addWidget(self.crossButton, 0, 0)
#        grid.addWidget(self.makeImgBox, 0, 1)
#        grid.addWidget(illumPlotsDockArea, 1, 0, 1, 8)
#
#        grid.addWidget(self.quality_label, 2, 0)
#        grid.addWidget(self.quality_edit, 2, 1)
#        grid.addWidget(self.win_size_label, 3, 0)
#        grid.addWidget(self.win_size_edit, 3, 1)
#        grid.addWidget(self.show_beads_btn, 2, 2)
#        grid.addWidget(self.analysis_btn, 3, 2)
#
#        grid.addWidget(self.beads_label, 2, 4)
#        grid.addWidget(self.beadsBox, 2, 5)
#        grid.addWidget(self.change_beads_button, 3, 4, 1, 2)
#        grid.addWidget(self.overlay_check, 2, 6)
#        grid.addWidget(self.overlayBox, 2, 7)
#        grid.addWidget(self.clear_btn, 3, 6, 1, 2)
#
#        grid.setColumnMinimumWidth(3, 100)
#
#    def change_illum_image(self):
#        self.worker.delete_label()
#        curr_ind = self.beadsBox.currentIndex()
#        self.illumWgt.update(self.worker.illumImgs[curr_ind])
#        self.illumWgt.vb.autoRange()
#        if self.overlay_check.isChecked():
#            self.illumWgt.updateBack(self.worker.illumImgs_back[curr_ind])
#        if curr_ind == len(self.worker.illumImgs) - 1:
#            self.worker.showLargeViewLabel()
#
#    def nextBead(self):
#        self.worker.delete_label()
#        curr_ind = self.beadsBox.currentIndex()
#        if len(self.worker.illumImgs) == curr_ind + 1:
#            next_ind = 0
#        else:
#            next_ind = curr_ind + 1
#        self.illumWgt.update(self.worker.illumImgs[next_ind])
#        self.beadsBox.setCurrentIndex(next_ind)
#        if self.overlay_check.isChecked():
#            self.illumWgt.updateBack(self.worker.illumImgs_back[next_ind])
#        if next_ind == len(self.worker.illumImgs) - 1:
#            self.worker.showLargeViewLabel()
#        self.illumWgt.vb.autoRange()
#
#    def clear(self):
#        self.worker.illumImgsStocked = []
#        self.overlayBox.clear()


#class MultiScanWorker(QtCore.QObject):
#
#    def __init__(self, main_wgt, mainScanWid):
#        super().__init__()
#
#        self.main = main_wgt
#        self.mainScanWid = mainScanWid
#        self.illumImgs = []
#        self.illumImgsStocked = []
#        self.labels = []
#
#        # corner detection parameter of Shi-Tomasi
#        self.featureParams = dict(maxCorners=100, qualityLevel=0.1,
#                                  minDistance=7, blockSize=7)
#
#    def set_images(self, images):
#        stageScan = self.mainScanWid.scanner.stageScan
#        self.primScanDim = stageScan.primScanDim
#        if self.primScanDim == 'x':
#            self.steps = [stageScan.scans[stageScan.scanMode].stepsY,
#                          stageScan.scans[stageScan.scanMode].stepsX]
#        else:
#            self.steps = [stageScan.scans[stageScan.scanMode].stepsX,
#                          stageScan.scans[stageScan.scanMode].stepsY]
#        self.images = images
#
#    def find_fp(self):
#        self.main.illumWgt.delete_back()
#
#        # find feature points
#        ql = float(self.main.quality_edit.text())
#        self.featureParams['qualityLevel'] = ql
#        self.radius = int(self.main.win_size_edit.text())
#        self.nor_const = 255 / (np.max(self.images))
#
#        self.fFrame = (self.images[1] * self.nor_const).astype(np.uint8)
#        self.lFrame = (self.images[-1] * self.nor_const).astype(np.uint8)
#        fps_f = goodFeaturesToTrack(
#            self.fFrame, mask=None, **self.featureParams)
#        fps_f = np.array([point[0] for point in fps_f])
#        self.fps_f = fps_f[fps_f[:, 0].argsort()]
#        fps_l = goodFeaturesToTrack(
#            self.lFrame, mask=None, **self.featureParams)
#        self.fps_l = np.array([point[0] for point in fps_l])
#
#        # make frame for visualizing feature point detection
#        self.frameView = (self.fFrame + self.lFrame) / 2
#
#        # draw feature points image
#        self.delete_label()
#        self.centers = []   # center points between first FPs and last FPs
#        self.fps_ll = []    # FPs of last frame that match ones of fist frame
#        for i, fp_f in enumerate(self.fps_f):
#            distances = [np.linalg.norm(fp_l - fp_f) for fp_l in self.fps_l]
#            ind = np.argmin(distances)
#            self.fps_ll.append(self.fps_l[ind])
#            center = (fp_f + self.fps_l[ind]) / 2
#            self.centers.append(center)
#            # draw calculating window
#            rectangle(self.frameView,
#                      (int(center[0]-self.radius), int(center[1]-self.radius)),
#                      (int(center[0]+self.radius), int(center[1]+self.radius)),
#                      255, 1)
#            # make labels for each window
#            label = pg.TextItem()
#            label.setPos(center[0] + self.radius, center[1] + self.radius)
#            label.setText(str(i))
#            self.labels.append(label)
#            self.main.illumWgt.vb.addItem(label)
#        self.main.illumWgt.update(self.frameView.T, invert=False)
#        self.main.illumWgt.vb.autoRange()
#
#    def analyze(self):
#        self.main.beadsBox.clear()
#        self.illumImgs = []
#
#        self.delete_label()
#
#        data_mean = []      # means of calculating window for each images
#        cps_f = []          # center points of beads in first frame
#        cps_l = []          # center points of beads in last frame
#        for i in range(len(self.centers)):
#            data_mean.append([])
#            # record the center point of gravity
#            cps_f.append(self.find_cp(
#                self.fFrame, self.fps_f[i].astype(np.uint16), self.radius))
#            cps_l.append(self.find_cp(
#                self.lFrame, self.fps_ll[i].astype(np.uint16), self.radius))
#
#            # calculate the mean of calculating window
#            for image in self.images:
#                mean = self.meanROI(
#                    image, self.centers[i].astype(np.uint16), self.radius)
#                data_mean[i].append(mean)
#
#        # reconstruct the illumination image
#        for i in range(len(data_mean)):
#            data_r = np.reshape(data_mean[i], self.steps)
#            if self.primScanDim == 'x':
#                data_r = data_r.T
#            self.illumImgs.append(data_r)
#            self.main.beadsBox.addItem(str(i))
#
#        # stock images for overlaying
#        self.illumImgsStocked.append(self.illumImgs)
#        self.main.overlayBox.addItem(str(self.main.overlayBox.count()))
#
#        # make large field of view of illumination image
#        # expand beads image
#        dif = []
#        for i in range(len(cps_f)):
#            dif_x = np.abs(cps_f[i][0] - cps_l[i][0])
#            dif_y = np.abs(cps_f[i][1] - cps_l[i][1])
#            dif.append(max(dif_x, dif_y))
#        rate = max(self.steps) / np.average(dif)
#        imgLarge = np.zeros((int(self.fFrame.shape[0]*rate),
#                             int(self.fFrame.shape[1]*rate))).T
#
#        self.points_large = []  # start and end points of illumination image
#        for point, illum_image in zip(self.fps_f, self.illumImgs):
#            px = imgLarge.shape[1] - (point[1] * rate).astype(int)
#            py = imgLarge.shape[0] - (point[0] * rate).astype(int)
#            if self.primScanDim == 'x':
#                pxe = min(px+self.steps[0], imgLarge.shape[1])
#                pye = min(py+self.steps[1], imgLarge.shape[0])
#            else:
#                pxe = min(px+self.steps[1], imgLarge.shape[1])
#                pye = min(py+self.steps[0], imgLarge.shape[0])
#            imgLarge[py:pye, px:pxe] = illum_image[0:pye-py, 0:pxe-px]
#            self.points_large.append([px, py, pxe, pye])
#        self.illumImgs.append(imgLarge)
#
#        # update illumination image
#        self.main.illumWgt.update(imgLarge)
#        self.showLargeViewLabel()
#        self.main.beadsBox.addItem('Large FOV')
#        self.main.beadsBox.setCurrentIndex(len(self.illumImgs) - 1)
#        self.main.illumWgt.vb.autoRange()
#
#        # do not display large view if bead is only one
#        if len(self.illumImgs) == 2:
#            self.main.nextBead()
#
#    def overlay(self):
#        ind = self.main.overlayBox.currentIndex()
#        self.illumImgs_back = []     # illumination images for overlay
#
#        # overlay previous image to current image
#        if self.main.overlay_check.isChecked():
#
#            # process the large field of view
#            illumImgLargePre = np.zeros(self.illumImgs[-1].shape)
#            for i, point in enumerate(self.points_large):
#                px, py, pxe, pye = point
#                illumImgPre = self.illumImgsStocked[ind][i]
#                illumImgLargePre[py:pye, px:pxe] = illumImgPre[:pye-py,
#                                                               :pxe-px]
#
#            # process each image
#            for i in range(len(self.illumImgs) - 1):
#                illumImgPre = self.illumImgsStocked[ind][i]
#                self.illumImgs_back.append(illumImgPre)
#
#            self.illumImgs_back.append(illumImgLargePre)
#
#            # update the background image
#            img = self.illumImgs_back[self.main.beadsBox.currentIndex()]
#            self.main.illumWgt.updateBack(img)
#
#        else:
#            self.illumImgs_back.clear()
#            self.main.illumWgt.delete_back()
#
#    def delete_label(self):
#        # delete beads label
#        if len(self.labels) != 0:
#            for label in self.labels:
#                self.main.illumWgt.vb.removeItem(label)
#            self.labels.clear()
#
#    def showLargeViewLabel(self):
#        for i, point in enumerate(self.points_large):
#            px, py, pxe, pye = point
#            label = pg.TextItem()
#            label.setPos(py, px)
#            label.setText(str(i))
#            self.labels.append(label)
#            self.main.illumWgt.vb.addItem(label)
#
#    @staticmethod
#    def meanROI(array, p, r):
#        xs = max(p[0] - r, 0)
#        xe = min(p[0] + r, array.shape[1])
#        ys = max(p[1] - r, 0)
#        ye = min(p[1] + r, array.shape[0])
#        roi = array[ys: ye, xs: xe]
#        return np.average(roi)
#
#    @staticmethod
#    def find_cp(array, point, r):
#        xs = max(point[0] - r, 0)
#        xe = min(point[0] + r, array.shape[1])
#        ys = max(point[1] - r, 0)
#        ye = min(point[1] + r, array.shape[0])
#        roi = array[ys: ye, xs: xe]
#        M = moments(roi, False)
#        cx = int(M['m10'] / M['m00'])
#        cy = int(M['m01'] / M['m00'])
#        return [int(cx + point[0] - r), int(cy + point[1] - r)]


class IllumImageWidget(pg.GraphicsLayoutWidget):

    def __init__(self):
        super().__init__()

        self.vb = self.addViewBox(row=1, col=1)
        self.vb.setAspectLocked(True)
        self.vb.enableAutoRange()

        self.img = pg.ImageItem()
        self.vb.addItem(self.img)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.vb.setLimits(yMin=0, yMax=66000)
        redsColormap = pg.ColorMap([0, 1], [(0, 0, 0), (255, 0, 0)])
        self.hist.gradient.setColorMap(redsColormap)
        for tick in self.hist.gradient.ticks:
            tick.hide()
        self.addItem(self.hist, row=1, col=2)

        self.imgBack = pg.ImageItem()
        self.vb.addItem(self.imgBack)
        self.imgBack.setZValue(10)
        self.imgBack.setOpacity(0.5)
        self.histBack = pg.HistogramLUTItem(image=self.imgBack)
        self.histBack.vb.setLimits(yMin=0, yMax=66000)
        pos, rgba = zip(*guitools.cmapToColormap(plt.get_cmap('viridis')))
        greensColormap = pg.ColorMap(pos, rgba)
        self.histBack.gradient.setColorMap(greensColormap)
        for tick in self.histBack.gradient.ticks:
            tick.hide()
        self.addItem(self.histBack, row=1, col=3)

        self.first = True
        self.firstBack = True

    def update(self, img, invert=True):
        self.img.setImage(img, autoLevels=self.first)
        if invert:
            self.vb.invertX(True)
            self.vb.invertY(True)
        else:
            self.vb.invertX(False)
            self.vb.invertY(False)
        if self.first:
            self.hist.setLevels(*guitools.bestLimits(img))
        self.first = False

    def updateBack(self, img):
        self.imgBack.setImage(img, autoLevels=self.firstBack)
        if self.first:
            self.histBack.setLevels(*guitools.bestLimits(img))
        self.firstBack = False

    def delete_back(self):
        self.imgBack.clear()
        self.firstBack = True


class LaserCycle():

    def __init__(self, device, pxCycle):
        self.nidaq = device
        self.pxCycle = pxCycle

    def run(self, DOchans):
        self.dotask = nidaqmx.Task('dotaskLaser')

        devs = list(self.pxCycle.sigDict.keys())
        assert len(devs) == len(DOchans), '# digital channels is not the same as # devices'
        it = range(0, len(devs))
        for i in it:
            print('Adding line', DOchans[i])
            chanstring = 'Dev1/port0/line%s' % DOchans[i]
            self.dotask.do_channels.add_do_chan(
                lines=chanstring, name_to_assign_to_lines='chan%s' % devs[i])

        print('Finished adding lines')

        fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in range(0, len(DOchans))])

        self.dotask.timing.cfg_samp_clk_timing(
           source=r'100kHzTimeBase',
           rate=self.pxCycle.sampleRate,
           sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)

        self.dotask.write(fullDOsig, auto_start=False)

        self.dotask.start()

    def stop(self):
        self.dotask.stop()
        self.dotask.close()
        del self.dotask
        self.nidaq.reset_device()


class StageScan():
    '''Contains the analog signals in sig_dict. The update function takes the
    parameter_values and updates the signals accordingly.'''
    def __init__(self, sampleRate):
        self.scanMode = '2D scan'
        self.primScanDim = 'chan0'
        self.secScanDim = 'chan1'
        self.thiScanDim = 'chan2'
        self.sigDict = {'chan0': [], 'chan1': [], 'chan2': []}
        self.sampleRate = sampleRate
        self.seqSamps = None
        self.twoDimScan = TwoDimScan(self.sampleRate)
        self.threeDimScan = ThreeDimScan(self.sampleRate)
        self.oneDimScan = OneDimScan(self.sampleRate)
        self.scans = {'1D scan': self.oneDimScan,
                      '2D scan': self.twoDimScan,
                      '3D scan': self.threeDimScan}
        self.frames = 0
        self.return_ramp_samps = 3000

    def getScanPars(self):
        parDict = {}
        dim0 = self.scans[self.scanMode].steps_dim0
        dim1 = self.scans[self.scanMode].steps_dim1
        dim2 = self.scans[self.scanMode].steps_dim2

        """Parameter values are saved in order from fastest changing dimension to slowest changing"""
        parDict['dims'] = (dim0, dim1, dim2)

        stepSize_dim0 = self.scans[self.scanMode].corrStepSize_dim0
        stepSize_dim1 = self.scans[self.scanMode].corrStepSize_dim1
        stepSize_dim2 = self.scans[self.scanMode].corrStepSize_dim2


        parDict['step_sizes'] = (stepSize_dim0, stepSize_dim1, stepSize_dim2)

        return parDict

    def setScanMode(self, mode):
        self.scanMode = mode

    def updateFrames(self, parValues):
        self.scans[self.scanMode].updateFrames(parValues)
        self.frames = self.scans[self.scanMode].frames

    def update(self, parValues):
        self.scans[self.scanMode].update(parValues, self.primScanDim, self.secScanDim, self.thiScanDim, self.return_ramp_samps)
        self.sigDict = self.scans[self.scanMode].sigDict
        self.seqSamps = self.scans[self.scanMode].seqSamps
        self.frames = self.scans[self.scanMode].frames


class OneDimScan():

    def __init__(self, sampleRate):
        self.sigDict = {'chan0': [], 'chan1': [], 'chan2': []}
        self.sampleRate = sampleRate
        self.corrStepSize_dim0 = None
        self.corrStepSize_dim1 = None
        self.corrStepSize_dim2 = None
        self.seqSamps = None
        self.frames = 0
        self.steps_dim0 = None
        self.steps_dim1 = None
        self.steps_dim2 = None

    def updateFrames(self, parValues):
        size_dim0 = parValues['size_dim0']
        stepSize_dim0 = parValues['stepSize_dim0']
        steps_dim0 = int(np.ceil(size_dim0 / stepSize_dim0))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = steps_dim0

    def update(self, parValues, primScanDim, secScanDim, thiScanDim, return_ramp_samps):
        '''Create signals.
        First, distances are converted to voltages.'''
        self.start_dim0 = 0
        self.size_dim0 = parValues['size_dim0']
        self.seqSamps = int(np.round(self.sampleRate * parValues['seqTime']))
        self.stepSize_dim0 = parValues['stepSize_dim0']
        self.steps_dim0 = int(np.ceil(self.size_dim0 / self.stepSize_dim0))
        self.steps_dim1 = 1
        self.steps_dim2 = 1
        # Step size compatible with width
        self.corrStepSize_dim0 = self.size_dim0 / self.steps_dim0
        self.corrStepSize_dim1 = 1
        self.corrStepSize_dim2 = 1

        if primScanDim == 'chan0':
            self.makePrimDimSig('chan0')
            self.sigDict['chan1'] = np.zeros(len(self.sigDict['chan0']))
            self.sigDict['chan2'] = np.zeros(len(self.sigDict['chan0']))
        elif primScanDim == 'chan1':
            self.makePrimDimSig('chan1')
            self.sigDict['chan0'] = np.zeros(len(self.sigDict['chan0']))
            self.sigDict['chan2'] = np.zeros(len(self.sigDict['chan0']))
        elif primScanDim == 'chan2':
            self.makePrimDimSig('chan2')
            self.sigDict['chan0'] = np.zeros(len(self.sigDict['chan0']))
            self.sigDict['chan1'] = np.zeros(len(self.sigDict['chan0']))


    def makePrimDimSig(self, chan):
        rowSamps = self.steps_dim0 * self.seqSamps
        ramp = makeRamp(self.start_dim0, self.size_dim0, rowSamps)

        self.sigDict[chan] = ramp / convFactors[chan]

class TwoDimScan():

    def __init__(self, sampleRate):
        self.sigDict = {'chan0': [], 'chan1': [], 'chan2': []}
        self.sampleRate = sampleRate
        self.corrStepSize_dim0 = None
        self.corrStepSize_dim1 = None
        self.corrStepSize_dim2 = None
        self.seqSamps = None
        self.frames = 0
        self.steps_dim0 = None
        self.steps_dim1 = None
        self.steps_dim2 = None

    def updateFrames(self, parValues):
        '''Update signals according to parameters.
        Note that rounding floats to ints may cause actual scan to differ
        slightly from expected scan. Maybe either limit input parameters to
        numbers that "fit each other" or find other solution, eg step size has
        to be width divided by an integer. Maybe not a problem ???'''
        stepSize_dim0 = parValues['stepSize_dim0']
        stepSize_dim1 = parValues['stepSize_dim1']
        size_dim0 = parValues['size_dim0']
        size_dim1 = parValues['size_dim1']
        steps_dim0 = int(np.ceil(size_dim0 / stepSize_dim0))
        steps_dim1 = int(np.ceil(size_dim1 / stepSize_dim1))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = steps_dim0 * steps_dim1

    def update(self, parValues, primScanDim, secScanDim, thiScanDim, return_ramp_samps):
        '''Create signals.
        Signals are first created in units of distance and converted to voltage
        at the end.'''
        # Create signals
        self.start_dim0 = self.start_dim1 = 0
        self.size_dim0 = parValues['size_dim0']
        self.size_dim1 = parValues['size_dim1']
        self.stepSize_dim0 = parValues['stepSize_dim0']
        self.stepSize_dim1 = parValues['stepSize_dim1']
        self.seqSamps = int(np.round(self.sampleRate*parValues['seqTime']))
        self.steps_dim0 = int(np.ceil(self.size_dim0 / self.stepSize_dim0))
        self.steps_dim1 = int(np.ceil(self.size_dim1 / self.stepSize_dim1))
        self.steps_dim2 = 1
        # Step size compatible with width
        self.corrStepSize_dim0 = self.size_dim0 / self.steps_dim0
        self.corrStepSize_dim1 = self.size_dim1 / self.steps_dim1
        self.corrStepSize_dim2 = 1
        self.return_ramp_samps = return_ramp_samps

        if primScanDim == 'chan0':
            self.makePrimDimSig('chan0')
            if secScanDim == 'chan1':
                self.makeSecDimSig('chan1')
                self.sigDict['chan2'] = np.zeros(len(self.sigDict['chan0']))
            elif secScanDim == 'chan2':
                self.makeSecDimSig('chan2')
                self.sigDict['chan1'] = np.zeros(len(self.sigDict['chan0']))
        elif primScanDim == 'chan1':
            self.makePrimDimSig('chan1')
            if secScanDim == 'chan2':
                self.makeSecDimSig('chan2')
                self.sigDict['chan0'] = np.zeros(len(self.sigDict['chan1']))
            elif secScanDim == 'chan0':
                self.makeSecDimSig('chan0')
                self.sigDict['chan2'] = np.zeros(len(self.sigDict['chan1']))
        if primScanDim == 'chan2':
            self.makePrimDimSig('chan2')
            if secScanDim == 'chan1':
                self.makeSecDimSig('chan1')
                self.sigDict['chan0'] = np.zeros(len(self.sigDict['chan2']))
            elif secScanDim == 'chan0':
                self.makeSecDimSig('chan0')
                self.sigDict['chan1'] = np.zeros(len(self.sigDict['chan2']))

    def makePrimDimSig(self, chan):
        rowSamps = self.steps_dim0 * self.seqSamps
        LTRramp = makeRamp(self.start_dim0, self.start_dim0 + self.size_dim0, rowSamps)
        # Fast return to startX
        RTLramp = smoothRamp(self.start_dim0 + self.size_dim0, self.start_dim0, self.return_ramp_samps)
        LTRTLramp = np.concatenate((LTRramp, RTLramp))
        primSig = np.tile(LTRTLramp, self.steps_dim1)
        self.sigDict[chan] = primSig / convFactors[chan]

    def makeSecDimSig(self, chan):
        # y axis scan signal
        colSamps = self.steps_dim1 * self.return_ramp_samps
        Yramp = makeRamp(self.start_dim1, self.start_dim1 + self.size_dim1, colSamps)
        Yramps = np.split(Yramp, self.steps_dim1)
        constant = np.ones((self.steps_dim0)*self.seqSamps)
        Sig = np.array([np.concatenate((i[0]*constant, i)) for i in Yramps])
        secSig = Sig.ravel()
        self.sigDict[chan] = secSig / convFactors[chan]


class ThreeDimScan():

    def __init__(self, sampleRate):
        self.sigDict = {'chan0': [], 'chan1': [], 'chan2': []}
        self.sampleRate = sampleRate
        self.corrStepSize = None
        self.seqSamps = None
        self.frames = 0
        self.steps_dim0 = None
        self.steps_dim1 = None
        self.steps_dim2 = None

    def updateFrames(self, parValues):
        '''Update signals according to parameters.
        Note that rounding floats to ints may cause actual scan to differ
        slightly from expected scan. Maybe either limit input parameters to
        numbers that "fit each other" or find other solution, eg step size has
        to be width divided by an integer. Maybe not a problem ???'''
        stepSize_dim0 = parValues['stepSize_dim0']
        stepSize_dim1 = parValues['stepSize_dim1']
        stepSize_dim2 = parValues['stepSize_dim2']
        size_dim0 = parValues['size_dim0']
        size_dim1 = parValues['size_dim1']
        size_dim2 = parValues['size_dim2']
        steps_dim0 = int(np.ceil(size_dim0 / stepSize_dim0))
        steps_dim1 = int(np.ceil(size_dim1 / stepSize_dim1))
        steps_dim2 = int(np.ceil(size_dim2 / stepSize_dim2))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = steps_dim1 * steps_dim0 * steps_dim2

    def update(self, parValues, primScanDim, secScanDim, thiScanDim, return_ramp_samps):
        '''Create signals.
        Signals are first created in units of distance and converted to voltage
        at the end.'''
        print('Updating 3D signal, from update function')
        # Create signals
        self.start_dim0 = self.start_dim1 = self.start_dim2 = 0
        self.size_dim0 = parValues['size_dim0']
        self.size_dim1 = parValues['size_dim1']
        self.size_dim2 = parValues['size_dim2']
        self.stepSize_dim0 = parValues['stepSize_dim0']
        self.stepSize_dim1 = parValues['stepSize_dim1']
        self.stepSize_dim2 = parValues['stepSize_dim2']
        self.seqSamps = int(np.round(self.sampleRate*parValues['seqTime']))
        self.steps_dim0 = int(np.ceil(self.size_dim0 / self.stepSize_dim0))
        self.steps_dim1 = int(np.ceil(self.size_dim1 / self.stepSize_dim1))
        self.steps_dim2 = int(np.ceil(self.size_dim2 / self.stepSize_dim2))
        # Step size compatible with width
        self.corrStepSize_dim0 = self.size_dim0 / self.steps_dim0
        self.corrStepSize_dim1 = self.size_dim1 / self.steps_dim1
        self.corrStepSize_dim2 = self.size_dim2 / self.steps_dim2
        self.return_ramp_samps = return_ramp_samps



        if primScanDim == 'chan0':
            self.makePrimDimSig('chan0')
            if secScanDim == 'chan1':
                self.makeSecDimSig('chan1')
                self.makeThiDimSig('chan2')
            elif secScanDim == 'chan2':
                self.makeSecDimSig('chan2')
                self.makeThiDimSig('chan1')
        elif primScanDim == 'chan1':
            self.makePrimDimSig('chan1')
            if secScanDim == 'chan0':
                self.makeSecDimSig('chan0')
                self.makeThiDimSig('chan2')
            elif secScanDim == 'chan2':
                self.makeSecDimSig('chan2')
                self.makeThiDimSig('chan1')
        if primScanDim == 'chan2':
            self.makePrimDimSig('chan2')
            if secScanDim == 'chan1':
                self.makeSecDimSig('chan1')
                self.makeThiDimSig('chan0')
            elif secScanDim == 'chan0':
                self.makeSecDimSig('chan0')
                self.makeThiDimSig('chan1')

    def makePrimDimSig(self, chan):
        print('Making primary dimension signal')
        rowSamps = self.steps_dim0  * self.seqSamps
        LTRramp = makeRamp(self.start_dim0, self.start_dim0 + self.size_dim0, rowSamps)
        # Fast return to startX
        RTLramp = smoothRamp(self.start_dim0 + self.size_dim0, self.start_dim0, self.return_ramp_samps)
        LTRTLramp = np.concatenate((LTRramp, RTLramp))
        numSig = self.steps_dim1 * self.steps_dim2
        primSig = np.tile(LTRTLramp, numSig)
        self.sigDict[chan] = primSig / convFactors[chan]

    def makeSecDimSig(self, chan):
        print('Making second dimension signal')
        colSamps = self.steps_dim1 * self.return_ramp_samps
        ramp = makeRamp(self.start_dim1, self.start_dim1 + self.size_dim1, colSamps)
        ramps = np.split(ramp, self.steps_dim1)
        ramps[-1] = smoothRamp(ramps[-2][-1], self.start_dim1, self.return_ramp_samps)
#        ramps = ramps[0:len(ramps)-1]
#        wait = self.steps_dim0 + 1
#        constant = np.ones(wait * self.seqSamps)
        constant = np.ones((self.steps_dim0)*self.seqSamps)
        sig = np.array([np.concatenate((i[0]*constant, i)) for i in ramps])
        sig = sig.ravel()
#        returnRamp = makeRamp(sig[-1], self.start_dim1, self.seqSamps)
#        sig = np.concatenate((constant*0, sig, returnRamp))
        numSig = self.steps_dim2
        secSig = np.tile(sig, numSig)
        self.sigDict[chan] = secSig / convFactors[chan]

    def makeThiDimSig(self, chan):
        print('Making third dimension signal')
        colSamps = self.steps_dim2 * self.return_ramp_samps
        ramp = makeRamp(self.start_dim2, self.start_dim2 + self.size_dim2, colSamps)
        ramps = np.split(ramp, self.steps_dim2)
        ramps[-1] = smoothRamp(ramps[-2][-1], self.start_dim2, self.return_ramp_samps)
#        ramps = ramps[0:len(ramps)-1]
#        wait = (self.steps_dim0+2) * self.steps_dim1 - 1
#        constant = np.ones(wait*self.seqSamps)
        constant = np.ones((self.steps_dim0*self.seqSamps + self.return_ramp_samps)*self.steps_dim1 - self.return_ramp_samps)
        sig = np.array([np.concatenate((i[0]*constant, i)) for i in ramps])
        sig = sig.ravel()
#        returnRamp = makeRamp(sig[-1], self.start_dim2, self.seqSamps)
#        sig = np.concatenate((constant*0, sig, returnRamp))
#        thiSig = sig
        self.sigDict[chan] = sig / convFactors[chan]


class PixelCycle():
    ''' Contains the digital signals for the pixel cycle. The update function
    takes a parameter_values dict and updates the signal accordingly.'''
    def __init__(self, sampleRate, devices):
        self.sigDict = collections.OrderedDict()
        for dev in devices:
            self.sigDict[dev] = []

        self.sampleRate = sampleRate
        self.cycleSamps = None

    def update(self, devices, parValues, cycleSamps):
        self.cycleSamps = cycleSamps
        for device in devices:
            signal = np.zeros(cycleSamps, dtype='bool')
            start_name = 'sta' + device
            end_name = 'end' + device
            start_pos = parValues[start_name] * self.sampleRate
            start_pos = int(min(start_pos, cycleSamps - 1))
            end_pos = parValues[end_name] * self.sampleRate
            end_pos = int(min(end_pos, cycleSamps))
            signal[range(start_pos, end_pos)] = True
            self.sigDict[device] = signal


class GraphFrame(pg.GraphicsWindow):
    """Creates the plot that plots the preview of the pulses.
    Fcn update() updates the plot of "device" with signal "signal"."""
    def __init__(self, pxCycle, Device_info, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pxCycle = pxCycle
        devs = list(pxCycle.sigDict.keys())
        self.plot = self.addPlot(row=0, col=0)
        self.plot.setYRange(0, 1)
        self.plot.showGrid(x=False, y=False)
        self.plotSigDict = dict()
        for i in range(0, len(pxCycle.sigDict)):
            r = Device_info[i][2][0]
            g = Device_info[i][2][1]
            b = Device_info[i][2][2]
            self.plotSigDict[devs[i]] = self.plot.plot(pen=pg.mkPen(r,g,b))

#        self.plotSigDict = {'405': self.plot.plot(pen=pg.mkPen(130, 0, 200)),
#                            '488': self.plot.plot(pen=pg.mkPen(0, 247, 255)),
#                            '473': self.plot.plot(pen=pg.mkPen(0, 183, 255)),
#                            'CAM': self.plot.plot(pen='w')}

    def update(self, devices=None):
        if devices is None:
            devices = self.plotSigDict

        for device in devices:
            signal = self.pxCycle.sigDict[device]
            self.plotSigDict[device].setData(np.array(signal, dtype=np.int))


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


def smoothRamp(start, end, samples):
    curve_half = 0.6
    x = np.linspace(0, np.pi/2, num=np.floor(curve_half*samples), endpoint=True)
    signal = start + (end-start)*np.sin(x)
    signal = np.append(signal, end*np.ones(int(np.ceil((1-curve_half)*samples))))
    return signal
