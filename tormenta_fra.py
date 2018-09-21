# -*- coding: utf-8 -*-
"""
Created on Thu May 21 13:19:31 2015

@author: Barabas, Bodén, Masullo
"""
from pyqtgraph.Qt import QtGui
import nidaqmx
import sys

from control import control
import control.instruments as instruments


def main():

    app = QtGui.QApplication([])

    cobolt = 'cobolt.cobolt0601.Cobolt0601'
    with instruments.Laser(cobolt, 'COM12') as bluelaser, \
         instruments.Laser(cobolt, 'COM9') as bluelaser2, \
         instruments.Laser(cobolt, 'COM5') as greenlaser, \
         instruments.Laser(cobolt, 'COM11') as violetlaser, \
         instruments.Laser(cobolt, 'COM10') as uvlaser, \
          instruments.PZT(8) as pzt, instruments.Webcam() as webcam:
              
        lasers = [violetlaser, bluelaser, bluelaser2, greenlaser, uvlaser]
        
        cameras = instruments.Cameras()

        nidaq = nidaqmx.system.System.local().devices['Dev1']
        win = control.TormentaGUI(lasers, cameras, nidaq, pzt, webcam)
        win.show()

        sys.exit(app.exec_())
