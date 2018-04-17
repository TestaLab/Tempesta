# -*- coding: utf-8 -*-
"""
Created on Thu Mar 29 11:27:57 2018

@author: Tempesta_team
"""
import os
import sys
import subprocess
import time
import numpy as np
import re

import h5py as hdf
import tifffile as tiff

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
from tkinter import Tk, filedialog, messagebox

import control.guitools as guitools


# Widget to control image or sequence recording. Recording only possible when
# liveview active. StartRecording called when "Rec" presset. Creates recording
# thread with RecWorker, recording is then done in this seperate thread.
class RecordingWidget(QtGui.QFrame):
    '''Widget to control image or sequence recording.
    Recording only possible when liveview active.
    StartRecording called when "Rec" presset.
    Creates recording thread with RecWorker, recording is then done in this
    seperate thread.'''
    def __init__(self, main, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main = main
        self.nCameras = len(main.cameras)
        self.dataname = 'data'      # In case I need a QLineEdit for this

        self.recWorkers = [None] * len(self.main.cameras)
        self.recThreads = [None] * len(self.main.cameras)
        self.savenames = [None] * len(self.main.cameras)

        self.z_stack = []
        self.recMode = 1

        self.dataDir = r"D:\Data"
        self.initialDir = os.path.join(self.dataDir, time.strftime('%Y-%m-%d'))

        self.filesizewar = QtGui.QMessageBox()
        self.filesizewar.setText("File size is very big!")
        self.filesizewar.setInformativeText(
            "Are you sure you want to continue?")
        self.filesizewar.setStandardButtons(
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        # Title
        recTitle = QtGui.QLabel('<h2><strong>Recording settings</strong></h2>')
        recTitle.setTextFormat(QtCore.Qt.RichText)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)

        # Folder and filename fields
        self.folderEdit = QtGui.QLineEdit(self.initialDir)
        openFolderButton = QtGui.QPushButton('Open')
        openFolderButton.clicked.connect(self.openFolder)
        self.specifyfile = QtGui.QCheckBox('Specify file name')
        self.specifyfile.clicked.connect(self.specFile)
        self.filenameEdit = QtGui.QLineEdit('Current_time')
        self.formatBox = QtGui.QComboBox()
        self.formatBox.addItem('tiff')
        self.formatBox.addItem('hdf5')

        # Snap and recording buttons
        self.snapTIFFButton = QtGui.QPushButton('Snap')
        self.snapTIFFButton.setStyleSheet("font-size:16px")
        self.snapTIFFButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                          QtGui.QSizePolicy.Expanding)
        self.snapTIFFButton.clicked.connect(self.snapTIFF)
        self.recButton = QtGui.QPushButton('REC')
        self.recButton.setStyleSheet("font-size:16px")
        self.recButton.setCheckable(True)
        self.recButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                     QtGui.QSizePolicy.Expanding)
        self.recButton.clicked.connect(self.startRecording)

        # Number of frames and measurement timing
        modeTitle = QtGui.QLabel('<strong>Mode</strong>')
        modeTitle.setTextFormat(QtCore.Qt.RichText)
        self.specifyFrames = QtGui.QRadioButton('Number of frames')
        self.specifyFrames.clicked.connect(self.specFrames)
        self.specifyTime = QtGui.QRadioButton('Time (s)')
        self.specifyTime.clicked.connect(self.specTime)
        self.recScanOnceBtn = QtGui.QRadioButton('Scan once')
        self.recScanOnceBtn.clicked.connect(self.recScanOnce)
        self.recScanLapseBtn = QtGui.QRadioButton('Time-lapse scan')
        self.recScanLapseBtn.clicked.connect(self.recScanLapse)
        self.timeLapseEdit = QtGui.QLineEdit('5')
        self.timeLapseLabel = QtGui.QLabel('Each/Total [s]')
        self.timeLapseLabel.setAlignment(QtCore.Qt.AlignRight)
        self.timeLapseTotalEdit = QtGui.QLineEdit('60')
        self.timeLapseScan = 0
        self.untilSTOPbtn = QtGui.QRadioButton('Run until STOP')
        self.untilSTOPbtn.clicked.connect(self.untilStop)
        self.timeToRec = QtGui.QLineEdit('1')
        self.timeToRec.textChanged.connect(self.filesizeupdate)
        self.currentTime = QtGui.QLabel('0 / ')
        self.currentTime.setAlignment((QtCore.Qt.AlignRight |
                                       QtCore.Qt.AlignVCenter))
        self.currentFrame = QtGui.QLabel('0 /')
        self.currentFrame.setAlignment((QtCore.Qt.AlignRight |
                                        QtCore.Qt.AlignVCenter))
        self.numExpositionsEdit = QtGui.QLineEdit('100')
        self.tRemaining = QtGui.QLabel()
        self.tRemaining.setAlignment((QtCore.Qt.AlignCenter |
                                      QtCore.Qt.AlignVCenter))
        self.numExpositionsEdit.textChanged.connect(self.filesizeupdate)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setTextVisible(False)

        self.filesizeBar = QtGui.QProgressBar()
        self.filesizeBar.setTextVisible(False)
        self.filesizeBar.setRange(0, 2000000000)

        # Layout
        buttonWidget = QtGui.QWidget()
        buttonGrid = QtGui.QGridLayout()
        buttonWidget.setLayout(buttonGrid)
        buttonGrid.addWidget(self.snapTIFFButton, 0, 0)
        buttonWidget.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                   QtGui.QSizePolicy.Expanding)
        buttonGrid.addWidget(self.recButton, 0, 2)

        recGrid = QtGui.QGridLayout()
        self.setLayout(recGrid)

        recGrid.addWidget(recTitle, 0, 0, 1, 3)
        recGrid.addWidget(QtGui.QLabel('Folder'), 2, 0)

        if len(self.main.cameras) > 1:
            self.DualCam = QtGui.QCheckBox('Two-cam rec')
            recGrid.addWidget(self.DualCam, 1, 3)
            recGrid.addWidget(self.folderEdit, 2, 1, 1, 2)
            recGrid.addWidget(openFolderButton, 2, 3)
            recGrid.addWidget(self.filenameEdit, 3, 1, 1, 2)
            recGrid.addWidget(self.formatBox, 3, 3)
        else:
            recGrid.addWidget(self.folderEdit, 2, 1, 1, 2)
            recGrid.addWidget(openFolderButton, 2, 3)
            recGrid.addWidget(self.filenameEdit, 3, 1, 1, 2)
            recGrid.addWidget(self.formatBox, 3, 3)

        recGrid.addWidget(self.specifyfile, 3, 0)

        recGrid.addWidget(modeTitle, 4, 0)
        recGrid.addWidget(self.specifyFrames, 5, 0, 1, 5)
        recGrid.addWidget(self.currentFrame, 5, 1)
        recGrid.addWidget(self.numExpositionsEdit, 5, 2)
        recGrid.addWidget(self.specifyTime, 6, 0, 1, 5)
        recGrid.addWidget(self.currentTime, 6, 1)
        recGrid.addWidget(self.timeToRec, 6, 2)
        recGrid.addWidget(self.tRemaining, 6, 3, 1, 2)
