from  matplotlib.backends.backend_qt5agg  import  ( NavigationToolbar2QT  as  NavigationToolbar ) 
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time
import math
import random
import sys
import os
import scipy.stats
import layout2 as lay2
#from win_lay2 import *
#import win_lay2
class _benchmark_select(lay2.Ui_MainWindow):
    wl,pp,sp,th=0,0,0,0.0
    bl,bl_rms,amp,rt,dt,posi=0.0,0.0,0.0,0,0,0
    def __init__(self):
        super(_benchmark_select, self).__init__()
        self.setupUi(self)
        #init
        self.initState()
        #process
        self.pushButton_next.clicked.connect(self.from_next)
        self.pushButton_yes.clicked.connect(self._get_benchmark)

    def initState(self):
        self.center()
        self.commandLinkButton_next.setEnabled(False)
        self.pushButton_get_benchmark.setEnabled(False)
        file_para = open("paralist.txt",'r')
        self.FilePath = file_para.readline().split('\n')[0]
        self.FileName = file_para.readline().split('\n')[0]
        self.wl = int(file_para.readline().split('\n')[0])
        self.fs = int(file_para.readline().split('\n')[0])
        self.peakpos = int(file_para.readline().split('\n')[0])
        self.bl_s = int(file_para.readline().split('\n')[0])
        self.bl_e = int(file_para.readline().split('\n')[0])
        file_para.close()
        print([self.FilePath, self.FileName, self.wl, self.fs, self.peakpos, self.bl_s, self.bl_e])
        self.benchNo = 0
        print("Hello, let's start!")
        self.opfile = open(self.FilePath+self.FileName,"rb")
        self.benchmarkfile = open(self.FilePath+'data/benchmark.txt','r')
        line = self.benchmarkfile.readline()
        self.filedata = line.split('\n')
        self._get_pulse()
        return
    def closewin(self):
        self.close()
    def center(self, screenNum=0):
        '''多屏居中支持'''
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.normalGeometry2 = QRect((screen.width() - size.width())//2 + screen.left(),
                                     (screen.height() - size.height())//2, size.width(), size.height())
        self.setGeometry((screen.width() - size.width())//2 + screen.left(),
                         (screen.height() - size.height())//2, size.width(), size.height())

    def _get_pulse(self):
        t = []
        x = []
        num = 0
        for num in range(0,self.wl):
            t.append(num)
        self.arr_t = np.array(t)
        self.opfile.seek(4*(int(self.filedata[0])-self.peakpos),0)
        txt = self.opfile.read(self.wl*4)
        self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
        self.arr_x = (self.arr_x - self.bl)#/self.amp
        self.amp = np.max(self.arr_x)# - self.bl
        self.bl_RMS=math.sqrt(np.sum(np.power(self.arr_x[self.bl_s:self.bl_e],2)))*1.0/(self.bl_e-self.bl_s)
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x/self.amp, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return
    def from_next(self):
        line = self.benchmarkfile.readline()
        if not line:
            print(self.benchmarkpulse)
            np.savetxt(self.FilePath+'data/benchmarkpulse.txt', self.benchmarkpulse/self.bm_amp, fmt='%f',delimiter=",")
            self.pushButton_next.setEnabled(False)
            self.pushButton_yes.setEnabled(False)
            self.commandLinkButton_next.setEnabled(True)
            self.MplWidget.msgwarning3()
        else:
            self.filedata = line.split('\n')
            self._get_pulse()
            self.pushButton_yes.setEnabled(True)
        return
    def _get_benchmark(self):
        self.benchNo += 1
        if self.benchNo == 1:
            self.benchmarkpulse = self.arr_x
            self.bm_amp = np.max(self.benchmarkpulse)
        else:
            Rself = np.correlate(self.benchmarkpulse/self.bm_amp, self.benchmarkpulse/self.bm_amp, mode = 'full')
            pos1=np.argmax(Rself)
            print(pos1)
            Rcross = np.correlate(self.benchmarkpulse/self.bm_amp, self.arr_x/self.amp, mode = 'full')
            pos2=np.argmax(Rcross)
            print(pos2)
            x = []
            self.opfile.seek(4*(int(self.filedata[0])-self.peakpos-pos1+pos2),0)
            txt = self.opfile.read(self.wl*4)
            self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
            self.arr_x = (self.arr_x - self.bl)#/self.amp
            self.amp = np.max(self.arr_x)# - self.bl
            #self.corrcoef = scipy.stats.spearmanr(self.benchmarkpulse, self.arr_x)[0]
            #self.benchmarkpulse = (self.benchmarkpulse*(self.benchNo-1)+self.arr_x)/self.benchNo
            self.benchmarkpulse = self.benchmarkpulse+self.arr_x
            self.bm_amp = np.max(self.benchmarkpulse)# - self.bl
        self.MplWidget_2.canvas.axes.clear () 
        self.MplWidget_2.canvas.axes.plot(self.arr_t, self.benchmarkpulse/self.bm_amp, label='Benchmark pulse')
        self.MplWidget_2.defcanvas()
        self.MplWidget_2.canvas.draw()
        self.pushButton_yes.setEnabled(False)
        return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = _benchmark_select()
    window.show()
    sys.exit(app.exec_())

