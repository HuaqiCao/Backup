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
import scipy.stats
import uproot
import os
import layout5 as lay5
import scipy.fft
class _matchedfilter(lay5.Ui_MainWindow):
    wl,pp,sp,th=0,0,0,0.0
    bl,bl_rms,amp,rt,dt,posi=0.0,0.0,0.0,0,0,0
    def __init__(self,FilePath='/Users/zhaokangkang/WorkArea/Bolometer/Data/',FileName='20180419_19h56.BIN4.root'):
        self.FilePath = FilePath
        self.FileName = FileName
        super(_matchedfilter, self).__init__()
        self.setupUi(self)
        #init
        self.initState()
        #process
        self.pushButton_FilterTemplate.clicked.connect(self._filter_template)
        self.pushButton_FilterAll.clicked.connect(self._filter_all)
        self.pushButton_trigger.clicked.connect(self._trigger_all)
        self.pushButton_start.clicked.connect(self._get_start)
        self.pushButton_next.clicked.connect(self.from_next)
        self.pushButton_nps.clicked.connect(self._filter_nps)

    def initState(self):
        self.kk = 0
        self.center()
        self.pushButton_FilterAll.setEnabled(False)
        #self.pushButton_start.setEnabled(False)
        #self.pushButton_next.setEnabled(False)
        #self.pushButton_trigger.setEnabled(False)
        file_para = open("paralist.txt",'r')
        self.FilePath = file_para.readline().split('\n')[0]
        self.FileName = file_para.readline().split('\n')[0]
        self.wl = int(file_para.readline().split('\n')[0])
        self.fs = int(file_para.readline().split('\n')[0])
        self.peakpos = int(file_para.readline().split('\n')[0])
        self.bl_s = int(file_para.readline().split('\n')[0])
        self.bl_e = int(file_para.readline().split('\n')[0])
        file_para.close()
        print("Hello, let's start!")
        self.opfile = open(self.FilePath+self.FileName,"rb")
        return
    def closewin(self):
        self.close()
        #QCoreApplication.instance().quit()
    def center(self, screenNum=0):
        '''多屏居中支持'''
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.normalGeometry2 = QRect((screen.width() - size.width())//2 + screen.left(),
                                     (screen.height() - size.height())//2, size.width(), size.height())
        self.setGeometry((screen.width() - size.width())//2 + screen.left(),
                         (screen.height() - size.height())//2, size.width(), size.height())
    def _filter_template(self):
        self.signaltemplate = np.loadtxt(self.FilePath+'data/signaltemplate.txt',dtype=float)
        #diff_template = np.zeros(self.wl)
        #diff_template[1:] += np.diff(self.signaltemplate)
        diff_template = np.diff(self.signaltemplate)
        self.noisepsd = np.loadtxt(self.FilePath+'data/noiseps.txt',dtype=float)
        self.diff_nps = np.loadtxt(self.FilePath+'data/diff_nps.txt',dtype=float)
        self.freq = np.fft.fftfreq(self.wl, 1./self.fs)
        self.diff_freq = np.fft.fftfreq(self.wl-1, 1./self.fs)
        self.peakp = np.argmax(self.signaltemplate)
        print(self.peakp)
        print(self.freq)
        self.freqI = np.arange(self.wl)
        self.diff_freqI = np.arange(self.wl-1)
        #self.phaseshift = np.cos(self.freq*2*np.pi*self.peakp/self.wl)-np.sin(self.freq*2*np.pi*self.peakp/self.wl)*1j
        self.phaseshift = np.cos(self.freqI*2*np.pi*self.peakp/self.wl)-np.sin(self.freqI*2*np.pi*self.peakp/self.wl)*1j
        self.diff_phaseshift = np.cos(self.diff_freqI*2*np.pi*self.peakp/(self.wl-1))-np.sin(self.diff_freqI*2*np.pi*self.peakp/(self.wl-1))*1j
        #self.templateconj = np.fft.fft(diff_template).conjugate()
        self.templateconj = np.fft.fft(self.signaltemplate).conjugate()
        self.diff_templateconj = np.fft.fft(diff_template).conjugate()
        hconstant = np.sum(np.real(self.templateconj*np.fft.fft(self.signaltemplate))/self.noisepsd)/self.wl
        diff_hconstant = np.sum(np.real(self.diff_templateconj*np.fft.fft(diff_template))/self.diff_nps)/(self.wl-1)
        num = 0
        for xx in self.noisepsd:
            num +=1
            if xx == 0:
                print(num)
        self.filter = self.templateconj*self.phaseshift/(self.noisepsd)/hconstant
        self.diff_filter = self.diff_templateconj*self.diff_phaseshift/(self.diff_nps)/diff_hconstant
        np.savetxt(self.FilePath+'data/filter.txt', self.filter, fmt='%.20f',delimiter=",")
        np.savetxt(self.FilePath+'data/diff_filter.txt', self.diff_filter, fmt='%.20f',delimiter=",")
        self.filtered = np.real(np.fft.ifft(np.fft.fft(self.signaltemplate)*self.filter))
        self.diff_filtered = np.real(np.fft.ifft(np.fft.fft(diff_template)*self.diff_filter))#*0.85
        #self.filtered = np.real(np.fft.ifft(np.fft.fft(diff_template)*self.filter))
        print(np.argmax(self.filtered))
        print(np.max(self.filtered))
        print(hconstant)
        print(math.sqrt(1/(self.wl*hconstant)))
        print(math.sqrt(1/(self.wl*hconstant)))
        self.arr_t = np.arange(self.wl)
        self.MplWidget.canvas.axes.clear() 
        #self.MplWidget.canvas.axes.plot(self.arr_t, diff_template, label='Template')
        self.MplWidget.canvas.axes.plot(self.arr_t, self.signaltemplate, label='Template')
        #self.MplWidget.canvas.axes.plot(self.arr_t, self.filtered, label='Filtered template')
        self.MplWidget.canvas.axes.plot(self.arr_t[1:], self.diff_filtered, label='Diff Filtered template')
        self.MplWidget.canvas.axes.legend()
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        np.savetxt(self.FilePath+'data/filteredtemplate_ps.txt', self.filtered, fmt='%.20f',delimiter=",")
        np.savetxt(self.FilePath+'data/diff_filteredtemplate.txt', self.diff_filtered, fmt='%.20f',delimiter=",")
        self.pushButton_FilterAll.setEnabled(True)
        return
    def _filter_nps(self):
        signaltemplate_this = np.loadtxt(self.FilePath+'data/signaltemplate.txt',dtype=float)
        noisepsd_this = np.loadtxt(self.FilePath+'data/noiseps.txt',dtype=float)
        freq_this = np.fft.fftfreq(self.wl, 1./self.fs)
        templateconj_this = np.fft.fft(signaltemplate_this).conjugate()
        filtered_sps = np.real(templateconj_this*templateconj_this.conjugate())#/self.wl
        hconstant_this = np.sum(np.real(templateconj_this*templateconj_this.conjugate())/noisepsd_this)
        print(math.sqrt(1/hconstant_this))
        filtered_nps = math.pow(1/(hconstant_this),2)*np.real(templateconj_this*templateconj_this.conjugate())/noisepsd_this
        self.MplWidget.canvas.axes.clear() 
        self.MplWidget.canvas.axes.plot(freq_this[:self.wl//2], noisepsd_this[:self.wl//2]/self.wl/self.wl, label='Noise power spectrum')
        self.MplWidget.canvas.axes.plot(freq_this[:self.wl//2], filtered_nps[:self.wl//2], label='Filtered nps')
        self.MplWidget.canvas.axes.plot(freq_this[:self.wl//2], filtered_sps[:self.wl//2], label='Signal Power Spectrum')
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.axes.set_xlabel('Frequency (Hz)')
        self.MplWidget.canvas.axes.set_ylabel('PS (ADC^2/Hz)')
        self.MplWidget.canvas.axes.legend()
        self.MplWidget.canvas.axes.set_yscale('log')
        self.MplWidget.canvas.axes.set_xscale('log')
        self.MplWidget.canvas.draw()

        return
    def _filter_all(self):
        #get_filter = np.loadtxt(self.FilePath+'data/filter.txt',dtype=complex)
        get_filter = np.loadtxt(self.FilePath+'data/diff_filter.txt',dtype=complex)
        filter_t = np.real(np.fft.ifft(get_filter))
        self.wl = np.size(get_filter)
        filter_2t = np.zeros(2*self.wl)
        filter_2t[:self.wl//2]=filter_t[:self.wl//2]
        filter_2t[-self.wl//2:]=filter_t[-self.wl//2:]
        #np.savetxt(self.FilePath+'data/filter_2t.txt', filter_2t, fmt='%.20f',delimiter=",")
        np.savetxt(self.FilePath+'data/diff_filter_2t.txt', filter_2t, fmt='%.20f',delimiter=",")
        filter_padding = np.fft.fft(filter_2t)
        # 使用示例
        bar = ProgressBar() # 初始化 ProcessBar实例
        filelength = os.path.getsize(self.FilePath+self.FileName)
        tot = os.path.getsize(self.FilePath+self.FileName)//4
        total_number=0 # 总任务数
        task_id=0 # 子任务序号
        tot_num = tot//self.wl
        print(tot_num)
        #filefiltered = open(self.FilePath+"data/filtereddata.BIN2","wb")
        filefiltered = open(self.FilePath+"data/diff_filtereddata.BIN2","wb")
        for k in range(0, tot_num):
            if k%20000 == 0:
                print(k//20000)
            if (k*100)%tot_num ==0:
                bar.setValue(str(task_id),str(total_number),(k*100)//tot_num) # 刷新进度条
                QApplication.processEvents()  # 实时刷新显示
            x = []
            num = 0
            self.opfile.seek(4*self.wl*k,0)
            if (self.wl)*4*(k+2) >= filelength:
                break
            txt = self.opfile.read((2*self.wl+1)*4)
            arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            arr_x = np.diff(arr_x)
            filtered_x = np.real(np.fft.ifft(np.fft.fft(arr_x)*filter_padding))
            filtered_x = np.float32(filtered_x)
            txt = filtered_x[self.wl//2:(self.wl*3)//2].tobytes()
            filefiltered.write(txt)
        bar.close()  # 关闭进度条
        filefiltered.close()
        #self.pushButton_start.setEnabled(True)
        #self.pushButton_next.setEnabled(True)
        #self.pushButton_trigger.setEnabled(True)
        print("Hello\n")
        return
    def _get_start(self):
        self.startp = self.spinBox_start.value()
        self.filefiltered = open(self.FilePath+"data/diff_filtereddata.BIN2","rb")
        #self.filefiltered = open(self.FilePath+"data/filtereddata.BIN2","rb")
        self.filefiltered.seek(4*self.startp)
        self.opfile.seek(4*(self.wl//2+self.startp),0)
        self._get_pulse()
        self.pushButton_next.setEnabled(True)
        return
    def from_next(self):
        self.startp += self.spinBox_wl.value()
        self.spinBox_start.setValue(self.startp)
        self.filefiltered.seek(4*self.startp)
        self.opfile.seek(4*(self.wl//2+self.startp),0)
        self._get_pulse()
        return
    def _get_pulse(self):
        wl_inspect = self.spinBox_wl.value()
        txt = self.filefiltered.read(wl_inspect*4)
        arr_filtered = np.frombuffer(txt, 'float32')
        txt = self.opfile.read(wl_inspect*4)
        arr_x = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
        self.kk += 1
        arr_x = arr_x-arr_x[0]
        self.MplWidget.canvas.axes.clear()
        self.MplWidget.canvas.axes.plot(np.arange(wl_inspect)+self.startp, arr_x, label='Raw signal')
        self.MplWidget.canvas.axes.plot(np.arange(wl_inspect)+self.startp, arr_filtered, label='Filtered signal')
        self.MplWidget.canvas.axes.legend()
        self.MplWidget.defcanvas()
        self.MplWidget.canvas.draw()
        return
    def _trigger_all(self):
        self.signaltemplate = np.loadtxt(self.FilePath+'data/signaltemplate.txt',dtype=float)
        #self.filteredtemplate = np.loadtxt(self.FilePath+'data/filteredtemplate_ps.txt',dtype=float)
        self.filteredtemplate = np.loadtxt(self.FilePath+'data/diff_filteredtemplate.txt',dtype=float)
        peakp_template = np.argmax(self.signaltemplate)    
        peakp_filtered = np.argmax(self.filteredtemplate)
        noisepsd_this = np.loadtxt(self.FilePath+'data/noiseps.txt',dtype=float)
        templateconj_this = np.fft.fft(self.signaltemplate).conjugate()
        diff_template = np.diff(self.signaltemplate)
        self.diff_templateconj = np.fft.fft(diff_template).conjugate()
        self.diff_nps = np.loadtxt(self.FilePath+'data/diff_nps.txt',dtype=float)
        diff_hconstant = np.sum(np.real(self.diff_templateconj*np.fft.fft(diff_template))/self.diff_nps)/(self.wl-1)
        #hconstant_this = math.sqrt(1/np.sum(np.real(templateconj_this*templateconj_this.conjugate())/noisepsd_this))
        hconstant_this = diff_hconstant
        print(hconstant_this)
        print(hconstant_this)
        print(math.sqrt(1/(self.wl*hconstant_this)))
        hconstant_this = math.sqrt(1/(self.wl*diff_hconstant))
        print(hconstant_this)
        ref_dt = 0
        ref_rt = 0
        for i in reversed(self.signaltemplate[:peakp_template]):
            if i < 0.9:
                if i < 0.1:
                    break
                ref_rt+=1
        for i in self.signaltemplate[peakp_template:]:
            if i < 0.9:
                if i < 0.3:
                    break
                ref_dt+=1
        print(ref_rt)
        print(ref_dt)
        self.wl_2 = (ref_rt+ref_dt)*3//2*2
        print(self.wl_2)
        print(peakp_filtered)
        if self.wl_2 > peakp_filtered:
            self.wl_2 = (peakp_filtered-2)*2
        if self.wl_2//2 < 6*ref_rt:
            self.wl_2 = 12*ref_rt
        print('window length: %d' %self.wl_2)
        print('peakp: %d' %peakp_filtered)
        filtered = self.filteredtemplate[peakp_filtered:peakp_filtered+self.wl_2//2]
        filtered2 = self.filteredtemplate[peakp_filtered-self.wl_2//2:peakp_filtered+self.wl_2//2]
        print(len(filtered2))
        self.filefiltered = open(self.FilePath+"data/diff_filtereddata.BIN2","rb")
        self.filefiltered.seek(0)
        # 使用示例
        bar = ProgressBar() # 初始化 ProcessBar实例
        tot = os.path.getsize(self.FilePath+"data/diff_filtereddata.BIN2")//4
        total_number=0 # 总任务数
        task_id = 0    # 子任务序号
        self.step = 10*ref_rt#self.wl_2
        tot_num = (tot-int(self.wl/2))//(3*self.step//4)
        print(tot_num)
        list_bl  = []
        list_bl_RMS  = []
        list_bl_slope  = []
        list_bl_chi2  = []
        list_rt  = []
        list_dt  = []
        list_tvl = []
        list_tvr = []
        list_maxp_filtered = []
        list_amp_raw      = []
        list_amp_filtered = []
        list_chi2raw      = []
        list_chi2filtered = []
        list_amp_rawfit   = []
        list_bl_rawfit    = []
        list_lstsq_rawfit = []
        list_amp_filterfit   = []
        list_bl_filterfit    = []
        list_lstsq_filterfit = []

        maxp_filtered = 0
        for k in range(5,tot_num):
            if k%20000 == 0:
                print(k//20000)
            if (k*100)%tot_num ==0:
                bar.setValue(str(task_id),str(total_number),(k*100)//tot_num) # 刷新进度条
                QApplication.processEvents()  # 实时刷新显示
            x = []
            num = 0
            self.opfile.seek(4*((self.step*3//4)*k+self.wl//2),0)
            txt = self.opfile.read(self.step*4)
            arr_x_tmp = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))

            self.filefiltered.seek((self.step*3//4)*k*4,0)
            txt = self.filefiltered.read(self.step*4)
            arr_filtered_tmp = np.frombuffer(txt, 'float32')

            maxp_filtered_tmp = np.argmax(arr_filtered_tmp)
            amp_raw = np.max(arr_x_tmp)
            if maxp_filtered_tmp == 0:
                continue
            if maxp_filtered_tmp == self.step-1:
                continue
            #filter fire condition: threshold = num*sigma_f
            if np.max(arr_filtered_tmp) < 4*hconstant_this:
                continue
            if abs(np.argmax(arr_x_tmp)-maxp_filtered_tmp) > 2*ref_rt:
                continue
            if maxp_filtered == maxp_filtered_tmp+self.step*3//4*k:
                continue
            self.filefiltered.seek(((self.step*3//4)*k+maxp_filtered_tmp-self.wl_2//2)*4,0)
            txt2 = self.filefiltered.read(self.wl_2*4)
            arr_filtered = np.frombuffer(txt2, 'float32')
            amp_filtered = arr_filtered[self.wl_2//2]
            arr_filtered = arr_filtered/amp_filtered

            if np.corrcoef(arr_filtered[self.wl_2//2-ref_rt:self.wl_2//2+ref_rt], filtered2[self.wl_2//2-ref_rt:self.wl_2//2+ref_rt])[0,1]<0.75:
            #if np.corrcoef(arr_filtered[self.wl_2//2-ref_rt:self.wl_2//2+ref_rt], filtered2[self.wl_2//2-ref_rt:self.wl_2//2+ref_rt])[0,1]<0.85:
                continue
            '''
            if arr_filtered[self.wl_2//2-ref_rt]>1.2*filtered2[self.wl_2//2-ref_rt]:
                continue
            if arr_filtered[self.wl_2//2-ref_rt]<0.8*filtered2[self.wl_2//2-ref_rt]:
                continue
            if arr_filtered[self.wl_2//2+ref_rt]>1.2*filtered2[self.wl_2//2+ref_rt]:
                continue
            if arr_filtered[self.wl_2//2+ref_rt]<0.8*filtered2[self.wl_2//2+ref_rt]:
                continue
            if abs(linearfit_filter[0][0] -1) > 0.25:
                continue
            if abs(linearfit_filter[0][1]) > 0.25:
                continue
            '''
            linearfit_filter = np.polyfit(filtered2, arr_filtered, 1, full=True)
            maxp_filtered = maxp_filtered_tmp+self.step*3//4*k
            x = []
            num = 0
            self.opfile.seek(4*((self.step*3//4)*k+self.wl//2+maxp_filtered_tmp-self.wl_2//2),0)
            txt = self.opfile.read(self.wl_2*4)
            arr_x2 = np.frombuffer(txt, '<u4').astype(np.dtype('<i4'))
            bl = np.sum(arr_x2[self.wl_2//2-6*ref_rt:self.wl_2//2-2*ref_rt])/(ref_rt*4)
            bl_RMS = math.sqrt(np.sum(np.power(arr_x2[self.wl_2//2-6*ref_rt:self.wl_2//2-2*ref_rt]-bl,2))/(ref_rt*4))
            linearfit_bl = np.polyfit(np.arange(4*ref_rt),arr_x2[self.wl_2//2-6*ref_rt:self.wl_2//2-2*ref_rt],1,full=True)
            bl_slope = linearfit_bl[0][0]
            bl_chi2  = linearfit_bl[1][0]
            amp_raw = amp_raw-bl
            if amp_raw==0:
                    continue
            linearfit_raw = np.polyfit(self.signaltemplate[peakp_template-self.wl_2//2:peakp_template+self.wl_2//2],arr_x2,1,full=True)

            arr_x2 = (arr_x2-bl)/amp_raw
            dt = 0
            rt = 0
            for i in reversed(arr_x2[:self.wl_2//2]):
                if i < 0.9:
                    if i < 0.1:
                        break
                    rt+=1
            for i in arr_x2[self.wl_2//2:]:
                if i < 0.9:
                    if i < 0.3:
                        break
                    dt+=1
            '''
            if dt < 0.03*ref_dt:
                continue
            if rt < 0.2*ref_rt:
                continue
            '''
            chi2raw = math.sqrt(np.sum(np.power(arr_x2-self.signaltemplate[peakp_template-self.wl_2//2:peakp_template+self.wl_2//2],2))/self.wl_2)
            tvl = math.sqrt(np.sum(np.power(arr_filtered[:self.wl_2//2]-filtered,2))/self.wl_2)
            tvr = math.sqrt(np.sum(np.power(arr_filtered[-(self.wl_2//2):]-filtered[::-1],2))/self.wl_2)
            chi2filtered = tvl+tvr
            
            list_amp_filterfit.append(linearfit_filter[0][0])
            list_bl_filterfit.append(linearfit_filter[0][1])
            list_lstsq_filterfit.append(linearfit_filter[1][0])
            list_amp_rawfit.append(linearfit_raw[0][0])
            list_bl_rawfit.append(linearfit_raw[0][1])
            list_lstsq_rawfit.append(linearfit_raw[1][0])
            list_bl.append(bl)
            list_bl_RMS.append(bl_RMS)
            list_bl_slope.append(bl_slope)
            list_bl_chi2.append(bl_chi2)
            list_rt.append(rt)
            list_dt.append(dt)
            list_tvl.append(tvl)
            list_tvr.append(tvr)
            list_amp_raw.append(amp_raw)
            list_amp_filtered.append(amp_filtered)
            list_maxp_filtered.append(maxp_filtered)
            list_chi2raw.append(chi2raw)
            list_chi2filtered.append(chi2filtered)
            '''
            self.MplWidget.canvas.axes.clear()
            self.MplWidget.canvas.axes.plot(np.arange(self.wl_2), arr_x2, label='Raw signal')
            self.MplWidget.canvas.axes.plot(np.arange(self.wl_2), arr_filtered, label='Filtered signal')
            self.MplWidget.defcanvas()
            self.MplWidget.canvas.draw()
            #print(k)
            #print(maxp_filtered+5000)
            '''
        arr_bl = np.array(list_bl)
        arr_rt = np.array(list_rt)
        arr_dt = np.array(list_dt)
        arr_tvl = np.array(list_tvl)
        arr_tvr = np.array(list_tvr)
        arr_amp_raw      = np.array(list_amp_raw)
        arr_amp_filtered = np.array(list_amp_filtered)
        arr_chi2raw      = np.array(list_chi2raw)
        arr_chi2filtered = np.array(list_chi2filtered)
        arr_maxp_filtered = np.array(list_maxp_filtered)
        arr_amp_rawfit = np.array(list_amp_rawfit)
        arr_bl_rawfit = np.array(list_bl_rawfit)
        arr_lstsq_rawfit = np.array(list_lstsq_rawfit)
        arr_amp_filterfit = np.array(list_amp_filterfit)
        arr_bl_filterfit = np.array(list_bl_filterfit)
        arr_lstsq_filterfit = np.array(list_lstsq_filterfit)
        arr_bl_RMS = np.array(list_bl_RMS)
        arr_bl_slope = np.array(list_bl_slope)
        arr_bl_chi2 = np.array(list_bl_chi2)
        eventfile = uproot.recreate(self.FilePath+"data/TriggerEvent.root")
        eventfile["tree1"] = {"MaxPos": arr_maxp_filtered, "Baseline":arr_bl, "Amp_raw":arr_amp_raw,"Amp_filtered":arr_amp_filtered,"RiseTime":arr_rt,"DecayTime":arr_dt,"TVL":arr_tvl,"TVR":arr_tvr,"Chi2raw":arr_chi2raw,"Chi2filtered":arr_chi2filtered,"amp_rawfit":arr_amp_rawfit,"bl_rawfit":arr_bl_rawfit,"lstsq_rawfit":arr_lstsq_rawfit,"amp_filterfit":arr_amp_filterfit,"bl_filterfit":arr_bl_filterfit,"lstsq_filterfit":arr_lstsq_filterfit,"bl_RMS":arr_bl_RMS, "bl_slope":arr_bl_slope, "bl_chi2":arr_bl_chi2}
        return
    def _end_template(self):
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
    def setValue(self,task_number,total_task_number, value): # 设置总任务进度和子任务进度
        if task_number=='0' and total_task_number=='0':
            self.setWindowTitle(self.tr('正在处理中'))
        else:
            label = "正在处理：" + "第" + str(task_number) + "/" + str(total_task_number)+'个任务'
            self.setWindowTitle(self.tr(label)) # 顶部的标题
        self.progressBar.setValue(value)
        self.progressBar.update()
        return
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = _matchedfilter()
    window.show()
    sys.exit(app.exec_())
