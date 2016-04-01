# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 18:02:53 2016

@author: testaRES
"""

import numpy as np
import libnidaqmx

nidaq = libnidaqmx.Device('Dev1')
nidaq.reset()
#try:
#    a.clear()
#except:
#    pass
#
#def run():
a = libnidaqmx.AnalogOutputTask()
#
a.create_voltage_channel('Dev1/ao3')

a.configure_timing_sample_clock(rate = 1000, sample_mode = 'finite', samples_per_channel = 2)
#
#
s = np.zeros(2)
#
#s[range(0, 500)] = 1
#
a.write(s, layout='group_by_channel')
a.wait_until_done()
a.stop()
#
##a.stop()