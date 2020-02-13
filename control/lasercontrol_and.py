# -*- coding: utf-8 -*-
"""
Created on Tue Aug 12 11:51:21 2014

@author: Federico Barabas
"""

import time
from PyQt4 import QtGui, QtCore
from lantz import Q_
import nidaqmx
import numpy as np
from multiprocessing import Process

def mWtomV(x):

    # p are the coefficients from Ti:Sa calibration at 25/08/2016
    p = [0.0000000038094, -0.00000444662, 0.0019, -0.36947, 42.6684, 196]
    y = np.polyval(p,x)

    return y

class UpdatePowers(QtCore.QObject):

    def __init__(self, laserwidget, *args, **kwargs):

        super(QtCore.QObject, self).__init__(*args, **kwargs)
        self.widget = laserwidget

    def update(self):
#        bluepower = '{:~}'.format(self.widget.bluelaser.power)
#        violetpower = '{:~}'.format(self.widget.violetlaser.power)
#        uvpower = '{:~}'.format(self.widget.uvlaser.power)
#        self.widget.blueControl.powerIndicator.setText(bluepower)
#        self.widget.violetControl.powerIndicator.setText(violetpower)
#        self.widget.uvControl.powerIndicator.setText(uvpower)
#        time.sleep(1)
#        QtCore.QTimer.singleShot(0.01, self.update)
        pass


