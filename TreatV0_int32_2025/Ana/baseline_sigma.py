#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
import sys
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def __run():
    ene_cali_coeff = 1.0*100.6/430.12
    app = QApplication(sys.argv)
    fname, ftype = QFileDialog.getOpenFileName(None, "Open File", "../", "")
    if len(fname) == 0:
        print("No file selected.")
        return

    FilePath = str(fname.rsplit("/", 1)[0]) + "/"
    FileName = str(fname.rsplit("/", 1)[1])

    file_para = open(FilePath + 'data/paralist.txt', 'r')
    file_para.readline()
    file_para.readline()
    wl = int(file_para.readline().split('\n')[0])

    opfile = open(FilePath + FileName, "rb")
    open_noisecandidate = open(FilePath + 'data/noisecandidate.txt', 'r')
    line = open_noisecandidate.readline()
    k = 0
    y_raw = []
    y_diff_filtered_2t = []
    diff_filter_c = np.loadtxt(FilePath + 'data/diff_filter.txt', dtype=complex)
    diff_filter_t = np.real(np.fft.ifft(diff_filter_c))
    diff_filter_2t = np.zeros(2 * wl - 1)
    diff_filter_2t[:(wl - 1) // 2] = diff_filter_t[:(wl - 1) // 2]
    diff_filter_2t[-(wl - 1) // 2:] = diff_filter_t[-(wl - 1) // 2:]
    while line:
        k += 1
        filedata = line.split('\n')
        x = []
        num = 0
        opfile.seek(4 * (int(filedata[0]) - wl//2), 0)
        '''
        for num in range(0, 2 * wl):
            data = int.from_bytes(opfile.read(4), "little", signed=False)
            x.append(data)
        arr_x_2t = np.array(x)
        '''
        txt = opfile.read(2*wl*4)
        arr_x_2t = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        arr_x_2t = arr_x_2t - np.mean(arr_x_2t[wl // 2:wl // 2 + wl])
        arr_x_2t = (arr_x_2t) * ene_cali_coeff
        arr_raw = arr_x_2t[wl // 2:wl // 2 + wl]
        diff_arr_x_2t = np.diff(arr_x_2t)
        diff_filtered_2t = np.real(
            np.fft.ifft(np.fft.fft(diff_arr_x_2t * np.hamming(2 * wl - 1)) * np.fft.fft(diff_filter_2t)))
        for data1 in arr_raw:
            y_raw.append(data1)
        for data2 in diff_filtered_2t[wl // 2 - 1:wl // 2 + wl - 3]:
            y_diff_filtered_2t.append(data2)
        line = open_noisecandidate.readline()
    arr_y_diff_filtered_2t = np.array(y_diff_filtered_2t)
    arr_y_raw = np.array(y_raw)

    up_limit = 5 * np.std(arr_y_diff_filtered_2t)
    low_limit = -1.0 * up_limit
    bin_num = 200
    bin_width = (up_limit - low_limit) / bin_num

    xn = np.arange(low_limit, low_limit + bin_num * bin_width, bin_width)+bin_width/2
    fig, ax = plt.subplots(nrows=1, ncols=1)
    arr_yhist_diff_filtered_2t = plt.hist(arr_y_diff_filtered_2t, bins=bin_num, range=(low_limit, up_limit),
                                          histtype='bar')
    para = np.zeros(3)
    para[0] = len(arr_y_diff_filtered_2t)/10
    para[1] = 0
    para[2] = np.std(arr_y_diff_filtered_2t)
    # Executing curve_fit on noisy data
    popt4, pcov4 = curve_fit(__func, xn, arr_yhist_diff_filtered_2t[0],para)
    # popt returns the best fit values for parameters of the given model (func)
    print(abs(popt4[2]))
    ym4 = __func(xn, popt4[0], popt4[1], popt4[2])
    ax.plot(xn, ym4, c='r', label='Gaussian fit')
    ax.legend()
    ax.grid(True)
    ax.set_xlabel('Baseline (keV)')
    ax.set_ylabel('Counts')
    ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))

    up_limit_raw = 5 * np.std(arr_y_raw)
    low_limit_raw = -1.0 * up_limit_raw
    bin_width_raw = (up_limit_raw - low_limit_raw) / bin_num

    xn_raw = np.arange(low_limit_raw, low_limit_raw + bin_num * bin_width_raw, bin_width_raw)
    fig2, ax2 = plt.subplots(nrows=1, ncols=1)
    arr_yhist_raw = plt.hist(arr_y_raw, bins=bin_num, range=(low_limit_raw, up_limit_raw), histtype='bar')
    para[0] = len(arr_y_raw)/10
    para[1] = 0
    para[2] = np.std(arr_y_raw)
    # Executing curve_fit on noisy data
    popt, pcov = curve_fit(__func, xn_raw, arr_yhist_raw[0],para)
    # popt returns the best fit values for parameters of the given model (func)
    print(abs(popt[2]))
    ym = __func(xn_raw, popt[0], popt[1], popt[2])
    ax2.plot(xn_raw, ym, c='r', label='Gaussian fit')
    ax2.legend()
    ax2.grid(True)
    ax2.set_xlabel('Baseline (keV)')
    ax2.set_ylabel('Counts')
    ax2.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt[2])))

    open_noisecandidate.close()
    file_para.close()
    opfile.close()
    plt.show(block=False)
    # Wait for the figure windows to be closed
    while plt.fignum_exists(fig.number) or plt.fignum_exists(fig2.number):
        app.processEvents()

    return

def __func(x, a, x0, sigma):
    return a * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))

if __name__ == "__main__":
    __run()
