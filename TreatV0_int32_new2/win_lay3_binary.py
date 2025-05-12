from  matplotlib.backends.backend_qt5agg  import  ( NavigationToolbar2QT  as  NavigationToolbar ) 
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
#from PyQt5.QtWidgets import QMessageBox
import time
import math
import random
import sys
import os
import scipy.stats
import uproot
import layout3 as lay3
import time
class _benchmark_corr(lay3.Ui_MainWindow):
    wl,pp,sp,th=0,0,0,0.0
    bl,bl_rms,amp,rt,dt,posi=0.0,0.0,0.0,0,0,0
    def __init__(self,FilePath='/Users/zhaokangkang/WorkArea/Bolometer/Data/',FileName='20180419_19h56.BIN4.root'):
        self.FilePath = FilePath
        self.FileName = FileName
        super(_benchmark_corr, self).__init__()
        self.setupUi(self)
        #init
        self.initState()
        #process
        self.pushButton_search.clicked.connect(self._search_signal)
        self.pushButton_defaultcut.clicked.connect(self._default_cut)
        self.pushButton_cut.clicked.connect(self._mannual_cut)
        self.pushButton_start.clicked.connect(self._get_start)
        self.pushButton_next.clicked.connect(self.from_next)
        self.pushButton_yes.clicked.connect(self._get_template)
        self.pushButton_end.clicked.connect(self._end_template)

    def initState(self):
        self.center()
        self.commandLinkButton_next.setEnabled(False)
        file_para = open("paralist.txt",'r')
        self.FilePath = file_para.readline().split('\n')[0]
        self.FileName = file_para.readline().split('\n')[0]
        self.wl = int(file_para.readline().split('\n')[0])
        self.fs = int(file_para.readline().split('\n')[0])
        self.peakpos = int(file_para.readline().split('\n')[0])
        self.bl_s = int(file_para.readline().split('\n')[0])
        self.bl_e = int(file_para.readline().split('\n')[0])
        file_para.close()
        self.benchNo = 0
        self.step = self.wl
        print("Hello, let's start!")
        self.opfile = open(self.FilePath+self.FileName,"rb")
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
    def _default_cut(self):
        with uproot.open(self.FilePath+"data/SearchSignalEvent.root:tree1") as searchtree:
            events = searchtree.arrays(["Amplitude","Baseline","Bl_RMS","Max_position","Rise_time","Decay_time","Corrcoef","std_dev1","std_dev2","std_dev3","std_dev4","std_dev5","std_dev6","std_dev7","std_dev8","std_dev9","std_dev10"],library="np")
            defaultnum = 400
            b=events["Corrcoef"].argsort()[(0-defaultnum):]
            self.textBrowser_bl.setText(str(defaultnum))
            self.doubleSpinBox_dtmax.setValue(np.max(events["Decay_time"][b]))
            self.doubleSpinBox_dtmin.setValue(np.min(events["Decay_time"][b]))
            self.doubleSpinBox_ampmax.setValue(np.max(events["Amplitude"][b]))
            self.doubleSpinBox_ampmin.setValue(np.min(events["Amplitude"][b]))
            self.doubleSpinBox_blRMSmax.setValue(100)
            self.doubleSpinBox_blRMSmin.setValue(0)
            #self.doubleSpinBox_blRMSmax.setValue(np.max(events["Bl_RMS"][b]))
            #self.doubleSpinBox_blRMSmin.setValue(np.min(events["Bl_RMS"][b]))
            self.doubleSpinBox_rtmax.setValue(np.max(events["Rise_time"][b]))
            self.doubleSpinBox_rtmin.setValue(np.min(events["Rise_time"][b]))
            self.doubleSpinBox_coefmax.setValue(np.max(events["Corrcoef"][b]))
            self.doubleSpinBox_coefmin.setValue(np.min(events["Corrcoef"][b]))
        return
    def _mannual_cut(self):
        dtmax = self.doubleSpinBox_dtmax.value()
        dtmin = self.doubleSpinBox_dtmin.value()
        ampmax = self.doubleSpinBox_ampmax.value()
        ampmin = self.doubleSpinBox_ampmin.value()
        blRMSmax = self.doubleSpinBox_blRMSmax.value()
        blRMSmin = self.doubleSpinBox_blRMSmin.value()
        rtmax = self.doubleSpinBox_rtmax.value()
        rtmin = self.doubleSpinBox_rtmin.value()
        coefmax = self.doubleSpinBox_coefmax.value()
        coefmin = self.doubleSpinBox_coefmin.value()
        with uproot.open(self.FilePath+"data/SearchSignalEvent.root:tree1") as searchtree:
            events = searchtree.arrays(["Amplitude","Baseline","Bl_RMS","Max_position","Rise_time","Decay_time","Corrcoef","std_dev1","std_dev2","std_dev3","std_dev4","std_dev5","std_dev6","std_dev7","std_dev8","std_dev9","std_dev10"],library="np")
            length = len(events["Max_position"])
            num = 0
            signal_template = []
            if len(events["std_dev5"]) > 2000:
                c = events["std_dev5"].argsort()[:2000]
            else:
                c = events["std_dev5"].argsort()
            self.std_max = np.max(events["std_dev5"][c])
            self.std_min = np.min(events["std_dev5"][c])
            '''
            '''
            self.std_interval = self.std_max-self.std_min
            print(self.std_interval)
            for k in range(0, length):
                if events["Decay_time"][k] > dtmax:
                    continue
                if events["Decay_time"][k] < dtmin:
                    continue
                if events["Rise_time"][k] > rtmax:
                    continue
                if events["Rise_time"][k] < rtmin:
                    continue
                if events["Amplitude"][k] > ampmax:
                    continue
                if events["Amplitude"][k] < ampmin:
                    continue
                if events["Corrcoef"][k] < coefmin:
                    continue
                if events["Bl_RMS"][k] < blRMSmin:
                    continue
                if events["Bl_RMS"][k] > blRMSmax:
                    continue
                '''
                if (events["std_dev1"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev1"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev2"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev2"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev3"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev3"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev4"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev4"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev5"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev5"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev6"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev6"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev7"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev7"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev8"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev8"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev9"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev9"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                if (events["std_dev10"][k]-self.std_min)*100/(self.std_interval) > blRMSmax:
                    continue
                if (events["std_dev10"][k]-self.std_min)*100/(self.std_interval) < blRMSmin:
                    continue
                '''
                num+=1
                signal_template.append(events["Max_position"][k])
        arr_template = np.array(signal_template)
        np.savetxt(self.FilePath+'data/signalcandidate.txt', arr_template, fmt='%d',delimiter=",")
        self.textBrowser_bl.setText(str(num))
        return
    def _search_signal(self):
        # 使用示例
        bar = ProgressBar() # 初始化 ProcessBar实例
        tot = os.path.getsize(self.FilePath+self.FileName)//4
        total_number=0      # 总任务数
        task_id=0           # 子任务序号
        tot_num = tot//self.step
        print(tot_num//2000)
        self.benchmarkpulse = np.loadtxt(self.FilePath+'data/benchmarkpulse.txt',dtype=float)
        self.benchmarkpulse = self.benchmarkpulse/np.max(self.benchmarkpulse)
        print(self.benchmarkpulse)
        Rself = np.correlate(self.benchmarkpulse, self.benchmarkpulse, mode = 'full')
        pos1=np.argmax(Rself)
        a_amp      = [] 
        a_bl       = [] 
        a_bl_RMS   = [] 
        a_maxp     = [] 
        a_rt       = [] 
        a_dt       = [] 
        a_corrcoef = []
        a_std_dev  = []
        for i in range(10):      # 创建一个5行的列表（行）
            a_std_dev.append([])
        for k in range(2, tot_num-1):
            if k%2000 == 0:
                print(k//2000)
            if (k*100)%tot_num ==0:
                bar.setValue(str(task_id),str(total_number),(k*100)//tot_num) # 刷新进度条
                QApplication.processEvents()  # 实时刷新显示
            x = []
            num = 0
            self.opfile.seek(4*self.step*k,0)
            txt = self.opfile.read(self.step*4)
            arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            maxp = np.argmax(arr_x)+self.step*k
            del(x)
            x = []
            num = 0
            self.opfile.seek(4*(maxp-self.peakpos),0)
            txt = self.opfile.read(self.wl*4)
            arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            bl=np.sum(arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
            amp = np.max(arr_x) - bl
            arr_x = (arr_x - bl)/amp
            if np.argmax(arr_x) != self.peakpos:
                continue
            bl_RMS=math.sqrt(np.sum(np.power(arr_x[self.bl_s:self.bl_e],2)))*1.0/(self.bl_e-self.bl_s)
            corrcoef = np.corrcoef(self.benchmarkpulse, arr_x)[0,1]
            if corrcoef < 0.99:
                continue
            corrcoef = (corrcoef-0.99)/0.01
            '''
            corrcoef = scipy.stats.spearmanr(self.benchmarkpulse, arr_x)[0]
            if corrcoef < 0.95:
                continue
            corrcoef = (corrcoef-0.95)/0.05
            '''
            rt=0
            dt=0
            for i in reversed(arr_x[:self.peakpos]):
                if i < 0.9:
                    if i < 0.1:
                        break
                    rt+=1
            for i in arr_x[self.peakpos:]:
                if i < 0.9:
                    if i < 0.3:
                        break
                    dt+=1
            a_amp.append(amp) 
            a_bl.append(bl)  
            a_bl_RMS.append(bl_RMS)  
            a_maxp.append(maxp)  
            a_rt.append(rt)  
            a_dt.append(dt)  
            a_corrcoef.append(corrcoef)
            for i in range(10):      
                a_std_dev[i].append(math.sqrt(np.sum(np.power((self.benchmarkpulse-arr_x)[i*self.wl//10:(i+1)*self.wl//10],2))))
        arr_amp      = np.array(a_amp)
        arr_bl       = np.array(a_bl)
        arr_bl_RMS   = np.array(a_bl_RMS)  
        arr_maxp     = np.array(a_maxp)  
        arr_rt       = np.array(a_rt)  
        arr_dt       = np.array(a_dt)  
        arr_std_dev  = np.array(a_std_dev)
        print(arr_maxp)
        print(arr_dt)
        arr_corrcoef = np.array(a_corrcoef)
        eventfile = uproot.recreate(self.FilePath+"data/SearchSignalEvent.root")
        eventfile["tree1"] = {"Amplitude": arr_amp, "Baseline":arr_bl, "Bl_RMS":arr_bl_RMS, "Max_position":arr_maxp, "Rise_time":arr_rt, "Decay_time":arr_dt, "Corrcoef":arr_corrcoef,"std_dev1":arr_std_dev[0],"std_dev2":arr_std_dev[1],"std_dev3":arr_std_dev[2],"std_dev4":arr_std_dev[3],"std_dev5":arr_std_dev[4],"std_dev6":arr_std_dev[5],"std_dev7":arr_std_dev[6],"std_dev8":arr_std_dev[7],"std_dev9":arr_std_dev[8],"std_dev10":arr_std_dev[9]}
        bar.close()  # 关闭进度条
        print("Hello\n")
        return
    def _get_start(self):
        self.benchNo = 0
        self.signalcandidate = open(self.FilePath+'data/signalcandidate.txt','r')
        line = self.signalcandidate.readline()
        self.filedata = line.split('\n')
        self.drawnum = 0
        self._get_pulse()
        self.pushButton_next.setEnabled(True)
        self.pushButton_yes.setEnabled(True)
        return
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
        if self.drawnum == 0:
            self.MplWidget.canvas.axes.clear() 
        if self.drawnum > 5:
            self.drawnum = 0
            self.MplWidget.canvas.axes.clear() 
        self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
        self.arr_x = (self.arr_x - self.bl)
        self.amp = np.max(self.arr_x)
        self.bl_RMS=math.sqrt(np.sum(np.power(self.arr_x[self.bl_s:self.bl_e],2)))*1.0/(self.bl_e-self.bl_s)
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x/self.amp, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        self.drawnum += 1
        return
    def from_next(self):
        line = self.signalcandidate.readline()
        if not line:
            self._end_template()
            return
        else:
            self.filedata = line.split('\n')
            self._get_pulse()
            self.pushButton_yes.setEnabled(True)
        return
    def _end_template(self):
        self.MplWidget.canvas.axes.clear() 
        self.MplWidget.canvas.axes.plot(self.arr_t, self.signaltemplate/self.st_amp, label='Signal template')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        print(self.signaltemplate)
        np.savetxt(self.FilePath+'data/signaltemplate.txt', self.signaltemplate/self.st_amp, fmt='%f',delimiter=",")
        self.pushButton_next.setEnabled(False)
        self.pushButton_yes.setEnabled(False)
        self.commandLinkButton_next.setEnabled(True)
        self.MplWidget.msgwarning3()
        return
    def _get_template(self):
        self.benchNo += 1
        if self.benchNo == 1:
            self.signaltemplate = self.arr_x
            self.pushButton_end.setEnabled(True)
        else:
            Rself = np.correlate(self.signaltemplate/self.st_amp, self.signaltemplate/self.st_amp, mode = 'full')
            pos1=np.argmax(Rself)
            print(pos1)
            Rcross = np.correlate(self.signaltemplate/self.st_amp, self.arr_x/self.amp, mode = 'full')
            pos2=np.argmax(Rcross)
            print(pos2)
            x = []
            self.opfile.seek(4*(int(self.filedata[0])-self.peakpos-pos1+pos2),0)
            txt = self.opfile.read(self.wl*4)
            self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            self.bl=np.sum(self.arr_x[self.bl_s:self.bl_e])*1.0/(self.bl_e-self.bl_s)
            self.arr_x = (self.arr_x - self.bl)
            self.amp = np.max(self.arr_x)
            #self.arr_x = (self.arr_x - self.bl)/self.amp
            #self.signaltemplate = (self.signaltemplate*(self.benchNo-1)+self.arr_x)/self.benchNo
            self.signaltemplate = (self.signaltemplate+self.arr_x)
        self.st_amp = np.max(self.signaltemplate)
        self.from_next()
        #self.pushButton_yes.setEnabled(False)
        return

class ProgressBar(QDialog):
    def __init__(self,  parent=None):
        super(ProgressBar, self).__init__(parent)
        # Qdialog窗体的设置
        self.resize(250,32) # QDialog窗的大小
        # 创建并设置 QProcessbar
        self.progressBar = QProgressBar(self) # 创建
        self.progressBar.setMinimum(0)      #设置进度条最小值
        self.progressBar.setMaximum(100)    #设置进度条最大值
        self.progressBar.setValue(0)        #进度条初始值为0
        self.progressBar.setGeometry(QRect(10, 5, 220, 27)) # 设置进度条在 QDialog 中的位置 [左，上，右，下]
        self.show()
        return
    '''
    task_number和 total_task_number都为 0 时，不显示当前进行的任务情况
    task_number<total_task_number 都为整数，错误的设置将出现错误显示，暂未设置报错警告
    '''
    def setValue(self,task_number,total_task_number, value): # 设置总任务进度和子任务进度
        if task_number=='0' and total_task_number=='0':
            self.setWindowTitle(self.tr('正在处理中'))
        else:
            label = "正在处理：" + "第" + str(task_number) + "/" + str(total_task_number)+'个任务'
            self.setWindowTitle(self.tr(label)) # 顶部的标题
        self.progressBar.setValue(value)
        self.progressBar.update()
        return
'''
        #bar=pyqtbar() # 创建实例
        #bar.set_value(task_id,total_number,(k*100)//tot_num) # 刷新进度条
        #bar.close # 关闭 bar 和 app
class pyqtbar():
    def __init__(self):
        self.app = QApplication(sys.argv) # 打开系统 app
        self.progressbar = ProgressBar() # 初始化 ProcessBar实例
        return
    def set_value(self,task_number,total_task_number,i):
        self.progressbar.setValue(str(task_number), str(total_task_number),i+1)  # 更新进度条的值
        QApplication.processEvents()  # 实时刷新显示
        return
    def close(self):
        self.progressbar.close()  # 关闭进度条
        self.app.exit() # 关闭系统 app
        return
'''
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = _benchmark_corr()
    window.show()
    sys.exit(app.exec_())
'''
self.childWindowExist = True
self.child_window = Child()
self.child_window.window_show("Exeuting!")
self.child_window.show()
if self.childWindowExist:
    self.child_window.close()
    self.childWindowExist = False
class Child(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 300)
        self.setWindowTitle("Sub window")
    def window_show(self, text):
        # 展示内容
        self.label = QLabel(text)
        layout = QGridLayout()
        layout.addWidget(self.label, 0, 0)
        self.setLayout(layout)
'''

