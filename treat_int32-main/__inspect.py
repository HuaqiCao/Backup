import matplotlib.pyplot as plt
from  matplotlib.figure  import  Figure 
import numpy as np
import time
import math
import random
import sys
import os
def __read():
        FilePath=str('/Volumes/Lab 104/Run13_LMO_data/LMO_water_0626/')
        FileName=str('LMO_withwater_10h_0626.BIN2')
        print(FilePath+FileName)
        opfile = open(FilePath+FileName,"rb")
        x = []
        wl = 100000
        startp = 550000
        opfile.seek(2*startp,0)
        for num in range(0,wl):
            data = int.from_bytes(opfile.read(2), "little",signed=False)
            x.append(data)
        arr_x = np.array(x)
        arr_t = 0.0001*np.arange(wl)
        canvas  =  Figure(figsize=(800, 600), dpi=100)
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(arr_t, arr_x, label='LMO signal')
        ax.set_xlabel('Time (second)', fontsize=15)
        ax.set_ylabel('Amplitude (ADC)', fontsize=15)
        #ax.set_title('LMO output signal in a 10s window')
        ax.grid(True)
        plt.show()
        return
__read() 