#        recGrid.addWidget(self.progressBar, 5, 4, 1, 2)
        recGrid.addWidget(self.recScanOnceBtn, 7, 0, 1, 5)
        recGrid.addWidget(self.recScanLapseBtn, 8, 0, 1, 5)
        recGrid.addWidget(self.timeLapseLabel, 8, 1)
        recGrid.addWidget(self.timeLapseEdit, 8, 2)
        recGrid.addWidget(self.timeLapseTotalEdit, 8, 3)
        recGrid.addWidget(self.untilSTOPbtn, 9, 0, 1, 5)
        recGrid.addWidget(buttonWidget, 10, 0, 1, 0)

        recGrid.setColumnMinimumWidth(0, 70)

        # Initial condition of fields and checkboxes.
        self.writable = True
        self.readyToRecord = False
        self.filenameEdit.setEnabled(False)
        self.specifyTime.setChecked(True)
        self.specTime()
        self.filesizeupdate()

    @property
    def readyToRecord(self):
        return self._readyToRecord

    @readyToRecord.setter
    def readyToRecord(self, value):
        self.snapTIFFButton.setEnabled(value)
        self.recButton.setEnabled(value)
        self._readyToRecord = value

    @property
    def writable(self):
        return self._writable

    # Setter for the writable property. If Nr of frame is checked only the
    # frames field is set active and viceversa.
    @writable.setter
    def writable(self, value):
        if value:
            if self.specifyFrames.isChecked():
                self.specFrames()
            elif self.specifyTime.isChecked():
                self.specTime()
            elif self.recScanOnceBtn.isChecked():
                self.recScanOnce()
            elif self.recScanLapseBtn.isChecked():
                self.recScanLapse()
            else:
                self.untilStop()
        else:
            self.numExpositionsEdit.setEnabled(False)
            self.timeToRec.setEnabled(False)
