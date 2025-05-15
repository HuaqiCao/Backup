import matplotlib.pyplot as plt
import numpy as np
import time
import math
import random
import sys
import scipy.stats
import scipy.fft
from scipy import signal, stats, fft
import uproot
import os

def _trigger():
    # 路径结尾需要带有文件夹标识符"/"
    heat_path = '/Volumes/Kangkang/LSC_CROSS_Run9_dataforkangkang/075/'
    heat_name = '000920_20230927T161341_075.bin.converted'
    fs = 2000 #Hz
    heat_peakpos = 500 #sample points

    offset_points = -20 #negative value usually for triggering light using heat.
    correl_reject = 0.5 # (0, 1.0)
    parame_points = 



    heat_signaltemplate = np.loadtxt(heat_path+'data/signaltemplate.txt',dtype=float)
    heat_diffnoiseps = np.loadtxt(heat_path+'data/diff_nps.txt',dtype=float)
    heat_length = np.size(heat_signaltemplate)
    #heat_length = np.shape(heat_signaltemplate)[0]
    #在diff 尾端拼接一个0， 默认情况下，axis=0可以不写
    heat_difftemplate = np.concatenate((np.diff(heat_signaltemplate),[0]),axis=0)  

    heat_win = scipy.signal.windows.tukey(heat_length, alpha=0.5, sym=True)
    #计算归一化常数时，不应该使用余弦衰减函数
    heat_OF_norm = heat_length/np.sum(np.abs(np.fft.fft(heat_difftemplate))**2/np.append(heat_diffnoiseps,heat_diffnoiseps[-1]))
    #heat_OF_norm = heat_length/np.sum(np.abs(np.fft.fft(heat_difftemplate)*heat_win)**2/np.append(heat_diffnoiseps,heat_diffnoiseps[-1]))

    heat_freq = np.fft.fftfreq(heat_length, 1./fs)
    heat_phase = np.cos(heat_freq*2*np.pi*heat_peakpos/fs)-np.sin(heat_freq*2*np.pi*heat_peakpos/fs)*1j
    #heat_freqI = np.arange(heat_length)
    #heat_phase = np.cos(heat_freqI*2*np.pi*heat_peakpos/heat_length)-np.sin(heat_freqI*2*np.pi*heat_peakpos/heat_length)*1j

    heat_OF_f = heat_OF_norm*np.fft.fft(heat_difftemplate).conjugate()*heat_phase/np.append(heat_diffnoiseps, heat_diffnoiseps[-1])
    heat_OF_t = np.real(np.fft.ifft(heat_OF_f))
    heat_OF_2t = np.concatenate((heat_OF_t[0:heat_length//2]*heat_win[heat_length//2:heat_length],np.zeros(heat_length),heat_OF_t[heat_length//2:heat_length]*heat_win[0:heat_length//2]), axis=0)
    heat_OF_2f = np.fft.fft(heat_OF_2t)

    heat_template_2t = np.concatenate((np.zeros(heat_length//2),heat_win*heat_signaltemplate,np.zeros(heat_length//2)), axis=0)
    heat_OF_template_t = np.real(np.fft.ifft(heat_OF_f*np.fft.fft(heat_difftemplate*heat_win)))
    heat_OF_template_2t = np.real(np.fft.ifft(np.fft.fft(np.concatenate((np.zeros(heat_length//2),heat_win*np.append(np.diff(heat_signaltemplate),0),np.zeros(heat_length//2)), axis=0))*heat_OF_2f))#[heat_length/2:heat_length/2+heat_length]

    fig, ax = plt.subplots(nrows=1, ncols=1)
    ax.plot(np.arange(2*heat_length)/fs, heat_OF_template_2t, c='r', label='OF_2t')
    ax.plot(np.arange(2*heat_length)/fs, heat_template_2t, c='g', label='Template_2t')
    ax.plot(np.arange(heat_length)/fs+heat_length/fs/2, heat_OF_template_t, c='b', label='OF_t')
    ax.legend()
    ax.grid(True)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Height')
    #ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))
    plt.show()
    return

_trigger()
    
'''
filter = self.templateconj*self.phaseshift/(self.noisepsd)/hconstant

self.filteredtemplate = np.loadtxt(self.FilePath+'data/diff_filteredtemplate.txt',dtype=float)
peakp_template = np.argmax(self.signaltemplate)    
peakp_filtered = np.argmax(self.filteredtemplate)
noisepsd_this = np.loadtxt(self.FilePath+'data/noiseps.txt',dtype=float)
templateconj_this = np.fft.fft(self.signaltemplate).conjugate()
diff_template = np.diff(self.signaltemplate)
self.diff_templateconj = np.fft.fft(diff_template).conjugate()
self.diff_nps = np.loadtxt(self.FilePath+'data/diff_nps.txt',dtype=float)
diff_hconstant = np.sum(np.real(self.diff_templateconj*np.fft.fft(diff_template))/self.diff_nps)/(self.wl-1)
hconstant_this = diff_hconstant
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
print('window length: %d' %self.wl_2)
print('peakp: %d' %peakp_filtered)
filtered = self.filteredtemplate[peakp_filtered:peakp_filtered+self.wl_2//2]
filtered2 = self.filteredtemplate[peakp_filtered-self.wl_2//2:peakp_filtered+self.wl_2//2]
print(len(filtered2))
#self.filefiltered = open(self.FilePath+"data/filtereddata.BIN2","rb")
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
    self.opfile.seek(2*((self.step*3//4)*k+self.wl//2),0)
    for num in range(0,self.step):
        data = int.from_bytes(self.opfile.read(2), "little",signed=False)
        x.append(data)
    arr_x_tmp = np.array(x)

    self.filefiltered.seek((self.step*3//4)*k*4,0)
    txt = self.filefiltered.read(self.step*4)
    arr_filtered_tmp = np.frombuffer(txt, 'float32')

    maxp_filtered_tmp = np.argmax(arr_filtered_tmp)
    amp_raw = np.max(arr_x_tmp)
    if maxp_filtered_tmp == 0:
        continue
    if maxp_filtered_tmp == self.step-1:
        continue
    if np.max(arr_filtered_tmp) < 4*hconstant_this:
    #if np.max(arr_filtered_tmp) < 2.52:
        continue
    #if abs(np.argmax(arr_x_tmp)-maxp_filtered_tmp) > 4*ref_rt:
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
    linearfit_filter = np.polyfit(filtered2, arr_filtered, 1, full=True)
    maxp_filtered = maxp_filtered_tmp+self.step*3//4*k
    x = []
    num = 0
    self.opfile.seek(2*((self.step*3//4)*k+self.wl//2+maxp_filtered_tmp-self.wl_2//2),0)
    for num in range(0,self.wl_2):
        data = int.from_bytes(self.opfile.read(2), "little",signed=False)
        x.append(data)
    arr_x2 = np.array(x)
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
    if dt < 0.03*ref_dt:
        continue
    if rt < 0.2*ref_rt:
        continue
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
    self.MplWidget.canvas.axes.clear()
    self.MplWidget.canvas.axes.plot(np.arange(self.wl_2), arr_x2, label='Raw signal')
    self.MplWidget.canvas.axes.plot(np.arange(self.wl_2), arr_filtered, label='Filtered signal')
    self.MplWidget.defcanvas()
    self.MplWidget.canvas.draw()
    #print(k)
    #print(maxp_filtered+5000)
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
'''
