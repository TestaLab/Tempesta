# -*- coding: utf-8 -*-
"""
Created on Tue Sep 25 10:13:47 2018

@author: testaRES
"""
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

import numpy as np
import tifffile as tiff
import copy

class SideImageWidget(QtGui.QFrame):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        
        self.im_dict = {}
        self.ID = 0
        self.current_im = None
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
        self.slider.valueChanged[int].connect(self.slider_moved)
        
        frame_label = QtGui.QLabel('Frame # ')
        self.frame_nr = QtGui.QLineEdit('0')
        self.frame_nr.textChanged.connect(self.frame_nr_changed)
        self.frame_nr.setFixedWidth(45)
        
        self.image_list = QtGui.QListWidget()
        self.image_list.itemClicked.connect(self.IndexChanged)
        save_btn = QtGui.QPushButton('Save image')
        save_btn.clicked.connect(self.Save_Image)
        
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        
        
        grid.addWidget(imageWidget, 0, 0, 1, 3)
        grid.addWidget(self.slider, 1, 0)
        grid.addWidget(frame_label, 1, 1)
        grid.addWidget(self.frame_nr, 1, 2)
        grid.addWidget(self.image_list, 0, 3)
        grid.addWidget(save_btn, 1, 3)
        
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
        
    def slider_moved(self):
        i = self.slider.value()
        self.frame_nr.setText(str(i))
        self.setImgSlice(i)
        
    def frame_nr_changed(self):
        try:
            i = int(self.frame_nr.text())
        except TypeError:
            print('ERROR: Input must be an integer value')
        self.slider.setValue(i)
        self.setImgSlice(i)
        
    def setImgSlice(self, i):
        if i > self.current_im.slices:
            print('ERROR: slice number larger than existing slices')
            i = self.current_im.slices - 1
            self.frame_nr.setText(str(i))

        self.current_im.current_slice_nr = i
        self.img.setImage(self.current_im.getCurrentSlice())
        
    def IndexChanged(self):
        new_list_item = self.image_list.currentItem()
        self.current_im = self.im_dict[new_list_item.text()]
        self.slider.setValue(self.current_im.current_slice_nr)
        self.slider.setMaximum(self.current_im.slices - 1)
        self.frame_nr.setText(str(self.current_im.current_slice_nr))
        self.img.setImage(self.current_im.getCurrentSlice())
        
        
        
        
    def Save_Image(self):
        
        savename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', filter='*.tiff')
        save_data = copy.deepcopy(self.current_im.data)
        save_data.shape = 1, save_data.shape[0], 1, save_data.shape[2], save_data.shape[1], 1
        vx_size_0 = self.current_im.parDict['step_sizes'][0]
        vx_size_1 = self.current_im.parDict['step_sizes'][1]
        vx_size_2 = self.current_im.parDict['step_sizes'][2]
        tiff.imwrite(savename, save_data, imagej=True, 
                     resolution=(1/vx_size_0, 1/vx_size_1),
                     metadata={'spacing': vx_size_2, 'unit': 'µm'})

        
    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        
        
class ImageObj(object):
    def __init__(self, data, parDict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.data = data
        self.current_slice_nr = 0
        self.slices = np.shape(data)[0]
        self.parDict = parDict
        
    def getCurrentSlice(self):
        return self.data[self.current_slice_nr]