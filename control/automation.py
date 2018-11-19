# -*- coding: utf-8 -*-
"""
Created on Nov 14 13:27:57 2018

@author: Wei OUYANG
"""
import os
import sys
import time

from pyqtgraph.Qt import QtCore, QtGui, QtTest
import pyqtgraph.ptime as ptime

import control.guitools as guitools
import control.syntax_highlighter as syntax
from PyQt4.QtGui import QFont

class AutomationWidget(QtGui.QFrame):
    '''Widget to control the microscope automatically.'''
    def __init__(self, main, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main = main
        self.app = main.app
        self.recWidget = self.main.recWidget
        self.cameraParam = self.main.tree.p
        self.scanWidget = self.main.scanWidget
        self.laserWidgets = self.main.laserWidgets
        self.laserCtrlDict = self.laserWidgets.laserCtrlDict
        self.tisaCtrl = self.laserWidgets.tisacontrol
        self.digitalCtrl = self.laserWidgets.DigCtrl
        self.digitalPowerDict = self.digitalCtrl.digitalPowerDict

        # Title
        # autoTitle = QtGui.QLabel('<h2><strong>Automation</strong></h2>')
        # autoTitle.setTextFormat(QtCore.Qt.RichText)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)

        runButton = QtGui.QPushButton('Run')
        runButton.clicked.connect(self.runScript)

        loadButton = QtGui.QPushButton('Load')
        loadButton.clicked.connect(self.loadScript)

        saveButton = QtGui.QPushButton('Save')
        saveButton.clicked.connect(self.saveScript)

        scriptEditor = QtGui.QTextEdit()
        scriptEditor.setTabStopWidth(20)
        self._highlighter = syntax.PythonHighlighter(scriptEditor.document())
        scriptEditor.show()
        font = scriptEditor.font()
        if hasattr(QFont, "Monospace"):
            # Why is this not available on Debian squeeze
            font.setStyleHint(QFont.Monospace)
        else:
            font.setStyleHint(QFont.Courier)
        font.setFamily("Monaco")
        font.setPointSize(13)
        scriptEditor.setFont(font)


        if os.path.exists('scripts/startup.script'):
            infile = open('scripts/startup.script', 'r')
            scriptEditor.setPlainText(infile.read())
        else:
            scriptEditor.setPlainText("print('hello world.')")

        scriptEditor.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                   QtGui.QSizePolicy.Expanding)
        self.scriptEditor = scriptEditor
        self._highlighter.setDocument(self.scriptEditor.document())

        progressBar = QtGui.QProgressBar()
        progressBar.setTextVisible(True)
        progressBar.setMaximum(100)
        progressBar.setMinimum(0)
        progressBar.setValue(0)
        self.progressBar = progressBar

        autoGrid = QtGui.QGridLayout()
        self.autoGrid = autoGrid
        self.setLayout(autoGrid)

        # autoGrid.addWidget(autoTitle, 0, 0, 1, 3)
        autoGrid.addWidget(runButton, 0, 0, 1, 2)
        autoGrid.addWidget(loadButton, 0, 3, 1, 1)
        autoGrid.addWidget(saveButton, 0, 4, 1, 1)
        autoGrid.addWidget(progressBar, 1, 0, 1, 5)
        autoGrid.addWidget(scriptEditor, 6, 0, 8, 5)

        scriptPaths = sorted([f for f in os.listdir('scripts') if f.startswith('_') and f.endswith('.script')])
        self._buttonCount = 0
        self._buttonScripts = []
        for i, s in enumerate(scriptPaths):
            p = os.path.join('scripts', s)
            self._addScriptButton(p)

    def _addScriptButton(self, p):
        if self._buttonCount >= 5:
            print('cannot add more than 5 script buttons.')
            return
        if p not in self._buttonScripts:
            d, s = os.path.split(p)
            name = s[1:-(len('.script'))]
            btn = QtGui.QPushButton(name)
            def runSc():
                self.runScript(p)
            btn.clicked.connect(runSc)
            self.autoGrid.addWidget(btn, 3, self._buttonCount)
            self._buttonCount += 1
            self._buttonScripts.append(p)

    def startLive(self):
        self.main.liveviewStart()

    def stopLive(self):
        self.main.liveviewStop()

    def setStatus(self, status):
        self.progressBar.setFormat(str(status))

    def setProgress(self, value):
        value = max(value, 0)
        value = min(value, 100)
        self.progressBar.setValue(value)

    def showError(self, e, throw=True):
       msg = QtGui.QMessageBox()
       msg.setIcon(QtGui.QMessageBox.Critical)
       msg.setText('Error: ' + str(e))
       msg.setWindowTitle("Error")
       msg.setStandardButtons(QtGui.QMessageBox.Ok)
       msg.exec_()
       if throw:
           raise Exception('Error: ' + str(e))

    def showMessage(self, info):
       msg = QtGui.QMessageBox()
       msg.setIcon(QtGui.QMessageBox.Information)
       msg.setText(str(info))
       msg.setWindowTitle("Message")
       msg.setStandardButtons(QtGui.QMessageBox.Ok)
       msg.exec_()

    def hello(self):
        print('hello.')
        self.showMessage('hello.')

    def wait(self, seconds):
        if seconds > 1:
            for i in range(int(seconds)):
                time.sleep(1)
                self.app.processEvents()
        else:
            time.sleep(seconds)

    def setRecordMode(self, mode):
        if mode > 0 and mode < len(self.recWidget.modeWidgets):
            self.recWidget.modeWidgets[mode].click()
        else:
            self.showError('Recording mode should be a number between "{}" and {}'.format(0, len(self.recWidget.modeWidgets)))

    def specifyFileName(self, filePath):
        self.recWidget.specifyfile.setChecked(True)
        self.recWidget.filenameEdit.setText(str(filePath))

    def startRecord(self):
        if self.recWidget.recButton.text() == 'REC':
            self.recWidget.recButton.click()
        else:
            self.showError('Recording Cannot be started.')

    def stopRecord(self, wait=True, timeout=None):
        if self.recWidget.recButton.text() == 'STOP':
            self.recWidget.recButton.click()
            if wait:
                count = 0
                while not self.recWidget.readyToRecord:
                    self.app.processEvents()
                    if timeout is not None:
                        count += 1
                        if count > timeout:
                            self.showError('Recording Cannot be stopped (timeout).')
                            break
        else:
            self.showError('Recording Cannot be stopped.')

    def toggleCamera(self):
        self.main.toggleCamButton.click()

    def setCameraParam(self, key, value):
        if '/' in key:
            ks = key.split('/')
            pg = self.cameraParam.param(ks[0].strip())
            p = pg.param(ks[1].strip())
        else:
            p = self.cameraParam.param(key)
        if p.opts['type'] == 'list':
            if type(value) is int and value> 0 and value < len(p.opts['values']):
                value = p.opts['values'][value]
            if value not in p.opts['values']:
                self.showError('Unsupported option "{}", supported options for "{}" are: {}'.format(value, key, str(p.opts['values'])))
        p.setValue(value)

    def setExposure(self, t):
        self.setCameraParam('Timings/Set exposure time', t)

    def setTrigger(self, source):
        self.setCameraParam('Acquisition mode/Trigger source', source)

    def setLaser(self, name, on_off):
        if name in self.laserCtrlDict:
            enableButton = self.laserCtrlDict[name].enableButton
            if on_off == 'ON' or on_off == True:
                if enableButton.isChecked():
                    # self.showError('laser '+name+' is already on.', throw=False)
                    print('laser '+name+' is already on.')
                else:
                    enableButton.click()
            elif on_off == 'OFF' or on_off == False:
                if not enableButton.isChecked():
                    print('laser '+name+' is already off.')
                    # self.showError('laser '+name+' is already off.', throw=False)
                else:
                    enableButton.click()
            else:
                self.showError('you can only set laser to "ON" or "OFF".')
        else:
            self.showError('laser '+name+' not found, available lasers are ' +str(self.laserCtrlDict.keys()))

    def setLaserPower(self, name, power):
        if name in self.laserCtrlDict:
            setPointEdit = self.laserCtrlDict[name].setPointEdit
            if type(power) is float or type(power) is int:
                setPointEdit.setText(str(power))
            else:
                self.showError('you can only set laser to "ON" or "OFF".')
        else:
            self.showError('laser '+name+' not found, available lasers are ' +str(self.laserCtrlDict.keys()))

    def setDigitalModulation(self, on_off):
        enableButton = self.digitalCtrl.DigitalControlButton
        if on_off == 'ON' or on_off == True:
            if enableButton.isChecked():
                #self.showError('digital modulation is already on.', throw=False)
                print('digital modulation is already on.')
            else:
                enableButton.click()
        elif on_off == 'OFF' or on_off == False:
            if not enableButton.isChecked():
                print('digital modulation is already off.')
                # self.showError('digital modulation is already off.', throw=False)
            else:
                enableButton.click()
        else:
            self.showError('you can only set digital modulation to "ON" or "OFF".')

    def setDigitalPower(self, name, power):
        '''
        name: ON, READOUT, OFF
        '''
        if name in self.digitalPowerDict:
            setPointEdit = self.digitalPowerDict[name]
            if type(power) is float or type(power) is int:
                setPointEdit.setText(str(power))
            else:
                self.showError('you can only set the laser power with a number.')
        else:
            self.showError('laser '+name+' not found, available lasers are ' +str(self.digitalPowerDict.keys()))

    def setScanMode(self, mode):
        self.scanWidget.scanRadio()
        if mode >0 and mode< len(self.scanWidget.modeWidgets):
            self.scanWidget.modeWidgets[mode].click()
        else:
            self.showError('scan mode should be a number betwee {} and {}.'.format(0, len(self.scanWidget.modeWidgets)))

    def setScanRepeat(self, repeat):
        if repeat and not self.scanWidget.continuousCheck.isChecked():
            self.scanWidget.continuousCheck.click()
        elif not repeat and self.scanWidget.continuousCheck.isChecked():
            self.scanWidget.continuousCheck.click()

    def loadScan(self, filePath=None):
        self.scanWidget.loadScan(filePath)

    def whenScanStop(self, callback):
        self.scanWidget._stopScanCallback = callback

    def waitUntilScanStop(self):
        while self.scanWidget.scanning:
            self.app.processEvents()

    def startScan(self):
        if self.scanWidget.scanning:
            self.showError('cannot start scan while scanning.')
        else:
            self.scanWidget.scanOrAbort() #scanButton.click()
            # while not self.scanWidget.scanning:
            #     time.sleep(100)
            #     self.app.processEvents()

    def stopScan(self):
        if not self.scanWidget.scanning:
            self.showError('cannot stop while it is not scanning.')
        else:
            self.scanWidget.scanButton.click()

    def saveScan(self, filePath=None):
        self.scanWidget.saveScan(filePath)

    def _wrapFunc(self, func):
        # wrap all the api functions such that it will not freeze the UI
        def wrappedFunc(*args, **kwargs):
            ret = func(*args, **kwargs)
            self.app.processEvents()
            return ret
        return wrappedFunc

    def runScript(self, scriptPath=None):
        try:
            self.progressBar.setEnabled(True)
            self.progressBar.setValue(0)
            exclude_methods = []
            api = {func : getattr(self, func) for func in dir(self) if callable(getattr(self, func)) and not func.startswith('_') and func not in exclude_methods}
            for k in api:
                api[k] = self._wrapFunc(api[k])
            api['main'] = self.main
            if type(scriptPath) is str:
                if os.path.exists(scriptPath):
                    with open(scriptPath, 'r') as fs:
                        code =fs.read()
                else:
                    self.showError('Script file "{}" does not exists.'.format(scriptPath))
            else:
                code = self.scriptEditor.toPlainText()
            exec(code, globals(), api)
            self.progressBar.setValue(100)
        except Exception as e:
            self.showError(e, throw=False)
        finally:
            self.progressBar.setEnabled(False)

    def loadScript(self, scriptPath=None):
        if os.path.exists('scripts'):
            root = 'scripts'
        else:
            root = ''
        if type(scriptPath) is str:
            if os.path.exists(scriptPath):
                filePath = scriptPath
            else:
                self.showError('Script file "{}" does not exists.'.format(scriptPath))
        else:
            filePath = QtGui.QFileDialog.getOpenFileName(self, 'Load script', root, filter='*.script')
        if filePath is None or filePath == '':
            return
        if os.path.exists(filePath):
            infile = open(filePath, 'r')
            self.scriptEditor.setPlainText(infile.read())
        else:
            self.showError('Failed to load script.', throw=False)

    def saveScript(self):
        if not os.path.exists('scripts'):
            os.makedirs('scripts')
        filePath = QtGui.QFileDialog.getSaveFileName(self, 'Save script', 'scripts', filter='*.script')
        if filePath is None or filePath == '':
            return
        if not filePath.endswith('.script'):
            filePath += '.script'
        with open(filePath, 'w') as f:
            f.write(self.scriptEditor.toPlainText())

        d, n = os.path.split(filePath)
        if n.startswith('_') and os.path.abspath(d) == os.path.abspath('scripts'):
            self._addScriptButton(filePath)
