from  matplotlib.backends.backend_qt5agg  import  ( NavigationToolbar2QT  as  NavigationToolbar ) 
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
#from PyQt5.QtWidgets import QMessageBox
import math
import random
import sys
import os
import scipy.stats
import uproot
import layout4 as lay4
class _noisepowerspectrum(lay4.Ui_MainWindow):
    wl,pp,sp,th=0,0,0,0.0
    bl,bl_rms,amp,rt,dt,posi=0.0,0.0,0.0,0,0,0
    def __init__(self,FilePath='/Users/zhaokangkang/WorkArea/Bolometer/Data/',FileName='20180419_19h56.BIN4.root'):
        self.FilePath = FilePath
        self.FileName = FileName
        super(_noisepowerspectrum, self).__init__()
        self.setupUi(self)
        #init
        self.initState()
        #process
        self.pushButton_search.clicked.connect(self._search_noise)
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
        self.step = self.wl#int(self.wl/2)
        print("Hello, let's start!")
        self.opfile = open(self.FilePath+self.FileName,"rb")
        return
    def closewin(self):
        #QCoreApplication.instance().quit()
        self.close()
    def center(self, screenNum=0):
        '''多屏居中支持'''
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.normalGeometry2 = QRect((screen.width() - size.width())//2 + screen.left(),
                                     (screen.height() - size.height())//2, size.width(), size.height())
        self.setGeometry((screen.width() - size.width())//2 + screen.left(),
                         (screen.height() - size.height())//2, size.width(), size.height())
    def _search_noise(self):
        # 使用示例
        bar = ProgressBar() # 初始化 ProcessBar实例
        tot = os.path.getsize(self.FilePath+self.FileName)//4
        total_number=0 # 总任务数
        task_id=0 # 子任务序号
        tot_num = tot//self.step
        a_bl= []
        a_std = []
        a_startp = []
        a_vpp = []
        a_pvalue = []
        print(tot_num//2000)
        for k in range(0, tot_num-2):
            if k%2000 == 0:
                print(k//2000)
            if (k*100)%tot_num == 0:
                bar.setValue(str(task_id),str(total_number),(k*100)//tot_num) # 刷新进度条
                QApplication.processEvents()  # 实时刷新显示
            x = []
            num = 0
            self.opfile.seek(4*self.step*k,0)
            txt = self.opfile.read(self.wl*4)
            arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            startp = self.step*k
            bl  = np.mean(arr_x)
            std = np.std(arr_x)
            vpp = np.max(arr_x)-np.min(arr_x)
            dstatistic, pvalue = scipy.stats.kstest(arr_x, 'norm', (bl, std))
            #if vpp > 5*std:
            #    continue
            if pvalue == 0:
                continue
            if std == 0:
                continue
            a_bl.append(bl)  
            a_std.append(std)  
            a_startp.append(startp)  
            a_vpp.append(vpp)  
            a_pvalue.append(pvalue)  
        arr_startp = np.array(a_startp)
        arr_bl     = np.array(a_bl)
        arr_std    = np.array(a_std)  
        arr_pvalue = np.array(a_pvalue)  
        arr_vpp    = np.array(a_vpp)  
        eventfile = uproot.recreate(self.FilePath+"data/SearchNoiseEvent.root")
        eventfile["tree1"] = {"Startpos": arr_startp, "Baseline":arr_bl, "Bl_RMS":arr_std, "VPP":arr_vpp, "Pvalue":arr_pvalue}
        bar.close()  # 关闭进度条
        print("Hello\n")
        return
    def _default_cut(self):
        with uproot.open(self.FilePath+"data/SearchNoiseEvent.root:tree1") as searchtree:
            events = searchtree.arrays(["Startpos","Baseline","Bl_RMS","VPP","Pvalue"],library="np")
            defaultnum = 600
            b=events["Bl_RMS"].argsort()[:defaultnum]
            np.savetxt(self.FilePath+'data/noisecandidate.txt', events["Startpos"][b], fmt='%d',delimiter=",")
            self.textBrowser_bl.setText(str(defaultnum))
            self.doubleSpinBox_blmax.setValue(np.max(events["Baseline"][b]))
            self.doubleSpinBox_blmin.setValue(np.min(events["Baseline"][b]))
            self.doubleSpinBox_ppmax.setValue(np.max(events["VPP"][b]))
            self.doubleSpinBox_ppmin.setValue(np.min(events["VPP"][b]))
            self.doubleSpinBox_blRMSmax.setValue(np.max(events["Bl_RMS"][b]))
            self.doubleSpinBox_blRMSmin.setValue(np.min(events["Bl_RMS"][b]))
        return
    def _mannual_cut(self):
        ppmax = self.doubleSpinBox_ppmax.value()
        ppmin = self.doubleSpinBox_ppmin.value()
        blmax = self.doubleSpinBox_blmax.value()
        blmin = self.doubleSpinBox_blmin.value()
        blRMSmax = self.doubleSpinBox_blRMSmax.value()
        blRMSmin = self.doubleSpinBox_blRMSmin.value()
        with uproot.open(self.FilePath+"data/SearchNoiseEvent.root:tree1") as searchtree:
            events = searchtree.arrays(["Startpos","Baseline","Bl_RMS","VPP","Pvalue"],library="np")
            length = len(events["Startpos"])
            num = 0
            noise_template = []
            for k in range(0, length):
                if events["VPP"][k] > ppmax:
                    continue
                if events["VPP"][k] < ppmin:
                    continue
                if events["Baseline"][k] > blmax:
                    continue
                if events["Baseline"][k] < blmin:
                    continue
                if events["Bl_RMS"][k] < blRMSmin:
                    continue
                if events["Bl_RMS"][k] > blRMSmax:
                    continue
                num+=1
                noise_template.append(events["Startpos"][k])
        arr_template = np.array(noise_template)
        np.savetxt(self.FilePath+'data/noisecandidate.txt', arr_template, fmt='%d',delimiter=",")
        self.textBrowser_bl.setText(str(num))
        return
    def _get_start(self):
        self.MplWidget.canvas.axes.clear() 
        self.noisecandidate = open(self.FilePath+'data/noisecandidate.txt','r')
        line = self.noisecandidate.readline()
        self.filedata = line.split('\n')
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
        self.opfile.seek(4*(int(self.filedata[0])),0)
        txt = self.opfile.read(self.wl*4)
        self.arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.MplWidget.canvas.axes.plot(self.arr_t, self.arr_x, label='Raw signal')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return
    def from_next(self):
        line = self.noisecandidate.readline()
        if not line:
            self._end_template()
            self.pushButton_next.setEnabled(False)
            self.pushButton_yes.setEnabled(False)
            self.MplWidget.msgwarning3()
            return
        else:
            self.filedata = line.split('\n')
            self._get_pulse()
            self.pushButton_yes.setEnabled(True)
        return
    def _end_template(self):
        self.noisecandidate = open(self.FilePath+'data/noisecandidate.txt','r')
        line = self.noisecandidate.readline()
        k = 0
        self.freq = np.fft.fftfreq(self.wl, 1./self.fs)
        print(self.freq)
        self.noise_RMS = 0.0
        while line:
            k += 1
            self.filedata = line.split('\n')
            x = []
            self.opfile.seek(4*(int(self.filedata[0])),0)
            txt = self.opfile.read(self.wl*4)
            arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            diff_noise = np.diff(arr_x)
            Pxx1 = np.real(np.fft.fft(arr_x)*np.fft.fft(arr_x).conjugate())
            Pxx2 = np.real(np.fft.fft(diff_noise)*np.fft.fft(diff_noise).conjugate())
            self.noise_RMS += np.std(arr_x)
            '''
            #return (-Fs//2, +Fs//2)
            [Pxx1,f1] = plt.psd(arr_x,          # 随机信号
                    NFFT=self.wl,               # 每个窗的长度
                    Fs=10000,                   # 采样频率
                    detrend='mean',          # 去掉均值
                    window=np.hanning(self.wl), # 加汉尼窗
                    noverlap = 0, #int(self.wl*3/4),  # 每个窗重叠75%的数据
                    sides='twosided')        # 求双边谱
            '''
            if k == 1:
                self.nps = Pxx1
                self.diff_nps = Pxx2
            else:
                self.nps += Pxx1
                self.diff_nps += Pxx2
            line = self.noisecandidate.readline()
        self.noise_RMS /= k
        self.nps /= k
        self.diff_nps /= k
        print(self.noise_RMS)
        self.MplWidget.canvas.axes.clear()
        self.MplWidget.canvas.axes.set_xlabel('Frequency (Hz)')
        self.MplWidget.canvas.axes.set_ylabel('PSD (ADC^2/Hz)')
        #self.MplWidget.canvas.axes.plot(self.freq[:self.wl//2], self.nps[-self.wl//2:], label='Noise Power Spectrum')
        '''
        self.nps2 = np.zeros(shape=self.wl)
        self.nps2[:self.wl//2]  = self.nps[-self.wl//2:]
        self.nps2[-self.wl//2:] = self.nps[:self.wl//2]
        self.MplWidget.canvas.axes.plot(self.freq[:self.wl//2], self.nps2[:self.wl//2], label='Noise Power Spectrum')
        '''
        self.MplWidget.canvas.axes.plot(self.freq[:self.wl//2], self.nps[:self.wl//2], label='Noise Power Spectrum')
        #self.MplWidget.canvas.axes.plot(self.freq, self.nps, label='Noise Power Spectrum')
        self.MplWidget.canvas.axes.set_yscale('log')
        self.MplWidget.canvas.axes.set_xscale('log')
        self.MplWidget.canvas.draw()
        np.savetxt(self.FilePath+'data/noiseps.txt', self.nps, fmt='%.20f',delimiter=",")
        np.savetxt(self.FilePath+'data/diff_nps.txt', self.diff_nps, fmt='%.20f',delimiter=",")
        self.commandLinkButton_next.setEnabled(True)
        print("Hello\n")
        return
    def _get_template(self):
        self.benchNo += 1
        if self.benchNo == 1:
            self.signaltemplate = self.arr_x
            self.pushButton_end.setEnabled(True)
        else:
            print("Hello\n")
        self.pushButton_yes.setEnabled(False)
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
    window = _noisepowerspectrum()
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

