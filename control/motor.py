# -*- coding: utf-8 -*-
"""
Created on Thu Mar 29 14:39:06 2018

@author: Andreas
"""
import sys
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import thorlabs_apt.thorlabs_apt as apt

def motor_serials():
    return [x[1] for x in apt.list_available_devices()]

class Coord():
    def __init__(self, id_nr):
        self._motor = apt.Motor(id_nr)
        self._value = self._motor.position

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

    def closeEvent(self):
        del self._motor


class StageControl(QtGui.QWidget):
    def __init__(self, serials):
            super().__init__()

            self.stage = Stage(serials)

    def keyPressEvent(self, e):
        self.stage.keyPressEvent(e)

class Stage(object):
    def __new__(cls, serials, *args, **kwargs):
        try:
            stage = PhysStage(serials)
        except:
            stage = MockStage()
        return stage

class PhysStage(object):

        def __init__(self, serials):
            super().__init__()
            print('Initializing Stage with ', len(serials), 'motors')
            nr_motors = len(serials)

            self._coords =[]
            for i in range(nr_motors):
                self._coords.append(Coord(serials[i]))

            self.step_size_L = 0.01
            self.step_size_M = 0.001
            self.step_size_S = 0.0001

        def move_stage(self, dim, direction, step):
            self._coords[dim].value += direction*step

        def keyPressEvent(self, e):
            print('Key event detected in motor.py')

            if e.key() == e.key() == QtCore.Qt.Key_Left:
                self.move_stage(0, -1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_Right:
                self.move_stage(0, 1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_Down:
                self.move_stage(1, -1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_Up:
                self.move_stage(1, 1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_Q:
                self.move_stage(2, -1, self.step_size_L)

            elif e.key() == e.key() == QtCore.Qt.Key_W:
                self.move_stage(2, 1, self.step_size_L)

            elif e.key() == e.key() == QtCore.Qt.Key_A:
                self.move_stage(2, -1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_S:
                self.move_stage(2, 1, self.step_size_M)

            elif e.key() == e.key() == QtCore.Qt.Key_X:
                self.move_stage(2, -1, self.step_size_S)

            elif e.key() == e.key() == QtCore.Qt.Key_Z:
                self.move_stage(2, 1, self.step_size_S)
            else:
                print('Key not recognized as stage movement command')

class MockStage(object):
    def __init__(self):
        super().__init__()
        print('Initializing MockStageControl')

    def move_stage(self, dim, direction, step):
            pass

    def keyPressEvent(self, e):
            print('Key event detected in motor.py, no action since mock device')
            pass

def cleanup():
    apt.core._cleanup()

def main():
    serials = motor_serials()

    app = QtGui.QApplication(sys.argv)

    wid = StageControl([90876329, 90876330, 90876331])
    wid.show()

    sys.exit(app.exec())