#        self.folderEdit.setEnabled(value)
#        self.filenameEdit.setEnabled(value)
        self._writable = value

    def specFile(self):
        if self.specifyfile.checkState():
            self.filenameEdit.setEnabled(True)
            self.filenameEdit.setText('Filename')
        else:
            self.filenameEdit.setEnabled(False)
            self.filenameEdit.setText('Current time')

    # Functions for changing between choosing frames or time or "Run until
    # stop" when recording.
    def specFrames(self):
        self.numExpositionsEdit.setEnabled(True)
        self.timeToRec.setEnabled(False)
        self.timeLapseEdit.setEnabled(False)
        self.timeLapseTotalEdit.setEnabled(False)
        self.filesizeBar.setEnabled(True)
        self.progressBar.setEnabled(True)
        self.recMode = 1
        self.filesizeupdate()

    def specTime(self):
        self.numExpositionsEdit.setEnabled(False)
        self.timeToRec.setEnabled(True)
        self.timeLapseEdit.setEnabled(False)
        self.timeLapseTotalEdit.setEnabled(False)
        self.filesizeBar.setEnabled(True)
        self.progressBar.setEnabled(True)
        self.recMode = 2
        self.filesizeupdate()

    def recScanOnce(self):
        self.numExpositionsEdit.setEnabled(False)
        self.timeToRec.setEnabled(False)
        self.timeLapseEdit.setEnabled(False)
        self.timeLapseTotalEdit.setEnabled(False)
        self.filesizeBar.setEnabled(False)
        self.progressBar.setEnabled(False)
        self.recMode = 3

    def recScanLapse(self):
        self.numExpositionsEdit.setEnabled(False)
        self.timeToRec.setEnabled(False)
        self.timeLapseEdit.setEnabled(True)
        self.timeLapseTotalEdit.setEnabled(True)
        self.filesizeBar.setEnabled(False)
        self.progressBar.setEnabled(False)
        self.recMode = 4

    def untilStop(self):
        self.numExpositionsEdit.setEnabled(False)
        self.timeToRec.setEnabled(False)
        self.timeLapseEdit.setEnabled(False)
        self.timeLapseTotalEdit.setEnabled(False)
        self.filesizeBar.setEnabled(False)
        self.progressBar.setEnabled(False)
        self.recMode = 5

    def filesizeupdate(self):
        ''' For updating the approximated file size of and eventual recording.
        Called when frame dimensions or frames to record is changed.'''
        if self.specifyFrames.isChecked():
            frames = int(self.numExpositionsEdit.text())
        else:
            frames = int(self.timeToRec.text()) / self.main.RealExpPar.value()

        self.filesize = 2*frames*max([np.prod(s) for s in self.main.shapes])
        # Percentage of 2 GB
        self.filesizeBar.setValue(min(2000000000, self.filesize))
        self.filesizeBar.setFormat(str(self.filesize / 1000))

    def n(self):
        text = self.numExpositionsEdit.text()
        if text == '':
            return 0
        else:
            return int(text)

    def getTimeOrFrames(self):
        ''' Returns the time to record in order to record the correct number
        of frames.'''
        if self.specifyFrames.isChecked():
            return int(self.numExpositionsEdit.text())
        else:
            return int(self.timeToRec.text())

    def openFolder(self):
        try:
            if sys.platform == 'darwin':
                subprocess.check_call(['open', '', self.folderEdit.text()])
            elif sys.platform == 'linux':
                subprocess.check_call(
                    ['gnome-open', '', self.folderEdit.text()])
            elif sys.platform == 'win32':
                os.startfile(self.folderEdit.text())

        except FileNotFoundError:
            if sys.platform == 'darwin':
                subprocess.check_call(['open', '', self.dataDir])
            elif sys.platform == 'linux':
                subprocess.check_call(['gnome-open', '', self.dataDir])
            elif sys.platform == 'win32':
                os.startfile(self.dataDir)

    def loadFolder(self):
        try:
            root = Tk()
            root.withdraw()
            folder = filedialog.askdirectory(parent=root,
                                             initialdir=self.initialDir)
            root.destroy()
            if folder != '':
                self.folderEdit.setText(folder)
        except OSError:
            pass

    # Attributes saving
    def getAttrs(self):
        self.main.AbortROI()
        attrs = self.main.tree.attrs()

        for laserControl in self.main.laserWidgets.controls:
            name = re.sub('<[^<]+?>', '', laserControl.name.text())
            attrs.append((name, laserControl.laser.power))

        for key in self.main.scanWidget.scanParValues:
            attrs.append((key, self.main.scanWidget.scanParValues[key]))

        attrs.append(('Scan mode',
                      self.main.scanWidget.scanMode.currentText()))
        attrs.append(('True_if_scanning',
                      self.main.scanWidget.scanRadio.isChecked()))

        for key in self.main.scanWidget.pxParValues:
            attrs.append((key, self.main.scanWidget.pxParValues[key]))

        attrs.extend([('element_size_um', [1, 0.066, 0.066]),
                      ('Date', time.strftime("%Y-%m-%d")),
                      ('Saved at', time.strftime("%H:%M:%S")),
                      ('NA', 1.42)])

        return attrs

    def snapHDF(self):
        folder = self.folderEdit.text()

        if not os.path.exists(folder):
            os.mkdir(folder)

        image = self.main.image

        name = os.path.join(folder, self.getFileName())
        savename = guitools.getUniqueName(name + '.hdf5')
        store_file = hdf.File(savename)
        store_file.create_dataset(name=self.dataname, data=image)
        for item in self.getAttrs():
            if item[1] is not None:
                store_file[self.dataname].attrs[item[0]] = item[1]
        store_file.close()

    def getFileName(self):
        if self.specifyfile.checkState():
            filename = self.filenameEdit.text()

        else:
            filename = time.strftime('%Hh%Mm%Ss')

        return filename

    def snapTIFF(self):
        folder = self.folderEdit.text()
        if not os.path.exists(folder):
            os.mkdir(folder)

        time.sleep(0.01)
        savename = os.path.join(folder, self.getFileName()) + '_snap.tiff'
        savename = guitools.getUniqueName(savename)
        image = self.main.latest_images[self.main.currCamIdx].astype(np.uint16)
        tiff.imsave(savename, image, description=self.dataname,
                    software='Tempesta', imagej=True,
                    resolution=(1/self.main.umxpx, 1/self.main.umxpx),
                    metadata={'spacing': 1, 'unit': 'um'})

        guitools.attrsToTxt(os.path.splitext(savename)[0], self.getAttrs())

    def folderWarning(self):
        root = Tk()
        root.withdraw()
        messagebox.showwarning(title='Warning', message="Folder doesn't exist")
        root.destroy()

    def updateGUI(self):

        eSecs = self.recWorkers[self.main.currCamIdx].tRecorded
        nframe = self.recWorkers[self.main.currCamIdx].nStored
