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
import shutil
import layout1 as lay1
class _pulse_inspect(lay1.Ui_MainWindow):
    FilePath,FileName=0,0
    wl,pp,sp,th=0,0,0,0.0
    bl,bl_rms,amp,rt,dt,posi=0.0,0.0,0.0,0,0,0
    _peakpos = 0.0
    _export_para = 0
    def __init__(self):
        super(_pulse_inspect, self).__init__()
        self.setupUi(self)
        #init
        self.initState()
        self.Paralist = [7]
        #process
        self.pushButton_browser.clicked.connect(self._browserfile)
        self.pushButton_inspect.clicked.connect(self.from_start)
        self.pushButton_next.clicked.connect(self.from_next)
        self.pushButton_align.clicked.connect(self._align)
        self.pushButton_zero.clicked.connect(self._zero)
        self.radioButton_2.toggled.connect(self._trigger_set)
        self.radioButton_2.toggled.connect(self._no_trigger_set)
        self.pushButton_select.clicked.connect(self._benchmark_yes)

    def initState(self):
        self.center()
        self.wl = self.spinBox_wl.value()
        self.startp = 0
        self.spinBox_start.setValue(self.startp)
        print("Hello, let's start!")
        self.FilePath=str(self.lineEdit_filepath.text())
        self.FileName=str(self.lineEdit_filename.text())
        print(self.FilePath+self.FileName)
        self._openfile()
        return
    def closewin(self):
        self.close()
    def center(self, screenNum=0):
        '''多屏居中支持'''
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.normalGeometry2 = QRect((screen.width() - size.width()) // 2 + screen.left(),
                                     (screen.height() - size.height()) // 2, size.width(), size.height())
        self.setGeometry((screen.width() - size.width()) // 2 + screen.left(),
                         (screen.height() - size.height()) // 2, size.width(), size.height())

    def _openfile(self):
        self.opfile = open(self.FilePath+self.FileName,"rb")
        t = []
        x = []
        num = 0
        for num in range(0,self.wl):
            t.append(num)
        self.arr_t = np.array(t)
        self.opfile.seek(4*self.startp,0)
        txt = self.opfile.read(self.wl*4)
        self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.MplWidget.canvas.axes.clear () 
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return
    def _browserfile(self):
        fname = None
        #self指向自身，"Open File"为文件名，"./"为当前路径，最后为文件类型筛选器
        #fname,ftype = QFileDialog.getOpenFileName(self, "Open File", "~/")#, "root file(*.root)")#如果添加一个内容则需要加两个分号
        fname,ftype = QFileDialog.getOpenFileName(self, "Open File", "/mnt/d/RUNs_data_analysis/RUN2410/Converted_Data/tdms/BKG_RUN2410_2")#, "root file(*.root)")#如果添加一个内容则需要加两个分号
        if len(fname) == 0:
            print("fname")
            return
        print(fname)
        print(ftype)
        self.FilePath=str(fname.rsplit("/",1)[0])+"/"
        self.FileName=str(fname.rsplit("/",1)[1])
        self.lineEdit_filepath.setText(self.FilePath)
        self.lineEdit_filename.setText(self.FileName)
        print(self.FilePath+self.FileName)
        self.initState()
        return

    def from_start(self):
        #self.initState()
        self.startp = self.spinBox_start.value()
        self.wl = self.spinBox_wl.value()
        t = []
        x = []
        num = 0
        for num in range(0,self.wl):
            t.append(num)
        self.arr_t = np.array(t)
        self.opfile.seek(4*self.startp,0)
        txt = self.opfile.read(self.wl*4)
        self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.MplWidget.canvas.axes.clear () 
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return
    def from_next(self):
        if self.radioButton_2.isChecked() == True:
            print("Hello, next!")
            self.wl = self.spinBox_wl.value()
            self.startp = self.startp+self.wl
            self.spinBox_start.setValue(self.startp)
            t = []
            num = 0
            for num in range(0,self.wl):
                t.append(num)
            self.arr_t = np.array(t)
            x = []
            self.opfile.seek(4*self.startp,0)
            txt = self.opfile.read(self.wl*4)
            self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            self.MplWidget.canvas.axes.clear () 
            self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
            self.MplWidget.defcanvas()
            self.MplWidget.canvas.draw()
        else:
            self._next_triggered()
        return
    def _align(self):
        self.peakp = self.spinBox_peakp.value()
        self.wl = self.spinBox_wl.value()
        self.startp = self.spinBox_start.value()
        print(self.startp)
        self._posi = self.startp + np.argmax(self.arr_x)
        self.startp = self._posi-self.peakp
        self.spinBox_start.setValue(self.startp)
        print(self.startp)
        self.textBrowser_posi.setText(str(self._posi))
        x = []
        self.opfile.seek(4*(self._posi-self.peakp),0)
        txt = self.opfile.read(self.wl*4)
        self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.MplWidget.canvas.axes.clear () 
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return

    def _zero(self):
        self._align()
        self.bl_s = self.spinBox_bls.value()
        self.bl_e = self.spinBox_ble.value()
        if self.bl_e-self.bl_s <= 0:
            self.MplWidget.msgwarning1()
            return
        self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
        self.amp = self.arr_x[self.peakp] - self.bl
        self.bl_RMS=math.sqrt(np.sum(np.power(self.arr_x[self.bl_s:self.bl_e]-self.bl,2)))*1.0/(self.bl_e-self.bl_s)
        self.rt=0
        self.dt=0
        for i in reversed(self.arr_x[:self.peakp]):
            if i < 0.9*self.amp+self.bl:
                if i < 0.1*self.amp+self.bl:
                    break
                self.rt+=1
        for i in self.arr_x[self.peakp:]:
            if i < 0.9*self.amp+self.bl:
                if i < 0.3*self.amp+self.bl:
                    break
                self.dt+=1
        self.arr_x = self.arr_x - self.bl
        self.MplWidget.canvas.axes.clear() 
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        self.textBrowser_bl.setText(str(float('%.2f' % self.bl)))
        self.textBrowser_blRMS.setText(str(float('%.4f' % self.bl_RMS)))
        self.textBrowser_amp.setText(str(float('%.2f' % self.amp)))
        self.textBrowser_rt.setText(str(self.rt))
        self.textBrowser_dt.setText(str(self.dt))
        print("Hello, benchmark!")
        return
    def _next_triggered(self):
        #从交互框中获取触发阈值及事例计算参数
        self.th = self.doubleSpinBox_th.value()
        if self.th == 0.00:
            self.MplWidget.msgwarning2()
            return
        self.bl_s = self.spinBox_bls.value()
        self.bl_e = self.spinBox_ble.value()
        self.peakp = self.spinBox_peakp.value()
        self.wl = self.spinBox_wl.value()
        self.startp = self.spinBox_start.value()
        t = []
        num = 0
        for num in range(0,self.wl):
            t.append(num)
        self.arr_t = np.array(t)
        cycle_i = 0
        while True:
            cycle_i = cycle_i + 1
            self.startp = self.startp + self.wl//2
            x = []
            self.opfile.seek(4*self.startp,0)
            txt = self.opfile.read(self.wl*4)
            self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            self._posi = self.startp + np.argmax(self.arr_x)
            self.startp = self._posi-self.peakp
            del x
            x = []
            self.opfile.seek(4*(self._posi-self.peakp),0)
            txt = self.opfile.read(self.wl*4)
            self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
            self.amp = self.arr_x[self.peakp] - self.bl
            self.bl_RMS=math.sqrt(np.sum(np.power(self.arr_x[self.bl_s:self.bl_e]-self.bl,2)))*1.0/(self.bl_e-self.bl_s)
            if self.amp > self.th*self.bl_RMS:
                print(self.peakp)
                print(self.amp)
                print(self.bl)
                self.rt=0
                self.dt=0
                for i in reversed(self.arr_x[:self.peakp]):
                    if i < 0.9*self.amp+self.bl:
                        if i < 0.1*self.amp+self.bl:
                            break
                        self.rt+=1
                for i in self.arr_x[self.peakp:]:
                    if i < 0.9*self.amp+self.bl:
                        if i < 0.3*self.amp+self.bl:
                            break
                        self.dt+=1
                self.arr_x = self.arr_x - self.bl
                self.MplWidget.canvas.axes.clear () 
                self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
                self.MplWidget.defcanvas()
                self.MplWidget.canvas.draw()
                self.spinBox_start.setValue(self.startp)
                self.textBrowser_posi.setText(str(self._posi))
                self.textBrowser_bl.setText(str(float('%.2f' % self.bl)))
                self.textBrowser_blRMS.setText(str(float('%.4f' % self.bl_RMS)))
                self.textBrowser_amp.setText(str(float('%.2f' % self.amp)))
                self.textBrowser_rt.setText(str(self.rt))
                self.textBrowser_dt.setText(str(self.dt))
                self._peakpos = self.startp + self.peakp
                break
            if cycle_i == 50:
                self.MplWidget.canvas.axes.clear () 
                self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
                self.MplWidget.defcanvas()
                self.MplWidget.canvas.draw()
                self.spinBox_start.setValue(self.startp)
                self.textBrowser_posi.setText(str(self._peakpos))
                break
        print("Hello, trigger next!")
        return
    def _trigger_set(self):
        if self.radioButton.isChecked() == False:
            return
        self.bl_s = self.spinBox_bls.value()
        self.bl_e = self.spinBox_ble.value()
        if self.bl_e-self.bl_s <= 0:
            self.radioButton_2.setChecked(True)
            self.MplWidget.msgwarning1()
            return
        self.spinBox_peakp.setEnabled(False)
        self.spinBox_bls.setEnabled(False)
        self.spinBox_ble.setEnabled(False)
        self.th = self.doubleSpinBox_th.value()
        if self.th == 0.00:
            self.MplWidget.msgwarning2()
            return
    def _no_trigger_set(self):
        if self.radioButton_2.isChecked() == True:
            self.spinBox_peakp.setEnabled(True)
            self.spinBox_bls.setEnabled(True)
            self.spinBox_ble.setEnabled(True)
        return
    def _benchmark_yes(self):
        if self._export_para == 0:
            if not os.path.exists(self.FilePath+'data'):
                os.mkdir(self.FilePath+'data')
            self.FilePath=str(self.lineEdit_filepath.text())
            self.FileName=str(self.lineEdit_filename.text())
            self.wl = self.spinBox_wl.value()
            self.freq = self.spinBox_freq.value()
            self.peakp = self.spinBox_peakp.value()
            self.bl_s = self.spinBox_bls.value()
            self.bl_e = self.spinBox_ble.value()
            self.Paralist = [self.FilePath, self.FileName, self.wl, self.freq ,self.peakp, self.bl_s, self.bl_e]
            self.commandLinkButton.setEnabled(True)
            file_para = open("paralist.txt","w")
            for line in self.Paralist:
                file_para.write(str(line)+'\n')
            file_para.close()
            shutil.copy("paralist.txt",self.FilePath+'data/')
            self._export_para = 1
            benchmarkfile = open(self.FilePath+"data/benchmark.txt","w")
            print("Hello, benchmark!")
            benchmarkfile.write(str(self._peakpos))
            benchmarkfile.write("\n")
            benchmarkfile.close()
        else:
            benchmarkfile = open(self.FilePath+"data/benchmark.txt","a+")
            benchmarkfile.write(str(self._peakpos))
            benchmarkfile.write("\n")
            benchmarkfile.close()
        return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = _pulse_inspect()
    window.show()
    sys.exit(app.exec_())

