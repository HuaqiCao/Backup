import numpy as np
import matplotlib.pyplot as plt
from lmfit import Model, Parameters
import myFunc
from PyQt5.QtWidgets import QApplication, QFileDialog
import sys
import shutil
import os

global sampling

def tempfunc1(x, A, td, tr, t0, v0):
    # y = A * ( exp(-t/td)  - exp(-t/tr) ) + v0
    xx = x - t0
    y = np.zeros_like(x)
    mask = xx > 0
    y[mask] = A * (np.exp(-xx[mask] / td) - np.exp(-xx[mask] / tr))
    return y

def tempfunc2(x, A, p, td1, td2, tr, t0):
    # y = A * ( p*exp(-t/td1) + (1-p)*exp(-t/td2) - exp(-t/tr) )
    xx = x - t0
    y = np.zeros_like(x)
    mask = xx > 0
    y[mask] = A * (
        p * np.exp(-xx[mask] / td1) +
        (1 - p) * np.exp(-xx[mask] / td2) -
        np.exp(-xx[mask] / tr)
    )
    # y = myFunc.bessel_filter(y, 2000, fc=100, order=8)
    return y


def fitTemp(sampling, fname, N, isReplace=False):
    if isReplace:
        backup_fname = fname + ".backup"
        shutil.copy2(fname, backup_fname)

    sampling = sampling * N
    y = np.loadtxt(fname)
    y = myFunc.interpolateN(y, N)
    t = np.arange(len(y)) / sampling

    model = Model(tempfunc2)

    params = Parameters()
    params.add('A',     value=1.000, min=1,     max=1000)
    params.add('p',     value=0.001, min=0,     max=1)
    params.add('td1',   value=0.015, min=0.0001, max=1)
    params.add('td2',   value=0.001, min=0.0001, max=1)
    params.add('tr',    value=0.001, min=0.0001, max=1)
    params.add('t0',    value=0.993, min=0.97,   max=1.0)

    # 拟合
    result = model.fit(y, params, x=t)

    print(result.fit_report())

    # 将拟合结果保存到原文件中（如果需要）
    if isReplace:
        np.savetxt(fname, result.best_fit[::N], fmt='%.10f')

    # --- 画图 ---
    plt.figure(figsize=(8, 5))
    plt.plot(t, y, 'o', markersize=3, label="y")
    plt.plot(t, result.best_fit, '-', label="fit")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Signal Template Fit (tempfunc2)")
    plt.legend()
    plt.grid(True)
    plt.show()
    
    return result

_ = QApplication(sys.argv)
fname, _ = QFileDialog.getOpenFileName(None, "Open File", "/home/duandy/disk/bolometer/Data/", "Signal Template(*template.txt)")
if len(fname) == 0:
    fname = "/home/duandy/disk/bolometer/Data/RUN33/WTh_CS_WP_ustcBox_1202_fitTemp/data/signaltemplate.txt"

print("Selected file:", fname)
fitTemp(2000, fname, 4, isReplace=True)