#        rSecs = self.getTimeOrFrames() - eSecs
#        rText = '{}'.format(datetime.timedelta(seconds=max(0, rSecs)))
#        self.tRemaining.setText(rText)
        self.currentFrame.setText(str(nframe) + ' /')
        self.currentTime.setText(str(int(eSecs)) + ' /')
#        self.progressBar.setValue(100*(1 - rSecs / (eSecs + rSecs)))

    def startRecording(self):
        ''' Called when "Rec" button is pressed.'''
        if self.recButton.isChecked():
            ret = QtGui.QMessageBox.Yes
            # Checks if estimated file size is dangerously large, > 1,5GB-.
            if self.filesize > 1500000000:
                ret = self.filesizewar.exec_()

            if ret == QtGui.QMessageBox.Yes:

                # Sets Recording widget to not be writable during recording.
                self.writable = False
                self.readyToRecord = False
                self.recButton.setEnabled(True)
                self.recButton.setText('STOP')

                # Sets camera parameters to not be writable during recording.
                self.main.tree.writable = False
                self.main.liveviewButton.setEnabled(False)
#                self.main.liveviewStop()  # Stops liveview from updating

                # Saves the time when started to calculate remaining time.
                self.startTime = ptime.time()

                if self.recMode == 4:   # recMode 4 is timelapse scan
                    total = float(self.timeLapseTotalEdit.text())
                    each = float(self.timeLapseEdit.text())
                    self.timeLapseScan = int(np.ceil(total/each))
                    self.timer = QtCore.QTimer()
                    self.timer.timeout.connect(self.doRecording)
                    self.timer.start(float(self.timeLapseEdit.text())*1000)
                self.doRecording()

            else:
                self.recButton.setChecked(False)
                self.folderWarning()

        else:
            if self.recMode in [3, 4]:
                self.timeLapseScan = 0
                self.recButton.setEnabled(False)
                if not self.main.scanWidget.scanning:
                    self.endRecording()
            for i in range(0, self.nCameras):
                ind = np.mod(self.main.currCamIdx + i, 2)
                self.recWorkers[ind].pressed = False

    def doRecording(self):
        if not self.main.scanWidget.scanning:
            self.makeSavenames()
            for i in range(0, self.nCameras):
                ind = np.mod(self.main.currCamIdx + i, 2)

                # Creates an instance of RecWorker class.
                self.recWorkers[ind] = RecWorker(
                    self, self.main.cameras[ind], self.recMode,
                    self.getTimeOrFrames(), self.main.shapes[ind],
                    self.main.lvworkers[ind], self.main.RealExpPar,
                    self.savenames[ind], self.dataname, self.getAttrs())
                # Connects the updatesignal that is continously emitted
                # from recworker to updateGUI function.
                self.recWorkers[ind].updateSignal.connect(self.updateGUI)
                # Connects the donesignal emitted from recworker to
                # endrecording function.
                self.recWorkers[ind].doneSignal.connect(self.endRecording)
                # Creates a new thread
                self.recThreads[ind] = QtCore.QThread()
                # moves the worker object to this thread.
                self.recWorkers[ind].moveToThread(self.recThreads[ind])
                self.recThreads[ind].started.connect(
                    self.recWorkers[ind].start)

            for i in range(0, self.nCameras):
                ind = np.mod(self.main.currCamIdx + i, 2)
                self.recThreads[ind].start()

    def endRecording(self):
        """ Function called when recording finishes to reset relevant
        parameters."""
        if self.nCameras == 2 and (
                not self.recWorkers[0].done or not self.recWorkers[1].done):
            pass
        else:
            ind = self.main.currCamIdx

            for i in range(0, self.nCameras):
                ind = np.mod(self.main.currCamIdx + i, 2)
                self.recThreads[ind].terminate()
                # Same as done in Liveviewrun()

            if self.recMode != 4:
                self.writable = True
                self.readyToRecord = True
                self.recButton.setText('REC')
                self.recButton.setChecked(False)
                self.main.tree.writable = True
                self.main.liveviewButton.setEnabled(True)
                self.progressBar.setValue(0)
                self.currentTime.setText('0 /')
                self.currentFrame.setText('0 /')
            else:
                self.timeLapseScan -= 1
                if self.timeLapseScan <= 0:
                    self.timer.stop()
                    self.writable = True
                    self.readyToRecord = True
                    self.recButton.setEnabled(True)
                    self.recButton.setText('REC')
                    self.recButton.setChecked(False)
                    self.main.tree.writable = True
                    self.main.liveviewButton.setEnabled(True)
                    self.progressBar.setValue(0)
                    self.currentTime.setText('0 /')
                    self.currentFrame.setText('0 /')

    def makeSavenames(self):
        folder = self.folderEdit.text()
        if not os.path.exists(folder):
            os.mkdir(folder)

        if self.nCameras == 1:
            self.savenames[0] = (
                os.path.join(folder, self.getFileName()) + '_rec')
            self.savenames[0] = guitools.getUniqueName(self.savenames[0])

        else:
            nameRoot = os.path.join(folder, self.getFileName())
            for i in range(0, self.nCameras):
                ind = np.mod(self.main.currCamIdx + i, 2)
                # Sets name for final output file
                self.savenames[ind] = nameRoot + '_rec_cam' + str(ind + 1)
                # If same filename exists it is appended by (1) or (2) etc.
                self.savenames[ind] = guitools.getUniqueName(
                    self.savenames[ind])


