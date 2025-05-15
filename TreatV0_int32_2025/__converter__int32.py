#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
import sys
from nptdms import TdmsFile
import time
import math
import numpy as np
def run():
    start = time.process_time()
    app = QApplication(sys.argv)
    fname,ftype = QFileDialog.getOpenFileName(None, "Open File", "~/", "TDMS file(*.tdms)")#如果添加一个内容则需要加两个分号
    fnewname = fname.split(".tdms",1)[0]
    tdms_file = TdmsFile.read(fname)
    end   = time.process_time()
    print('Time to read the file: %s Seconds' %(end-start))
    all_groups = tdms_file.groups()
    print(all_groups[0])
    all_group_channels = all_groups[1].channels()
    data_heat = all_group_channels[0]
    print("Make a new File:"+fnewname+".BIN4")
    fileBIN2_heat = open(fnewname+".BIN4",'wb')
    num = 0
    print('Total: %d' %(len(data_heat)//2000000))
    tot_num = len(data_heat)//20000
    converted_heat = np.zeros(20000)
    for num in range(0, tot_num):
        if num%100 == 0:
            print(num//100)
        converted_heat = ((data_heat[20000*num:20000*(num+1)]+5.0)*(2**15)/5).astype(np.dtype('<u4'))
        txt_heat = converted_heat.tobytes()
        fileBIN2_heat.write(txt_heat)
    fileBIN2_heat.close()
    '''
    fig, ax = plt.subplots(nrows=1, ncols=1)
    #ax.plot(np.arange(2*heat_length), heat_data_OF, c='r', label='OF_data_2t')
    #ax.plot(np.arange(2*heat_length), heat_OF_template_shifted*heat_filamp, c='g', label='OF_template_2t')
    ax.plot(np.arange(20000), data[0:20000], c='b', label='heat')
    ax.plot(np.arange(20000), data2[0:20000], c='r', label='light')
    #ax.plot(np.arange(heat_length)/fs+heat_length//2/fs, heat_data_norm*heat_filamp, c='b', label='Data_2t')
    #ax.plot(np.arange(2*heat_length)/fs, heat_diffdata, c='b', label='Diffdata_2t')
    ax.legend()
    ax.grid(True)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Height')
    #ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))
    plt.show()
    '''
    #print(data[0:10])


run()
