# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 14:19:15 2018

@author: testaRES
"""

import nidaqmx
import numpy as np

#dotask = nidaqmx.Task('dotask')
aotask = nidaqmx.Task('aotask')
aotask2 = nidaqmx.Task('aotask2')
samples = 10**4


sig0 = np.zeros(samples, dtype=np.uint32)
sig1 = np.ones(samples, dtype=np.uint32)
sig = np.concatenate((sig0, sig1, sig0, sig1, sig0, sig1, sig0, sig1))
dsig = sig == 1


aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao1',
                name_to_assign_to_channel='chan_0',
                min_val=0,
                max_val=10)

aotask2.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao2',
                name_to_assign_to_channel='chan_2',
                min_val=0,
                max_val=10)

aotask.timing.cfg_samp_clk_timing(
            rate=100000,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples*8)

aotask2.timing.cfg_samp_clk_timing(
            rate=100000,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples*8)

#dotask.do_channels.add_do_chan(
#                lines='Dev1/port0',
#                name_to_assign_to_lines='chanX')
#
#dotask.timing.cfg_samp_clk_timing(
#            rate=100000,
#            source=r'100kHzTimeBase',
#            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#            samps_per_chan=samples*8)

aotask.write(sig, auto_start=False)
#dotask.write(sig, auto_start=False)
#dotask.start()

aotask.start()
aotask.wait_until_done()
aotask.stop()
aotask.close()

#aotask2.write(sig, auto_start=False)
#aotask2.start()
#aotask2.wait_until_done()
#aotask2.stop()

aotask.close()
aotask2.close()