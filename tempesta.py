# -*- coding: utf-8 -*-
"""
Created on Thu May 21 13:19:31 2015

@author: federico
"""
from pyqtgraph.Qt import QtGui

def main():

    from control import control
    import control.instruments as instruments    
    
    app = QtGui.QApplication([])

#TO DO: create an instruments.Camera(hamamatsu) or something similar

#    with instruments.Camera('hamamatsu.hamamatsu_camera.HamamatsuCameraMR') as orcaflash, \
    with instruments.Laser('cobolt.cobolt0601.Cobolt0601', 'COM12') as bluelaser, \
         instruments.OneFiveLaser() as violetlaser, \
         instruments.Laser('cobolt.cobolt0601.Cobolt0601', 'COM10') as uvlaser, \
         instruments.SLM() as slm, \
         instruments.DAQ() as daq, instruments.ScanZ(12) as scanZ:
             
        #instruments.Camera('andor.ccd.CCD') as andor, \
#         instruments.SLM() as slm, \

#for now, bluelaser is the 488nm laser, greenlaser is the 405nm laser and redlaser is the 355nm laser
        orcaflash = instruments.Camera()
        print(bluelaser.idn)
        print(violetlaser.idn)
        print(uvlaser.idn)
        print(daq.idn)
        win = control.TempestaGUI(bluelaser, violetlaser, uvlaser,
                                  scanZ, daq, orcaflash,slm)
        win.show()
        app.exec_()
    
def analysisApp():

    from analysis import analysis

    app = QtGui.QApplication([])

    win = analysis.AnalysisWidget()
    win.show()

    app.exec_()

    
    
