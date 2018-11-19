# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 14:19:15 2018

@author: testaRES
"""

import nidaqmx
import numpy as np

nidaq = nidaqmx.system.System.local().devices['Dev1']

dotask = nidaqmx.Task('dotask')
aotask = nidaqmx.Task('aotask')
aotask2 = nidaqmx.Task('aotask2')
samples = 2


sig0 = np.zeros(samples, dtype=np.float)
sig1 = np.ones(samples, dtype=np.float)
sig = sig0#np.concatenate((sig0, sig1, sig0, sig1, sig0, sig1, sig0, sig1))
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
            samps_per_chan=samples)

aotask2.timing.cfg_samp_clk_timing(
            rate=100000,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples)

dotask.do_channels.add_do_chan(
                lines='Dev1/port0/line5',
                name_to_assign_to_lines='chanX')

dotask.timing.cfg_samp_clk_timing(
            rate=100000,
            source=r'100kHzTimeBase',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples)

aotask.write(sig, auto_start=False)
dotask.write(np.array(sig, dtype=np.bool), auto_start=False)
dotask.start()

aotask.start()
aotask.wait_until_done()
aotask.stop()
aotask.close()
dotask.wait_until_done()
dotask.stop()
dotask.close()
aotask2.write(sig, auto_start=False)
aotask2.start()
aotask2.wait_until_done()
aotask2.stop()

aotask.close()
aotask2.close()