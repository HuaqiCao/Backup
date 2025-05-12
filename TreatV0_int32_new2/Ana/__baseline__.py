#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
import sys
from nptdms import TdmsFile
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
def func(x, a, x0, sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))
def run():
    wl = 3000
    FilePath = '../'
    FileName = 'LMO_highNa22_0701.BIN2'
    opfile = open(FilePath+FileName,"rb")
    open_noisecandidate = open(FilePath+'data/noisecandidate.txt','r')
    line = open_noisecandidate.readline()
    k = 0
    y = []
    while line:
        k += 1
        filedata = line.split('\n')
        x = []
        opfile.seek(2*(int(filedata[0])),0)
        for num in range(0,wl):
            data = int.from_bytes(opfile.read(2), "little",signed=False)
            x.append(data)
        arr_x = np.array(x)
        arr_x = (arr_x - np.mean(arr_x))*511/129.2
        for data2 in arr_x:
            y.append(data2)
        line = open_noisecandidate.readline()
    arr_y = np.array(y)
    fig, ax = plt.subplots(nrows=1, ncols=1)
    arr_yhist = plt.hist(y, bins=200, range=(-200, 200))
    print(arr_yhist[0])
    xn = np.arange(-200,200,2)
    # Executing curve_fit on noisy data
    popt, pcov = curve_fit(func, xn, arr_yhist[0])

    #popt returns the best fit values for parameters of the given model (func)
    print (popt)

    ym = func(xn, popt[0], popt[1], popt[2])
    ax.plot(xn, ym, c='r', label='Gaussian fit')
    ax.legend()
    #fig.tight_layout()
    #ax.plot(bins, y, '--')
    ax.grid(True)
    ax.set_xlabel('Baseline (keV)')
    ax.set_ylabel('Counts')
    print(popt[1])
    print(popt[2])
    #ax.set_title(r'Histogram of IQ: $\mu$={}, $\sigma$={}'.format(popt[1],popt[2]))
    ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(popt[2]))
    plt.show()


run()