class LaserWidget(QtGui.QFrame):

    def __init__(self, lasers, nidaq, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.ACTlaser, self.OFF1_laser, self.OFF2_laser, self.EXClaser = lasers
        self.mW = Q_(1, 'mW')

        self.OFF_frame = TwoLaser_Frame([self.OFF1_laser, self.OFF2_laser],
                                        ['<h3>OFF 1<h3>', '<h3>OFF 2<h3>'],
                                        [(0, 247, 255), (0, 247, 255)],
                                        [(0, 100), (0, 100)],
                                        [100, 100],
                                        [10, 10],
                                        3, 0, 10,
                                        [False, False])

        self.ACTControl = LaserControl(self.ACTlaser,
                                         '<h3>Activation<h3>',
                                         color=(73, 0, 188), prange=(0, 200),
                                         tickInterval=5, singleStep=0.1)

        self.EXCControl = LaserControl(self.EXClaser,
                                         '<h3>Excitation<h3>',
                                         color=(0, 247, 255), prange=(0, 200),
                                         tickInterval=10, singleStep=1,
                                         modulable=False)

        self.tisacontrol = TiSaControl('<h3>TiSa<h3>',
                                        color=(200, 0, 0), prange=(0, 10000),
                                        tickInterval=5, singleStep=0.01,
                                        modulable = False)

        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        self.DigCtrl = DigitalControl(lasers=(self.ACTControl, self.EXCControl))
        self.DigCtrl.updateDigitalPowers()

        grid.addWidget(self.OFF_frame, 0, 0, 4, 2)
        grid.addWidget(self.ACTControl, 0, 2, 4, 1)
        grid.addWidget(self.EXCControl, 0, 3, 4, 1)
#        grid.addWidget(self.tisacontrol, 4, 0, 1, 1)
        grid.addWidget(self.DigCtrl, 4, 2, 1, 2)

        grid.setRowMinimumHeight(4, 200)

        # Current power update routine
        self.updatePowers = UpdatePowers(self)
        self.updateThread = QtCore.QThread()
        self.updatePowers.moveToThread(self.updateThread)
        self.updateThread.start()
        self.updateThread.started.connect(self.updatePowers.update)

    def getParameters(self):

        OFF1_pwr = self.OFF1_laser.power_sp.magnitude
        OFF2_pwr = self.OFF2_laser.power_sp.magnitude
        ACT_pwr = self.ACTlaser.power_sp.magnitude
        ACT_pwr_MOD = float(self.ACTlaser.query('glmp?'))
        RO_pwr = self.EXClaser.power_sp.magnitude
        RO_pwr_MOD = float(self.EXClaser.query('glmp?'))

        return {'OFF1_power': OFF1_pwr, 'OFF2_power': OFF2_pwr,
                'ACT_power': ACT_pwr, 'RO_power': RO_pwr,
                'ACT_power_MOD': ACT_pwr_MOD, 'RO_power_MOD': RO_pwr_MOD}

    def closeEvent(self, *args, **kwargs):
        self.updateThread.terminate()
        super().closeEvent(*args, **kwargs)


class DigitalControl(QtGui.QFrame):

    def __init__(self, lasers, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mW = Q_(1, 'mW')
        self.lasers = lasers
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        self.ACTDigLabel = QtGui.QLabel('<h3>Activation<h3>')
        self.ACTDigPower = QtGui.QLineEdit('0')
        self.ACTDigPower.textChanged.connect(self.updateDigitalPowers)
        self.EXCDigLabel = QtGui.QLabel('<h3>Excitation<h3>')
        self.EXCDigPower = QtGui.QLineEdit('0')
        self.EXCDigPower.textChanged.connect(self.updateDigitalPowers)


        self.ACTDigLabel.setStyleSheet("background-color: rgb{}".format((73, 0, 188)))
        self.EXCDigLabel.setStyleSheet("background-color: rgb{}".format((0, 247, 255)))

        self.DigitalControlButton = QtGui.QPushButton('Digital modulation')
        self.DigitalControlButton.setCheckable(True)
        self.DigitalControlButton.clicked.connect(self.GlobalDigitalMod)
        style = "background-color: rgb{}".format((160, 160, 160))
        self.DigitalControlButton.setStyleSheet(style)

        self.updateDigPowersButton = QtGui.QPushButton('Update powers')
        self.updateDigPowersButton.clicked.connect(self.updateDigitalPowers)

#        self.startGlobalDigitalModButton = QtGui.QPushButton('START')
#        self.startGlobalDigitalModButton.clicked.connect(self.startGlobalDigitalMod)

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.ACTDigLabel, 0, 0)
        grid.addWidget(self.ACTDigPower, 1, 0)
        grid.addWidget(self.EXCDigLabel, 0, 1)
        grid.addWidget(self.EXCDigPower, 1, 1)
        grid.addWidget(self.DigitalControlButton, 2, 0)
#        grid.addWidget(self.updateDigPowersButton, 2, 1)

#    def GlobalDigitalMod(self):
#        if self.DigitalControlButton.isChecked():
#            for i in np.arange(len(self.lasers)):
#                self.lasers[i].laser.power_sp = float(self.powers[i]) * self.mW
#        else:
#            for i in np.arange(len(self.lasers)):
#                self.lasers[i].laser.power_sp = float(self.lasers[i].laser.setPointEdit) * self.mW

    def GlobalDigitalMod(self):
        self.digitalPowers = [float(self.ACTDigPower.text()),
                              float(self.EXCDigPower.text())]

        if self.DigitalControlButton.isChecked():
            for i in np.arange(len(self.lasers)):
                print('Enterig modulation mode')
                self.lasers[i].laser.enter_mod_mode()
        else:
            for i in np.arange(len(self.lasers)):
                self.lasers[i].laser.query('cp')

#                self.lasers[i].laser.enabled = True
                print('go back to continous')

    def updateDigitalPowers(self):
        self.digitalPowers = [float(self.ACTDigPower.text()),
                              float(self.EXCDigPower.text())]
        for i in np.arange(len(self.lasers)):
            value = float(self.digitalPowers[i]) * self.mW
            print('slmp {:.5f}'.format(value))
            self.lasers[i].laser.query('slmp {:.5f}'.format(value.magnitude))
            print('power_mod set to: ', float(self.digitalPowers[i]))



class LaserControl(QtGui.QFrame):

    def __init__(self, laser, name, color, prange, tickInterval, singleStep,
                 modulable=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        self.laser = laser
        self.mW = Q_(1, 'mW')
        self.laser.digital_mod = True
        self.laser.enabled = False
        self.laser.autostart = False

        self.name = QtGui.QLabel('</h3>{}</h3>'.format(name))
        self.name.setTextFormat(QtCore.Qt.RichText)
        self.name.setAlignment(QtCore.Qt.AlignCenter)
        self.powerIndicator = QtGui.QLineEdit('{:~}'.format(self.laser.power))
        self.powerIndicator.setReadOnly(True)
        self.powerIndicator.setFixedWidth(100)
        self.powerIndicator.setStyleSheet("background-color: rgb(240,240,240);")
        self.setPointEdit = QtGui.QLineEdit(str(self.laser.power_sp.magnitude))
        self.setPointEdit.setFixedWidth(100)
        self.enableButton = QtGui.QPushButton('ON')
        self.enableButton.setFixedWidth(100)
        style = "background-color: rgb{}".format(color)
        self.enableButton.setStyleSheet(style)
        self.enableButton.setCheckable(True)
        self.name.setStyleSheet(style)
        if self.laser.enabled:
            self.enableButton.setChecked(True)

        self.minpower = QtGui.QLabel(str(prange[0]))
        self.minpower.setAlignment(QtCore.Qt.AlignCenter)
        self.maxpower = QtGui.QLabel(str(prange[1]))
        self.maxpower.setAlignment(QtCore.Qt.AlignCenter)
        self.slider = QtGui.QSlider(QtCore.Qt.Vertical, self)
        self.slider.setFocusPolicy(QtCore.Qt.NoFocus)
        self.slider.setMinimum(prange[0])
        self.slider.setMaximum(prange[1])
        self.slider.setTickInterval(tickInterval)
        self.slider.setSingleStep(singleStep)
        self.slider.setValue(self.laser.power.magnitude)


        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.name, 0, 0)
        grid.addWidget(self.powerIndicator, 3, 0)
        grid.addWidget(self.setPointEdit, 4, 0)
        grid.addWidget(self.enableButton, 5, 0)
        grid.addWidget(self.maxpower, 1, 1)
        grid.addWidget(self.slider, 2, 1, 5, 1)
        grid.addWidget(self.minpower, 7, 1)
        grid.setRowMinimumHeight(2, 30)
#        grid.setRowMinimumHeight(6, 60)

        # Digital modulation
        if modulable == True:
                self.digimodButton = QtGui.QPushButton('Digital modulation')
                style = "background-color: rgb{}".format((160, 160, 160))
                self.digimodButton.setStyleSheet(style)
                self.digimodButton.setCheckable(True)
#                grid.addWidget(self.digimodButton, 6, 0)
                self.digimodButton.toggled.connect(self.digitalMod)
                # Initial values
#                self.digimodButton.setChecked(False)

        # Connections
        self.enableButton.toggled.connect(self.toggleLaser)
        self.slider.valueChanged[int].connect(self.changeSlider)
        self.setPointEdit.returnPressed.connect(self.changeEdit)

    def toggleLaser(self):
        if self.enableButton.isChecked():
            self.laser.enabled = True
        else:
            self.laser.enabled = False

    def digitalMod(self):
        if self.digimodButton.isChecked():
            self.laser.digital_mod = True
            self.laser.enter_mod_mode()
            print(self.laser.mod_mode)
        else:
            self.laser.query('cp')

    def enableLaser(self):
        self.laser.enabled = True
        self.laser.power_sp = float(self.setPointEdit.text()) * self.mW

    def changeSlider(self, value):
        self.laser.power_sp = self.slider.value() * self.mW
        self.setPointEdit.setText(str(self.laser.power_sp.magnitude))

    def changeEdit(self):
        self.laser.power_sp = float(self.setPointEdit.text()) * self.mW
        self.slider.setValue(self.laser.power_sp.magnitude)

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)

