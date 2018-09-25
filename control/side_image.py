# -*- coding: utf-8 -*-
"""
Created on Tue Sep 25 10:13:47 2018

@author: testaRES
"""
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg

import numpy as np
import tifffile as tiff

class SideImageWidget(QtGui.QFrame):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        
        self.im_list = None
        self.ID = 1
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
        
        self.image_list = QtGui.QListWidget()
        self.image_list.itemClicked.connect(self.IndexChanged)
        save_btn = QtGui.QPushButton('Save image')
        save_btn.clicked.connect(self.Save_Image)
        
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        
        
        grid.addWidget(imageWidget, 0, 0, 2, 1)
        grid.addWidget(self.image_list, 0, 1)
        grid.addWidget(save_btn, 1, 1)

    def makeBeadImg(self, data):
        
        imside = np.sqrt(np.size(data, 0))
        trace = np.mean(data, (1,2), dtype=np.float32)
        data = np.reshape(trace, (imside, imside))
        im = ImageObj(data)
        if self.im_list is None:
            self.im_list = np.array([im])
        else:
            self.im_list = np.concatenate((self.im_list, [im]))
            
        self.image_list.addItem('Image' + str(self.ID))
        self.ID += 1
        self.img.setImage(self.im_list[-1].data)
        
    def IndexChanged(self):
        self.curr_ind = self.image_list.currentRow()
        self.img.setImage(self.im_list[self.curr_ind].data)
        
    def Save_Image(self):
        
        savename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', filter='*.tiff')
        print(savename)
        tiff.imsave(savename, np.array(self.im_list[self.curr_ind].data, dtype=np.float32), dtype=np.float32)
        
    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        
        
class ImageObj(object):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.data = data