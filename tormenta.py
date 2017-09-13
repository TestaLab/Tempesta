# -*- coding: utf-8 -*-
"""
Created on Thu May 21 13:19:31 2015

@author: Barabas, Bodén, Masullo
"""
from pyqtgraph.Qt import QtGui
import nidaqmx

from control import control
import control.instruments as instruments


def main():

    app = QtGui.QApplication([])

    cobolt = 'cobolt.cobolt0601.Cobolt0601'

    # NI-DAQ channels configuration
    DO = {'405': 0, '473': 1, '488': 2, 'CAM': 3}
    AO = {'x': 0, 'y': 1, 'z': 2}
    outChannels = [DO, AO]
    nidaq = nidaqmx.system.System.local().devices['Dev1']

# TODO: create an instruments.Camera(hamamatsu) or something similar
    with instruments.Laser(cobolt, 'COM4') as violetlaser, \
            instruments.Laser(cobolt, 'COM13') as exclaser, \
            instruments.Laser(cobolt, 'COM6') as offlaser1, \
            instruments.Laser(cobolt, 'COM7') as offlaser2, \
            instruments.PZT('nv401', 8) as pzt:

        orcaflashV3 = instruments.Camera(0)
        orcaflashV2 = instruments.Camera(1)
        print(violetlaser.idn)
        print(exclaser.idn)
        print(offlaser1.idn)
        print(offlaser2.idn)

        win = control.TormentaGUI(violetlaser, exclaser, offlaser1, offlaser2,
                                  orcaflashV2, orcaflashV3,
                                  nidaq, outChannels, pzt)
        win.show()

        app.exec_()