class TwoLaser_Frame(QtGui.QFrame):
    def __init__(self, lasers, names, colors, pranges, tickIntervals, singleSteps,
                 aom_channel, aom_min_V, aom_max_V, modulable=[True, True],
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        #GUI
        self.L1 = LaserControl(lasers[0], names[0], colors[0],
                               (pranges[0][0], pranges[0][1]),
                               tickIntervals[1], singleSteps[1], modulable[1])

        self.L2 = LaserControl(lasers[1], names[1], colors[1],
                               (pranges[1][0], pranges[1][1]),
                               tickIntervals[1], singleSteps[1], modulable[1])

        self.AOMframe = AOM_Frame(aom_channel, aom_min_V, aom_max_V)

            #Layout
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(self.L1, 0, 0)
        grid.addWidget(self.L2, 0, 1)
        grid.addWidget(self.AOMframe, 1, 0, 1, 2)


class AOM_Frame(QtGui.QFrame):
    def __init__(self, channel, min_V, max_V, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self values
        self.max_V = max_V


        #Workers
        self.VC = VControl(channel, min_V, max_V)


        #GUI
        self.set_max_check = QtGui.QCheckBox('Set to max V')
        V_label = QtGui.QLabel('Voltage')
        self.V_edit = QtGui.QLineEdit()

            #Connections
        self.V_edit.returnPressed.connect(self.change_V)
        self.set_max_check.clicked.connect(self.toggle_set_to_max)
            #Layout
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(self.set_max_check, 0, 0, 1, 2)
        grid.addWidget(V_label, 1, 0, 1, 1)
        grid.addWidget(self.V_edit, 1, 1, 1, 1)

    def change_V(self):
        self.VC.changeV(float(self.V_edit.text()))

    def toggle_set_to_max(self):
        if self.set_max_check.isChecked():
            self.VC.changeV(self.max_V)
            self.V_edit.setEnabled(False)
        else:
            try:
                V = float(self.V_edit.text())
            except ValueError:
                V = 0

            self.VC.changeV(V)
            self.V_edit.setEnabled(True)


class VControl:
    def __init__(self, channel, min_V, max_V):
        self.aotask = nidaqmx.Task("SetVoltageTask")
        print('aom channel = ', channel)
        self.aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % channel,
                name_to_assign_to_channel='VoltageChannel',
                min_val=min_V,
                max_val=max_V)

        self.aotask.timing.cfg_samp_clk_timing(
            rate=100000,
            source=r'100kHzTimeBase',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=1)

    def changeV(self, new_voltage):
        self.aotask.write(new_voltage, auto_start=True)
        self.aotask.wait_until_done()
        self.aotask.stop()


class TiSaControl(QtGui.QFrame):

    def __init__(self, name, color, prange, tickInterval, singleStep,
                 invert=True, modulable=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        self.mV = Q_(1, 'mV')
        self.mW = Q_(1, 'mW')
        init_voltage = 0
        self.name = QtGui.QLabel(name)
        self.name.setTextFormat(QtCore.Qt.RichText)
        self.name.setAlignment(QtCore.Qt.AlignCenter)
        style = "background-color: rgb{}".format(color)
        self.powerIndicator = QtGui.QLineEdit(str(init_voltage))
        self.powerIndicator.setReadOnly(True)
        self.powerIndicator.setFixedWidth(100)
        self.setPointEdit = QtGui.QLineEdit(str(init_voltage))
        self.setPointEdit.setFixedWidth(100)
        self.powerIndicator = QtGui.QLineEdit()
        self.powerIndicator.setStyleSheet("background-color: rgb(240,240,240);")
        self.powerIndicator.setReadOnly(True)
        self.powerIndicator.setFixedWidth(100)
        self.name.setStyleSheet(style)
        self.calibCheck = QtGui.QCheckBox('Calibration mW/mV')

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.name, 0, 0)
        grid.addWidget(self.powerIndicator, 1, 0)
        grid.addWidget(self.setPointEdit, 2, 0)
        grid.addWidget(self.calibCheck, 3, 0)
        self.setPointEdit.returnPressed.connect(self.changeEdit)

#        self.aotask_tisa = libnidaqmx.AnalogOutputTask('aotask')
#        aochannel = 3
#        self.aotask_tisa.create_voltage_channel('Dev1/ao%s'%aochannel, min_val = 0,  max_val = 10)
#
#        self.aotask_tisa.start()

    def changeEdit(self):
        calibrated = self.calibCheck.isChecked()
        userInput = float(self.setPointEdit.text())
        if calibrated == False:
            new_value = userInput * self.mV
        if calibrated == True:
            new_value = mWtomV(userInput) * self.mV
            print(mWtomV(float(self.setPointEdit.text())))
        aochannel = 3
        self.p = Process(target=change_V_in_process, args=(new_value.magnitude, aochannel))
        self.p.start()
        self.p.join()
        if calibrated == False:
            self.powerIndicator.setText('{:~}'.format(new_value))
        if calibrated == True:
            self.powerIndicator.setText('{:~}'.format(userInput * self.mW))

    def change_voltage(self, new_value):

#        data = (new_value/1000)*np.ones(10) # new_value in millivolts
#        self.aotask_tisa.write(data, layout = 'group_by_channel')
#        self.powerIndicator.setText('{}'.format(self.setPointEdit.text()))
        for i in range(1000, 100000):
            print(i)
            data = (i/1000)*np.ones(2000) # new_value in millivolts
            self.aotask_tisa.write(data, layout = 'group_by_channel')
    #        self.powerIndicator.setText('{}'.format(self.setPointEdit.text()))

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)

def change_V_in_process(value, aochannel):
    pass
#    aotask_tisa = libnidaqmx.AnalogOutputTask('aotask')
#
#    aotask_tisa.create_voltage_channel('Dev1/ao%s'%aochannel, min_val = 0,  max_val = 1)
#
#    aotask_tisa.start()
#
#    data = (value/1000)*np.ones(2) # new_value in millivolts
#    aotask_tisa.write(data, layout = 'group_by_channel')
#
##    for a in range(1,10):
##        for i in range(1000, 10000):
##            print(i)
##            data = (i/1000)*np.ones(2) # new_value in millivolts
##            aotask_tisa.write(data, layout = 'group_by_channel')
##
#    aotask_tisa.stop()












