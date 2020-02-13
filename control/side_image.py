# -*- coding: utf-8 -*-
"""
Created on Tue Sep 25 10:13:47 2018

@author: testaRES
"""
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

import os
import sys
import numpy as np
import tifffile as tiff
import copy

if not os.environ['PY_UTILS_PATH'] in sys.path:
    sys.path.append(os.environ['PY_UTILS_PATH'])
import DataIO_tools

class SideImageWidget(QtGui.QFrame):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.im_dict = {}
        self.ID = 0
        self.current_im = None
        self.view = 0
        # Image Widget
        imageWidget = pg.GraphicsLayoutWidget()
        self.img_vb = imageWidget.addViewBox(row=0, col=0)
        self.img_vb.setMouseMode(pg.ViewBox.PanMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
#        self.img.setPxMode(True)
        self.img_vb.addItem(self.img)
        self.img_vb.setAspectLocked(True)
        self.img_hist = pg.HistogramLUTItem(image=self.img)
#        self.hist.vb.setLimits(yMin=0, yMax=2048)
        imageWidget.addItem(self.img_hist, row=0, col=1)

        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.sliderMoved[int].connect(self.slider_moved)

        """Button group for choosing view"""
        self.choose_view_group = QtGui.QButtonGroup()
        self.choose_view_box = QtGui.QGroupBox('Choose view')
        self.view_layout = QtGui.QHBoxLayout()

        self.standard_view = QtGui.QRadioButton('Standard view')
        self.choose_view_group.addButton(self.standard_view, 0)
        self.view_layout.addWidget(self.standard_view)
        self.bottom_view = QtGui.QRadioButton('Bottom side view')
        self.choose_view_group.addButton(self.bottom_view, 1)
        self.view_layout.addWidget(self.bottom_view)
        self.left_view = QtGui.QRadioButton('Left side view')
        self.choose_view_group.addButton(self.left_view, 2)
        self.view_layout.addWidget(self.left_view)

        self.choose_view_box.setLayout(self.view_layout)

        self.choose_view_group.buttonClicked.connect(self.change_view)

        """Set initial states"""
        self.standard_view.setChecked(True)

        """Frame slider"""
        frame_label = QtGui.QLabel('Frame # ')
        self.frame_nr = QtGui.QLineEdit('0')
        self.frame_nr.textChanged.connect(self.frame_nr_changed)
        self.frame_nr.setFixedWidth(45)

        """Image list"""
        self.image_list = QtGui.QListWidget()
        self.image_list.itemClicked.connect(self.IndexChanged)
        save_btn = QtGui.QPushButton('Save image')
        save_btn.clicked.connect(self.Save_Image)


        """Layout"""
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)


        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.choose_view_box, 1, 0)
        grid.addWidget(self.slider, 2, 0)
        grid.addWidget(frame_label, 2, 1)
        grid.addWidget(self.frame_nr, 2, 2)
        grid.addWidget(self.image_list, 0, 1, 1, 2)
        grid.addWidget(save_btn, 1, 1, 1, 2)

    def makeBeadImg(self, data, parDict):
        """Takes average of each frame and reshapes into 3D data.
        - Dims is given as (Slices, X ,Y)"""
        data = np.array(data, dtype=np.float32)
        trace = np.mean(data, (1,2))
        data = np.reshape(trace, (parDict['dims'][2], parDict['dims'][1], parDict['dims'][0]))
        print('Shape of bead scan data: ', data.shape)
        self.current_im = ImageObj(data, parDict)

        data_name = ('Image' + str(self.ID))
        self.ID += 1
        list_item = QtGui.QListWidgetItem(data_name)
        self.image_list.addItem(list_item)
        self.im_dict[list_item.text()] = self.current_im
        self.image_list.setCurrentItem(list_item)
        self.IndexChanged()

    def slider_moved(self, new_value):
#        i = self.slider.value()
        print('New slider value = ', new_value)
        self.frame_nr.setText(str(new_value))
        self.setImgSlice()

    def change_view(self):
        print('Changing view')
        self.view = self.choose_view_group.checkedId()
        self.current_im.current_view = self.view
        self.slider.setMaximum(self.current_im.data.shape[self.view] - 1)
        self.slider.setValue(self.current_im.current_slice_nr[self.view])
        self.frame_nr.setText(str(self.current_im.current_slice_nr[self.view]))
        self.setImgSlice()

    def frame_nr_changed(self):
        try:
            i = int(self.frame_nr.text())
        except TypeError:
            print('ERROR: Input must be an integer value')
        self.slider.setValue(i)
        self.setImgSlice()

    def setImgSlice(self):

        i = self.slider.value()

        self.current_im.current_slice_nr[self.view] = i
        print('New current slices = ', self.current_im.current_slice_nr)
        self.img.setImage(self.current_im.getSlice())

    def IndexChanged(self):
        new_list_item = self.image_list.currentItem()
        self.current_im = self.im_dict[new_list_item.text()]
        self.view = self.current_im.current_view
        self.choose_view_group.button(self.view).setChecked(True)
        self.slider.setValue(self.current_im.current_slice_nr[self.view])
        self.slider.setMaximum(self.current_im.data.shape[self.view])

        self.frame_nr.setText(str(self.current_im.current_slice_nr[self.view]))
        self.setImgSlice()




    def Save_Image(self):

        savename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', filter='*.tiff')
        data_to_save = copy.deepcopy(self.current_im.data)
        DataIO_tools.save_data(data_to_save, path=savename)


    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)


class ImageObj(object):
    def __init__(self, data, parDict, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data = data
        self.current_slice_nr = [0,0,0]
        self.current_view = 0 #Standard view
        self.slices = np.shape(data)[0]
        self.parDict = parDict

    def getSlice(self):
        if  self.current_view== 0:
            return self.data[self.current_slice_nr[0], ::, ::]
        elif self.current_view == 1:
            return self.data[::, self.current_slice_nr[1], ::]
        elif self.current_view == 2:
            return self.data[::, ::, self.current_slice_nr[2]]






