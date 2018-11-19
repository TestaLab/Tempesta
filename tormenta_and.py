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
    with instruments.Laser(cobolt, 'COM7') as OFFlaser1, \
         instruments.Laser(cobolt, 'COM6') as OFFlaser2, \
         instruments.Laser(cobolt, 'COM5') as EXClaser, \
         instruments.Laser(cobolt, 'COM10') as ACTlaser, \
          instruments.PZT(8) as pzt, instruments.Webcam() as webcam:

        cameras = instruments.Cameras()

        nidaq = nidaqmx.system.System.local().devices['Dev1']
        win = control.TormentaGUI(ACTlaser, OFFlaser1, OFFlaser2, EXClaser, cameras,
                                  nidaq, pzt, webcam)
        win.show()

        sys.exit(app.exec_())