class RecWorker(QtCore.QObject):

    updateSignal = QtCore.pyqtSignal()
    doneSignal = QtCore.pyqtSignal()

    def __init__(self, main, camera, recMode, timeorframes, shape, lvworker,
                 t_exp, savename, dataname, attrs, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main = main
        self.camera = camera

        # 1=frames, 2=time, 3=scan once, 4=Time-lapse scan, 5=until stop
        self.recMode = recMode

        # Nr of seconds or frames to record depending on bool_ToF.
        self.timeorframes = timeorframes
        self.shape = shape  # Shape of one frame
        self.lvworker = lvworker
        self.t_exp = t_exp
        self.savename = savename
        self.dataname = dataname
        self.attrs = attrs
        self.pressed = True
        self.done = False
        self.scanWidget = self.main.main.scanWidget

        self.nStored = 0  # number of frames stored
        self.tRecorded = 0

    def start(self):
        self.lvworker.startRecording()
        time.sleep(0.1)

        self.starttime = time.time()
        saveMode = self.main.formatBox.currentText()

        # Main loop for waiting until recording is finished and sending update
        # signal
        if self.recMode == 1:
            if saveMode == 'tiff':
                with tiff.TiffWriter(self.savename + '.tiff',
                                     software='Tormenta') as storeFile:
                    while self.nStored < self.timeorframes and self.pressed:
                        self.tRecorded = time.time() - self.starttime
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        self.nStored += len(newFrames)
                        for frame in newFrames:
                            storeFile.save(frame)
                        self.updateSignal.emit()

            elif saveMode == 'hdf5':
                with hdf.File(self.savename + '.hdf5', "w") as storeFile:
                    storeFile.create_dataset(
                        'Images', (1, self.shape[0], self.shape[1]),
                        maxshape=(None, self.shape[0], self.shape[1]))
                    dataset = storeFile['Images']
                    while self.nStored < self.timeorframes and self.pressed:
                        self.tRecorded = time.time() - self.starttime
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        dataset.resize((self.nStored+len(newFrames)), axis=0)
                        dataset[self.nStored:] = newFrames
                        self.nStored += len(newFrames)
                        self.updateSignal.emit()

        elif self.recMode == 2:
            if saveMode == 'tiff':
                with tiff.TiffWriter(self.savename + '.tiff',
                                     software='Tormenta') as storeFile:
                    while self.tRecorded < self.timeorframes and self.pressed:
                        self.tRecorded = time.time() - self.starttime
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        self.nStored += len(newFrames)
                        for frame in newFrames:
                            storeFile.save(frame)
                        self.updateSignal.emit()

            elif saveMode == 'hdf5':
                with hdf.File(self.savename + '.hdf5', "w") as storeFile:
                    storeFile.create_dataset(
                        'Images', (1, self.shape[0], self.shape[1]),
                        maxshape=(None, self.shape[0], self.shape[1]))
                    dataset = storeFile['Images']
                    while self.tRecorded < self.timeorframes and self.pressed:
                        self.tRecorded = time.time() - self.starttime
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        dataset.resize((self.nStored + len(newFrames)), axis=0)
                        dataset[self.nStored:] = newFrames
                        self.nStored += len(newFrames)
                        self.updateSignal.emit()

        elif self.recMode in [3, 4]:
            # Change setting for scanning
            self.main.main.trigsourceparam.setValue('External "frame-trigger"')
            laserWidget = self.main.main.laserWidgets
            laserWidget.DigCtrl.DigitalControlButton.setChecked(True)

            # Getting Z steps
            if self.scanWidget.scanMode.currentText() == 'VOL scan':
                sizeZ = self.scanWidget.scanParValues['sizeZ']
                stepSizeZ = self.scanWidget.scanParValues['stepSizeZ']
                stepsZ = int(np.ceil(sizeZ / stepSizeZ))
            else:
                stepsZ = 1
            framesExpected = int(self.scanWidget.stageScan.frames / stepsZ)

            # start scanning
            self.scanWidget.scanButton.click()
            if saveMode == 'tiff':
                for i in range(stepsZ):
                    name = self.savename + '_z' + str(i) + '.tiff'
                    with tiff.TiffWriter(name, software='Tormenta') \
                            as storeFile:
                        while self.nStored != framesExpected*(i + 1) \
                                and self.pressed:
                            time.sleep(0.01)
                            newFrames = self.lvworker.fRecorded[self.nStored:]
                            if self.nStored + len(newFrames) \
                                    > framesExpected*(i + 1):
                                maxF = framesExpected*(i + 1) - self.nStored
                                newFrames = newFrames[:maxF]
                            self.nStored += len(newFrames)
                            for frame in newFrames:
                                storeFile.save(frame)
                            self.updateSignal.emit()

            elif saveMode == 'hdf5':
                with hdf.File(self.savename + '.hdf5', "w") as storeFile:
                    for i in range(stepsZ):
                        zPlane = storeFile.create_group('z' + str(i))
                        dataset = zPlane.create_dataset(
                            'Images', (1, self.shape[0], self.shape[1]),
                            maxshape=(None, self.shape[0], self.shape[1]))
                        while self.nStored != framesExpected*(i+1)\
                                and self.pressed:
                            time.sleep(0.01)
                            newFrames = self.lvworker.fRecorded[self.nStored:]
                            if self.nStored + len(newFrames) \
                                    > framesExpected*(i + 1):
                                maxF = framesExpected*(i+1)-self.nStored
                                newFrames = newFrames[:maxF]
                            size = (self.nStored - framesExpected*i +
                                    len(newFrames))
                            dataset.resize(size, axis=0)
                            dataset[self.nStored:] = newFrames
                            self.nStored += len(newFrames)
                            self.updateSignal.emit()
        elif self.recMode == 5:
            if saveMode == 'tiff':
                with tiff.TiffWriter(self.savename + '.tiff',
                                     software='Tormenta') as storeFile:
                    while self.pressed:
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        self.nStored += len(newFrames)
                        for frame in newFrames:
                            storeFile.save(frame)
                        self.updateSignal.emit()

            elif saveMode == 'hdf5':
                with hdf.File(self.savename + '.hdf5', "w") as storeFile:
                    storeFile.create_dataset(
                        'Images', (1, self.shape[0], self.shape[1]),
                        maxshape=(None, self.shape[0], self.shape[1]))
                    dataset = storeFile['Images']
                    while self.pressed:
                        time.sleep(0.01)
                        newFrames = self.lvworker.fRecorded[self.nStored:]
                        dataset.resize((self.nStored + len(newFrames)), axis=0)
                        dataset[self.nStored:] = newFrames
                        self.nStored += len(newFrames)
                        self.updateSignal.emit()

        self.lvworker.stopRecording()

        self.done = True
        self.doneSignal.emit()
