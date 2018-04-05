# -*- coding: utf-8 -*-
"""
Created on Thu Mar 29 14:39:06 2018

@author: Andreas
"""
import sys
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import thorlabs_apt.thorlabs_apt as apt

class Coord():
    def __init__(self, id_nr, value):
        self._value = value
        self._motor = apt.Motor(id_nr)

        self.min_value = self._motor.get_stage_axis_info()[0]
        self.max_value = self._motor.get_stage_axis_info()[1]

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = np.clip(value, self.min_value, self.max_value)
        print('Setting motor position to: ', self._value)
        self._motor.position = self.value


class StageControl(QtGui.QWidget):

        def __init__(self, serials):
            super().__init__()
            nr_motors = len(serials)

            self._coords =[]
            for i in range(nr_motors):
                self._coords.append(Coord(serials[i], 0))

            self.step_size = 0.1


        def move_stage(self, dim, direction):
            self._coords[dim].value += direction*self.step_size

        def keyPressEvent(self, e):

            if e.key() == QtCore.Qt.Key_Escape:
                self.close()

            elif e.key() == e.key() == QtCore.Qt.Key_Left:
                self.move_stage(0, -1)

            elif e.key() == e.key() == QtCore.Qt.Key_Right:
                self.move_stage(0, 1)

            elif e.key() == e.key() == QtCore.Qt.Key_Down:
                self.move_stage(1, -1)

            elif e.key() == e.key() == QtCore.Qt.Key_Up:
                self.move_stage(1, 1)

            elif e.key() == e.key() == QtCore.Qt.Key_Minus:
                self.move_stage(2, -1)

            elif e.key() == e.key() == QtCore.Qt.Key_Plus:
                self.move_stage(2, 1)

def main():
    serials = [x[1] for x in apt.list_available_devices()]

    app = QtGui.QApplication(sys.argv)

    wid = QtGui.QWidget()#StageControl(serials)
    wid.show()
    app.aboutToQuit.connect(app.deleteLater)
    sys.exit(app.exec())