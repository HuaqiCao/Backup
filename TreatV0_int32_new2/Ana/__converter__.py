#!/usr/bin/python
# -*- coding: utf-8 -*- 
from nptdms import TdmsFile
import time
import math
import numpy as np
def run():
    start = time.process_time()
    tdms_file = TdmsFile.read("../../LMO_highNa22_0701/LMO_Na22_1700gain_200Mohm_2Vbias_1Vrange_water_0701.tdms")
    end   = time.process_time()
    print('Time to read the file: %s Seconds' %(end-start))
    all_groups = tdms_file.groups()
    all_group_channels = all_groups[1].channels()
    data = all_group_channels[0]
    fileBIN2 = open("../../LMO_highNa22_0701/LMO_highNa22_0701.BIN2",'wb')
    num = 0
    print('Total: %d' %(len(data)//2000000))
    '''
    tot_num = len(data)//20000
    data_tmp = np.zeros(20000)
    for num in range(0, tot_num):
        if num%100 == 0:
            print(num//100)
        data_tmp = np.float32(data[20000*num:20000*(num+1)])
        txt = data_tmp.tobytes()
        fileBIN2.write(txt)
    '''
    for line in data:
        if num%2000000 == 0:
            print(num//2000000)
        intdata = int((line+5)*(math.pow(2,16)-1)/10)
        if intdata < 0:
            print(num)
        '''
        if num > 4000000:
            break
        '''
        b = intdata.to_bytes(length=2, byteorder='little', signed=False)
        fileBIN2.write(b)
        num += 1
    fileBIN2.close()
    print(data[0:10])


run()
