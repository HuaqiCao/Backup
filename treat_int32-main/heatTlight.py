import matplotlib.pyplot as plt
import numpy as np
import time
import math
import random
import sys
import scipy.signal
from scipy import signal, stats, fft
from scipy.optimize import curve_fit
import uproot
import os
def func_exp(x, a, b, c):
    return a * np.exp(-b * x) + c
def _trigger():
    # 路径结尾需要带有文件夹标识符"/"
    heat_path  = '/home/duandy/disk/bolometer/Data/RUN33/fHuL_WTh_CS/heat/'
    # BIN file name
    heat_name  = 'Run33_fHuL_WTh_CS_1125_heat.BIN2'
    
    light_path = '/home/duandy/disk/bolometer/Data/RUN33/fHuL_WTh_CS/light/'
    # BIN file name
    light_name = 'Run33_fHuL_WTh_CS_1125_light.BIN2'
    # the offset parameter is essential, you need to check the offset of peak value between signal template of heat and light 
    offset = -30 #negative value usually for triggering light using heat.

    data_bytes = 4
    heat_correreject = 0.1 # (0, 1.0)
    heat_paralength = 600 #should be less than half of window length
    light_paralength = 300 #should be less than half of window length
    fs = 5000 #Hz

    threshold = 4.0
    light_threshold = 4.0

    heat_signaltemplate = np.loadtxt(heat_path+'data/signaltemplate.txt',dtype=float)
    heat_signaltemplate /= np.max(heat_signaltemplate)
    heat_diffnoiseps = np.loadtxt(heat_path+'data/diff_nps.txt',dtype=float)
    heat_length = np.size(heat_signaltemplate)
    heat_peakpos = np.argmax(heat_signaltemplate)+1 #sample points
    #heat_length = np.shape(heat_signaltemplate)[0]
    heat_ref_dt = 0
    heat_ref_rt = 0
    for i in reversed(heat_signaltemplate[:heat_peakpos]):
        if i < 0.9:
            if i < 0.1:
                break
            heat_ref_rt+=1
    for i in heat_signaltemplate[heat_peakpos:]:
        if i < 0.9:
            if i < 0.3:
                break
            heat_ref_dt+=1
    print(heat_ref_rt)
    print(heat_ref_dt)
    #在diff 尾端拼接一个0， 默认情况下，axis=0可以不写
    heat_difftemplate = np.concatenate((np.diff(heat_signaltemplate),[0]),axis=0)  

    heat_win = scipy.signal.windows.tukey(heat_length, alpha=heat_peakpos/heat_length, sym=True)
    #计算归一化常数时，不应该使用余弦衰减函数
    heat_OF_norm = heat_length/np.sum(np.abs(np.fft.fft(heat_difftemplate))**2/np.append(heat_diffnoiseps,heat_diffnoiseps[-1]))
    #heat_OF_norm = heat_length/np.sum(np.abs(np.fft.fft(heat_difftemplate)*heat_win)**2/np.append(heat_diffnoiseps,heat_diffnoiseps[-1]))
    print(r'Filtered baseline sigma is: {0:0.2f}'.format(math.sqrt(heat_OF_norm/heat_length)*2**16/10.24))
    threshold *= math.sqrt(heat_OF_norm/heat_length)
    print(threshold)

    heat_freq = np.fft.fftfreq(heat_length, 1./fs)
    heat_phase = np.cos(heat_freq*2*np.pi*heat_peakpos/fs)-np.sin(heat_freq*2*np.pi*heat_peakpos/fs)*1j
    #heat_freqI = np.arange(heat_length)
    #heat_phase = np.cos(heat_freqI*2*np.pi*heat_peakpos/heat_length)-np.sin(heat_freqI*2*np.pi*heat_peakpos/heat_length)*1j

    heat_OF_f = heat_OF_norm*np.fft.fft(heat_difftemplate).conjugate()*heat_phase/np.append(heat_diffnoiseps, heat_diffnoiseps[-1])
    heat_OF_t = np.real(np.fft.ifft(heat_OF_f))
    heat_OF_2t = np.concatenate((heat_OF_t[0:heat_length//2]*heat_win[heat_length//2:heat_length],np.zeros(heat_length),heat_OF_t[heat_length//2:heat_length]*heat_win[0:heat_length//2]), axis=0)
    heat_OF_2f = np.fft.fft(heat_OF_2t)
    heat_OF_2f[0] = 0

    heat_template_2t = np.concatenate((np.zeros(heat_length//2),heat_win*heat_signaltemplate,np.zeros(heat_length//2)), axis=0)
    heat_OF_template_t = np.real(np.fft.ifft(heat_OF_f*np.fft.fft(heat_difftemplate*heat_win)))
    heat_OF_template_2t = np.real(np.fft.ifft(np.fft.fft(np.concatenate((np.zeros(heat_length//2),heat_win*np.append(np.diff(heat_signaltemplate),0),np.zeros(heat_length//2)), axis=0))*heat_OF_2f))#[heat_length/2:heat_length/2+heat_length]
    '''
    '''
    if heat_peakpos < heat_length//2:
        break_point = 2*heat_length - heat_length//2 + heat_peakpos
    else:
        break_point = - heat_length//2 + heat_peakpos
    heat_OF_template_center = np.concatenate((heat_OF_template_2t[break_point:heat_length*2],heat_OF_template_2t[0:break_point]),axis=0)
    heat_peakvalley_length = abs(np.argmax(heat_OF_template_2t)-np.argmin(heat_OF_template_2t))

    heat_OF_norm = heat_length/np.sum(np.abs(np.fft.fft(heat_difftemplate))**2/np.append(heat_diffnoiseps,heat_diffnoiseps[-1]))
    heat_sigmaL2 = (heat_OF_norm**2)*np.sum((np.abs(np.fft.fft(heat_difftemplate))**2)[heat_length//(2*heat_paralength):heat_length-heat_length//(2*heat_paralength)]/np.append(heat_diffnoiseps,heat_diffnoiseps[-1])[heat_length//(2*heat_paralength):heat_length-heat_length//(2*heat_paralength)]) 
    heat_meantime_template = np.sum(np.arange(heat_length)[heat_peakpos-2*heat_ref_rt:heat_peakpos+4*heat_ref_dt]*heat_signaltemplate[heat_peakpos-2*heat_ref_rt:heat_peakpos+4*heat_ref_dt])
    print(heat_peakvalley_length)
    print(heat_paralength)
    list_heat_trigpos_fil = []
    list_heat_rawamp = []
    list_heat_filamp = []
    list_heat_baseline  = []
    list_heat_baselineRMS  = []
    list_heat_corre  = []
    list_heat_tv  = []
    list_heat_tvl  = []
    list_heat_tvr  = []
    list_heat_SI = []
    list_heat_baseline_slope  = []
    list_heat_fitted_baseline  = []
    list_heat_fitted_rawamp  = []
    list_heat_rt  = []
    list_heat_dt  = []
    list_heat_delayamp = []
    list_heat_meantime= []
    list_heat_rawarea  = []
    list_heat_filarea = []
    list_heat_corre_narrow = []
    
    # fig0, ax0 = plt.subplots(nrows=1, ncols=1)
    # ax0.plot(np.arange(2*heat_length)/fs, heat_OF_template_2t, c='r', label='OF_2t')
    # ax0.plot(np.arange(2*heat_length)/fs, heat_template_2t, c='g', label='Template_2t')
    # ax0.plot(np.arange(heat_length)/fs+heat_length/fs/2, heat_OF_template_t, c='b', label='OF_t')
    # ax0.legend()
    # ax0.grid(True)
    # ax0.set_xlabel('Time (s)')
    # ax0.set_ylabel('Height')
    # #ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))
    # plt.show()
    


    ##############-----*Light*--------------------------##########
    light_signaltemplate = np.loadtxt(light_path+'data/signaltemplate.txt',dtype=float)
    light_signaltemplate /= np.max(light_signaltemplate)
    light_diffnoiseps = np.loadtxt(light_path+'data/diff_nps.txt',dtype=float)
    light_length = np.size(light_signaltemplate)
    light_peakpos = np.argmax(light_signaltemplate)+1 #sample points
    #light_length = np.shape(light_signaltemplate)[0]
    light_ref_dt = 0
    light_ref_rt = 0
    for i in reversed(light_signaltemplate[:light_peakpos]):
        if i < 0.9:
            if i < 0.1:
                break
            light_ref_rt+=1
    for i in light_signaltemplate[light_peakpos:]:
        if i < 0.9:
            if i < 0.3:
                break
            light_ref_dt+=1
    print(light_ref_rt)
    print(light_ref_dt)
    #在diff 尾端拼接一个0， 默认情况下，axis=0可以不写
    light_difftemplate = np.concatenate((np.diff(light_signaltemplate),[0]),axis=0)  

    light_win = scipy.signal.windows.tukey(light_length, alpha=light_peakpos/light_length, sym=True)
    #计算归一化常数时，不应该使用余弦衰减函数
    light_OF_norm = light_length/np.sum(np.abs(np.fft.fft(light_difftemplate))**2/np.append(light_diffnoiseps,light_diffnoiseps[-1]))
    #light_OF_norm = light_length/np.sum(np.abs(np.fft.fft(light_difftemplate)*light_win)**2/np.append(light_diffnoiseps,light_diffnoiseps[-1]))
    print(r'Filtered baseline sigma is: {0:0.2f}'.format(math.sqrt(light_OF_norm/light_length)*2**16/10.24))
    light_threshold *= math.sqrt(light_OF_norm/light_length)*2**16/10.24
    print(light_threshold)

    light_freq = np.fft.fftfreq(light_length, 1./fs)
    light_phase = np.cos(light_freq*2*np.pi*light_peakpos/fs)-np.sin(light_freq*2*np.pi*light_peakpos/fs)*1j
    #light_freqI = np.arange(light_length)
    #light_phase = np.cos(light_freqI*2*np.pi*light_peakpos/light_length)-np.sin(light_freqI*2*np.pi*light_peakpos/light_length)*1j

    light_OF_f = light_OF_norm*np.fft.fft(light_difftemplate).conjugate()*light_phase/np.append(light_diffnoiseps, light_diffnoiseps[-1])
    light_OF_t = np.real(np.fft.ifft(light_OF_f))
    light_OF_2t = np.concatenate((light_OF_t[0:light_length//2]*light_win[light_length//2:light_length],np.zeros(light_length),light_OF_t[light_length//2:light_length]*light_win[0:light_length//2]), axis=0)
    light_OF_2f = np.fft.fft(light_OF_2t)
    light_OF_2f[0] = 0

    light_template_2t = np.concatenate((np.zeros(light_length//2),light_win*light_signaltemplate,np.zeros(light_length//2)), axis=0)
    light_OF_template_t = np.real(np.fft.ifft(light_OF_f*np.fft.fft(light_difftemplate*light_win)))
    light_OF_template_2t = np.real(np.fft.ifft(np.fft.fft(np.concatenate((np.zeros(light_length//2),light_win*np.append(np.diff(light_signaltemplate),0),np.zeros(light_length//2)), axis=0))*light_OF_2f))#[light_length/2:light_length/2+light_length]
    '''
    '''
    if light_peakpos < light_length//2:
        break_point = 2*light_length - light_length//2 + light_peakpos
    else:
        break_point = - light_length//2 + light_peakpos
    light_OF_template_center = np.concatenate((light_OF_template_2t[break_point:light_length*2],light_OF_template_2t[0:break_point]),axis=0)
    light_peakvalley_length = abs(np.argmax(light_OF_template_2t)-np.argmin(light_OF_template_2t))

    light_OF_norm = light_length/np.sum(np.abs(np.fft.fft(light_difftemplate))**2/np.append(light_diffnoiseps,light_diffnoiseps[-1]))
    light_sigmaL2 = (light_OF_norm**2)*np.sum((np.abs(np.fft.fft(light_difftemplate))**2)[light_length//(2*light_paralength):light_length-light_length//(2*light_paralength)]/np.append(light_diffnoiseps,light_diffnoiseps[-1])[light_length//(2*light_paralength):light_length-light_length//(2*light_paralength)]) 
    light_meantime_template = np.sum(np.arange(light_length)[light_peakpos-2*light_ref_rt:light_peakpos+4*light_ref_dt]*light_signaltemplate[light_peakpos-2*light_ref_rt:light_peakpos+4*light_ref_dt])
    light_trigpos_fil = 0
    list_light_trigpos_fil = []
    list_light_rawamp = []
    list_light_filamp = []
    list_light_baseline  = []
    list_light_baselineRMS  = []
    list_light_corre  = []
    list_light_tv  = []
    list_light_tvl  = []
    list_light_tvr  = []
    list_light_SI = []
    list_light_baseline_slope  = []
    list_light_fitted_baseline  = []
    list_light_fitted_rawamp  = []
    list_light_rt  = []
    list_light_dt  = []
    list_light_delayamp = []
    list_light_meantime= []
    list_light_rawarea  = []
    list_light_filarea = []
    list_light_corre_narrow = []

    # fig0, ax0 = plt.subplots(nrows=1, ncols=1)
    # ax0.plot(np.arange(2*light_length)/fs, light_OF_template_2t, c='r', label='OF_2t')
    # ax0.plot(np.arange(2*light_length)/fs, light_template_2t, c='g', label='Template_2t')
    # ax0.plot(np.arange(light_length)/fs+light_length/fs/2, light_OF_template_t, c='b', label='OF_t')
    # ax0.legend()
    # ax0.grid(True)
    # ax0.set_xlabel('Time (s)')
    # ax0.set_ylabel('Height')
    # #ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))
    # plt.show()
    # return

    ##--Trigger Program---------
    ##---get file length
    heat_tot_length = os.path.getsize(heat_path+heat_name)//data_bytes
    light_tot_length = os.path.getsize(light_path+light_name)//data_bytes
    print(heat_tot_length)
    print(light_tot_length)
    if (heat_tot_length != light_tot_length):
        print(r"Heat file ({0:d}) and light file ({1:d}) have different length!!!".format(heat_tot_length,light_tot_length))
        return
    ##--sample window length and each step has 1/10 overlap
    heat_samplelength = 100#heat_para_length
    if heat_samplelength < 4*heat_peakvalley_length:
        heat_samplelength = 4*heat_peakvalley_length
        print(r'Automatically set step window length is {0:d} points.'.format(4*heat_peakvalley_length))
    if heat_paralength < 4*heat_peakvalley_length:
        heat_paralength = 4*heat_peakvalley_length
        print(r'Automatically set step parameter length is {0:d} points.'.format(4*heat_peakvalley_length))
    heat_steplength = heat_samplelength-heat_samplelength//10
    heat_tot_num = heat_tot_length//heat_steplength
    print(heat_tot_num)
    heat_file = open(heat_path+heat_name,"r")
    light_file = open(light_path+light_name,"r")
    #txt = heat_file.read(2*sample_length)
    #v = np.frombuffer(txt,dtype='<i2')
    #heat_file.seek(data_bytes*10)
    #print(v.astype(int))
    break_i = 0
    heat_trigpos_raw = 0
    heat_trigpos_fil = 0

    #[trigpos(s,1),rawmax,filtmax,baseline,baseline_rms,param,chi,tvl,tvr,pf(1),pf(2),risetime_val,decaytime_val,delayed_amp,meantime_value,pulse_area,f_pulse_area,chi_timedom,filtnoise];
    for k in range(000000, heat_tot_num):
        if k%20000 == 0:
            print(r'{0:d}/{1:d} is processing.'.format(k//20000,heat_tot_num//20000))
        heat_file.seek(k*data_bytes*heat_steplength,0)
        ##---use signed int32 to load unsigned int32 data, 
        ##---otherwise, you will have error when computer the diffrential data
        heat_sampledata = np.fromfile(heat_file, dtype=np.dtype('<u4'), count=heat_samplelength).astype(np.dtype('<i4'))
        max_index = np.argmax(heat_sampledata)
        ##--最大值小于一个滤波窗口长度，跳过
        if max_index + 1 + k*heat_steplength < heat_peakpos:
            continue
        if heat_tot_length - (max_index + 1 + k*heat_steplength) < heat_length-heat_peakpos:
            continue
        ##--最大值在截取窗口两端，跳过
        if max_index + 1 == heat_samplelength or max_index == 0:
            continue
        ##--重复触发，跳过
        if max_index + 1 + k*heat_steplength == heat_trigpos_raw:
            continue
        heat_trigpos_raw = max_index + 1 + k*heat_steplength
        
        ##---以得到的最大值位置为中心，截取一个滤波窗口数据进行滤波
        heat_file.seek(data_bytes*(heat_trigpos_raw - heat_peakpos),0)
        heat_data = np.fromfile(heat_file, dtype=np.dtype('<u4'), count=(heat_length)).astype(np.dtype('<i4'))
        heat_diffdata = np.append(np.diff(heat_data),0)
        heat_diffdata_2t = np.concatenate((np.zeros(heat_length//2),heat_win*heat_diffdata,np.zeros(heat_length//2)), axis=0)
        heat_data_OF = np.real(np.fft.ifft(np.fft.fft(heat_diffdata_2t)*heat_OF_2f))

        heat_peakpos_tmp = 0
        heat_peakpos_tmp = np.argmax(heat_data_OF[heat_length//2+heat_peakpos-heat_peakvalley_length//2:heat_length//2+heat_peakpos+heat_peakvalley_length//2])
        if heat_peakpos_tmp + 1 == (heat_peakvalley_length//2)*2 or heat_peakpos_tmp == 0:
            continue
        heat_peakpos_tmp += heat_length//2+heat_peakpos-heat_peakvalley_length//2
        '''
        heat_peakpos_tmp = 0
        heat_peakpos_tmp = np.argmax(heat_data_OF[heat_length//2+heat_peakpos-heat_samplelength//2:heat_length//2+heat_peakpos+heat_samplelength//2])
        if heat_peakpos_tmp + 1 == (heat_samplelength//2)*2 or heat_peakpos_tmp == 0:
            continue
        heat_peakpos_tmp += heat_length//2+heat_peakpos-heat_samplelength//2*2
        '''
        if heat_peakpos_tmp + heat_trigpos_raw - heat_peakpos - heat_length//2 == heat_trigpos_fil:
            continue
        heat_trigpos_fil = heat_peakpos_tmp + heat_trigpos_raw - heat_peakpos-heat_length//2
        ###----light conincidence
        ###---##########-----------
        if heat_trigpos_fil + offset < light_peakpos:
            continue
        ###---##########-----------
        
        heat_filamp = heat_data_OF[heat_peakpos_tmp]
        if heat_filamp < threshold:
            continue
        
        if heat_peakpos_tmp < heat_length//2+heat_peakpos:
            break_point = -(heat_peakpos_tmp - heat_length//2-heat_peakpos)
        else:
            break_point = 2*heat_length-(heat_peakpos_tmp - heat_length//2-heat_peakpos)
        heat_OF_template_shifted = np.concatenate((heat_OF_template_2t[break_point:heat_length*2],heat_OF_template_2t[0:break_point]),axis=0)
        heat_corre = np.corrcoef(heat_data_OF[heat_peakpos_tmp-heat_paralength:heat_peakpos_tmp+heat_paralength],heat_OF_template_center[heat_length-heat_paralength:heat_length+heat_paralength])[0,1]
        heat_corre_tmp = np.corrcoef(heat_data_OF[heat_peakpos_tmp-heat_peakvalley_length:heat_peakpos_tmp+heat_peakvalley_length],heat_OF_template_center[heat_length-heat_peakvalley_length:heat_length+heat_peakvalley_length])[0,1]
        #heat_corre_tmp = np.corrcoef(heat_data_OF[heat_peakpos_tmp-heat_peakvalley_length:heat_peakpos_tmp+heat_peakvalley_length], heat_OF_template_center[heat_length-heat_peakvalley_length:heat_length+heat_peakvalley_length])[0,1]
        #if(heat_corre_tmp < 0.8 or abs(heat_corre_tmp-heat_corre) > 0.5):
        #if(abs(heat_corre_tmp-heat_corre) > 0.5):
        #    continue
        if heat_corre < heat_correreject:
            continue
        
        heat_tvl = np.sum((heat_data_OF[heat_peakpos_tmp-heat_paralength:heat_peakpos_tmp]-heat_filamp*heat_OF_template_center[heat_length-heat_paralength:heat_length])**2)/heat_paralength
        heat_tvr = np.sum((heat_data_OF[heat_peakpos_tmp:heat_peakpos_tmp+heat_paralength]-heat_filamp*heat_OF_template_center[heat_length:heat_length+heat_paralength])**2)/heat_paralength
        heat_tv = heat_tvl + heat_tvr
        #heat_tv = np.sum((heat_data_OF[heat_peakpos_tmp-heat_paralength:heat_peakpos_tmp+heat_paralength]-heat_filamp*heat_OF_template_center[heat_length-heat_paralength:heat_length+heat_paralength])**2)/heat_paralength/2
        #heat_data #heat_length*1, peak at heat_peakpos
        #heat_diffdata #heat_length*1, 
        #heat_data_OF #heat_length*2, peak at heat_peakpos_tmp

        heat_baseline = np.mean(heat_data[0:heat_peakpos-4*heat_ref_rt])
        heat_baselineRMS = np.std(heat_data[0:heat_peakpos-4*heat_ref_rt])

        ##---fit baseline
        [heat_baseline_slope,heat_fitted_baseline] = np.polyfit(np.arange(heat_peakpos-4*heat_ref_rt)-heat_peakpos+4*heat_ref_rt+1,heat_data[0:heat_peakpos-4*heat_ref_rt],1)
        #[heat_baseline_slope,heat_fitted_baseline] = np.polyfit(np.arange(heat_peakpos-4*heat_ref_rt),heat_data[0:heat_peakpos-4*heat_ref_rt],1)
        [heat_fitted_rawamp,heat_fitted_baseline] = np.polyfit(heat_signaltemplate[heat_peakpos-2*heat_ref_rt:heat_peakpos+3*heat_ref_dt],heat_data[heat_peakpos-2*heat_ref_rt:heat_peakpos+3*heat_ref_dt],1)
        
        heat_data_norm = heat_data - heat_fitted_baseline
        heat_rawamp = heat_data_norm[heat_peakpos]#-heat_fitted_baseline
        heat_chi2_raw = np.sum((heat_data_norm-heat_fitted_rawamp*heat_signaltemplate)**2)/heat_length
        heat_data_norm = heat_data_norm/heat_rawamp
        
        heat_dt = 0
        heat_rt = 0
        rise_start = 0
        rise_end = 0
        decay_end = 0
        decay_start = 0
        for i in reversed(heat_data_norm[heat_peakpos-4*heat_ref_rt:heat_peakpos]):
            rise_start += 1
            if i < 0.9:
                if i < 0.1:
                    break
                heat_rt+=1
            else:
                rise_end += 1
        if heat_data_norm[heat_peakpos-rise_end+1] == heat_data_norm[heat_peakpos-rise_end]:
            heat_rt += 0.5
        else:
            heat_rt += (0.9 - heat_data_norm[heat_peakpos-rise_end])/(heat_data_norm[heat_peakpos-rise_end+1] - heat_data_norm[heat_peakpos-rise_end])
        if heat_data_norm[heat_peakpos-rise_start+2] == heat_data_norm[heat_peakpos-rise_start+1]:
            heat_rt += 0.5
        else:
            heat_rt += (heat_data_norm[heat_peakpos-rise_start+2]-0.1)/(heat_data_norm[heat_peakpos-rise_start+2] - heat_data_norm[heat_peakpos-rise_start+1])
        
        for i in heat_data_norm[heat_peakpos:heat_peakpos+3*heat_ref_dt]:
            decay_end += 1
            if i < 0.9:
                if i < 0.3:
                    break
                heat_dt+=1
            else:
                decay_start += 1
        heat_dt += (heat_data_norm[heat_peakpos+decay_end-2]-0.3)
        if heat_data_norm[heat_peakpos+decay_end-2] == heat_data_norm[heat_peakpos+decay_end-1]:
            heat_dt += 0.5
        else:
            heat_dt += (heat_data_norm[heat_peakpos+decay_end-2]-0.3)/(heat_data_norm[heat_peakpos+decay_end-2] - heat_data_norm[heat_peakpos+decay_end-1])
        heat_dt += (0.9-heat_data_norm[heat_peakpos+decay_start])
        if heat_data_norm[heat_peakpos+decay_start-1] == heat_data_norm[heat_peakpos+decay_start]:
            heat_dt += 0.5
        else:
            heat_dt += (0.9-heat_data_norm[heat_peakpos+decay_start])/(heat_data_norm[heat_peakpos+decay_start-1] - heat_data_norm[heat_peakpos+decay_start])
        heat_rt /= fs
        heat_dt /= fs

        heat_SI = np.sum((heat_data_OF[heat_peakpos_tmp-heat_paralength:heat_peakpos_tmp+heat_paralength]-heat_filamp*heat_OF_template_center[heat_length-heat_paralength:heat_length+heat_paralength])**2)/(heat_paralength*2-2)/heat_sigmaL2/heat_length**2

        heat_meantime = np.sum(np.arange(heat_length)[heat_peakpos-2*heat_ref_rt:heat_peakpos+4*heat_ref_dt]*heat_data_norm[heat_peakpos-2*heat_ref_rt:heat_peakpos+4*heat_ref_dt])-heat_meantime_template
        heat_delayamp = np.mean(heat_data_norm[heat_peakpos:heat_peakpos+heat_peakvalley_length])
        heat_rawarea = np.trapezoid(heat_data_norm[heat_peakpos-2*heat_ref_rt:heat_peakpos+4*heat_ref_dt])
        heat_filarea = np.trapezoid(heat_data_OF[heat_peakpos_tmp-heat_paralength:heat_peakpos_tmp+heat_paralength]/heat_filamp)

        '''
        print('Trigger position:',heat_trigpos_fil)
        print('Baseline:')
        print(heat_data[0])
        print(heat_baseline)
        print(heat_fitted_baseline)
        print(heat_peakpos)
        print(np.argmax(heat_data)+1)
        print('Amplitude:')
        print(heat_fitted_rawamp)
        print(heat_rawamp)
        print(heat_filamp)
        
        print(heat_rt)
        print(heat_dt)
        print(heat_SI)
        print(heat_corre_tmp)
        print(heat_corre)
        break_i += 1
        if break_i == 6:
            break
        '''
        list_heat_trigpos_fil.append(heat_trigpos_fil)
        list_heat_filamp.append(heat_filamp)
        list_heat_baseline.append(heat_baseline)
        list_heat_baselineRMS.append(heat_baselineRMS)
        list_heat_tv.append(heat_tv)
        list_heat_tvr.append(heat_tvr)
        list_heat_baseline_slope.append(heat_baseline_slope)
        list_heat_fitted_rawamp.append(heat_fitted_rawamp)
        list_heat_dt.append(heat_dt )
        list_heat_rawarea.append(heat_rawarea)
        list_heat_filarea.append(heat_filarea)
        list_heat_rawamp.append(heat_rawamp)
        list_heat_corre.append(heat_corre)
        list_heat_tvl.append(heat_tvl)
        list_heat_SI.append(heat_SI)
        list_heat_fitted_baseline.append(heat_fitted_baseline)
        list_heat_rt.append(heat_rt)
        list_heat_delayamp.append(heat_delayamp)
        list_heat_meantime.append(heat_meantime)
        list_heat_corre_narrow.append(heat_corre_tmp)
        
        ##---以得到的最大值位置为中心，截取一个滤波窗口数据进行滤波
        light_file.seek(data_bytes*(heat_trigpos_fil+offset - light_peakpos),0)
        light_data = np.fromfile(light_file, dtype=np.dtype('<u4'), count=(light_length)).astype(np.dtype('<i4'))
        light_diffdata = np.append(np.diff(light_data),0)
        light_diffdata_2t = np.concatenate((np.zeros(light_length//2),light_win*light_diffdata,np.zeros(light_length//2)), axis=0)
        light_data_OF = np.real(np.fft.ifft(np.fft.fft(light_diffdata_2t)*light_OF_2f))

        light_peakpos_tmp = 0
        light_peakpos_tmp = np.argmax(light_data_OF[light_length//2+light_peakpos-light_peakvalley_length//2:light_length//2+light_peakpos+light_peakvalley_length//2])
        light_peakpos_tmp += light_length//2+light_peakpos-light_peakvalley_length//2
        light_trigpos_fil = light_peakpos_tmp + heat_trigpos_fil+offset - light_peakpos-light_length//2
        
        light_filamp = light_data_OF[light_peakpos_tmp]
        
        if light_peakpos_tmp < light_length//2+light_peakpos:
            break_point = -(light_peakpos_tmp - light_length//2-light_peakpos)
        else:
            break_point = 2*light_length-(light_peakpos_tmp - light_length//2-light_peakpos)
        light_OF_template_shifted = np.concatenate((light_OF_template_2t[break_point:light_length*2],light_OF_template_2t[0:break_point]),axis=0)
        light_corre = np.corrcoef(light_data_OF[light_peakpos_tmp-light_paralength:light_peakpos_tmp+light_paralength],light_OF_template_center[light_length-light_paralength:light_length+light_paralength])[0,1]
        light_corre_tmp = np.corrcoef(light_data_OF[light_peakpos_tmp-light_peakvalley_length:light_peakpos_tmp+light_peakvalley_length],light_OF_template_center[light_length-light_peakvalley_length:light_length+light_peakvalley_length])[0,1]
        #light_corre_tmp = np.corrcoef(light_data_OF[light_peakpos_tmp-light_peakvalley_length:light_peakpos_tmp+light_peakvalley_length], light_OF_template_center[light_length-light_peakvalley_length:light_length+light_peakvalley_length])[0,1]
        #if(light_corre_tmp < 0.8 or abs(light_corre_tmp-light_corre) > 0.5):
        #if(abs(light_corre_tmp-light_corre) > 0.5):
        #    continue
        
        light_tvl = np.sum((light_data_OF[light_peakpos_tmp-light_paralength:light_peakpos_tmp]-light_filamp*light_OF_template_center[light_length-light_paralength:light_length])**2)/light_paralength
        light_tvr = np.sum((light_data_OF[light_peakpos_tmp:light_peakpos_tmp+light_paralength]-light_filamp*light_OF_template_center[light_length:light_length+light_paralength])**2)/light_paralength
        light_tv = light_tvl + light_tvr
        #light_tv = np.sum((light_data_OF[light_peakpos_tmp-light_paralength:light_peakpos_tmp+light_paralength]-light_filamp*light_OF_template_center[light_length-light_paralength:light_length+light_paralength])**2)/light_paralength/2
        #light_data #light_length*1, peak at light_peakpos
        #light_diffdata #light_length*1, 
        #light_data_OF #light_length*2, peak at light_peakpos_tmp

        light_baseline = np.mean(light_data[0:light_peakpos-4*light_ref_rt])
        light_baselineRMS = np.std(light_data[0:light_peakpos-4*light_ref_rt])

        ##---fit baseline
        [light_baseline_slope,light_fitted_baseline] = np.polyfit(np.arange(light_peakpos-4*light_ref_rt)-light_peakpos+4*light_ref_rt+1,light_data[0:light_peakpos-4*light_ref_rt],1)
        #[light_baseline_slope,light_fitted_baseline] = np.polyfit(np.arange(light_peakpos-4*light_ref_rt),light_data[0:light_peakpos-4*light_ref_rt],1)
        [light_fitted_rawamp,light_fitted_baseline] = np.polyfit(light_signaltemplate[light_peakpos-2*light_ref_rt:light_peakpos+3*light_ref_dt],light_data[light_peakpos-2*light_ref_rt:light_peakpos+3*light_ref_dt],1)
        
        light_data_norm = light_data - light_fitted_baseline
        light_rawamp = light_data_norm[light_peakpos]#-light_fitted_baseline
        light_chi2_raw = np.sum((light_data_norm-light_fitted_rawamp*light_signaltemplate)**2)/light_length
        light_data_norm = light_data_norm/light_rawamp
        
        light_dt = 0
        light_rt = 0
        rise_start = 0
        rise_end = 0
        decay_end = 0
        decay_start = 0
        for i in reversed(light_data_norm[light_peakpos-4*light_ref_rt:light_peakpos]):
            rise_start += 1
            if i < 0.9:
                if i < 0.1:
                    break
                light_rt+=1
            else:
                rise_end += 1
        if light_data_norm[light_peakpos-rise_end+1] == light_data_norm[light_peakpos-rise_end]:
            light_rt += 0.5
        else:
            light_rt += (0.9 - light_data_norm[light_peakpos-rise_end])/(light_data_norm[light_peakpos-rise_end+1] - light_data_norm[light_peakpos-rise_end])
        if light_data_norm[light_peakpos-rise_start+2] == light_data_norm[light_peakpos-rise_start+1]:
            light_rt += 0.5
        else:
            light_rt += (light_data_norm[light_peakpos-rise_start+2]-0.1)/(light_data_norm[light_peakpos-rise_start+2] - light_data_norm[light_peakpos-rise_start+1])
        
        for i in light_data_norm[light_peakpos:light_peakpos+3*light_ref_dt]:
            decay_end += 1
            if i < 0.9:
                if i < 0.3:
                    break
                light_dt+=1
            else:
                decay_start += 1
        light_dt += (light_data_norm[light_peakpos+decay_end-2]-0.3)
        if light_data_norm[light_peakpos+decay_end-2] == light_data_norm[light_peakpos+decay_end-1]:
            light_dt += 0.5
        else:
            light_dt += (light_data_norm[light_peakpos+decay_end-2]-0.3)/(light_data_norm[light_peakpos+decay_end-2] - light_data_norm[light_peakpos+decay_end-1])
        light_dt += (0.9-light_data_norm[light_peakpos+decay_start])
        if light_data_norm[light_peakpos+decay_start-1] == light_data_norm[light_peakpos+decay_start]:
            light_dt += 0.5
        else:
            light_dt += (0.9-light_data_norm[light_peakpos+decay_start])/(light_data_norm[light_peakpos+decay_start-1] - light_data_norm[light_peakpos+decay_start])
        light_rt /= fs
        light_dt /= fs

        light_SI = np.sum((light_data_OF[light_peakpos_tmp-light_paralength:light_peakpos_tmp+light_paralength]-light_filamp*light_OF_template_center[light_length-light_paralength:light_length+light_paralength])**2)/(light_paralength*2-2)/light_sigmaL2/light_length**2

        light_meantime = np.sum(np.arange(light_length)[light_peakpos-2*light_ref_rt:light_peakpos+4*light_ref_dt]*light_data_norm[light_peakpos-2*light_ref_rt:light_peakpos+4*light_ref_dt])-light_meantime_template
        light_delayamp = np.mean(light_data_norm[light_peakpos:light_peakpos+light_peakvalley_length])
        light_rawarea = np.trapezoid(light_data_norm[light_peakpos-2*light_ref_rt:light_peakpos+4*light_ref_dt])
        light_filarea = np.trapezoid(light_data_OF[light_peakpos_tmp-light_paralength:light_peakpos_tmp+light_paralength]/light_filamp)

        '''
        print('Trigger position:',light_trigpos_fil)
        print('Baseline:')
        print(light_data[0])
        print(light_baseline)
        print(light_fitted_baseline)
        print(light_peakpos)
        print(np.argmax(light_data)+1)
        print('Amplitude:')
        print(light_fitted_rawamp)
        print(light_rawamp)
        print(light_filamp)
        
        print(light_rt)
        print(light_dt)
        print(light_SI)
        print(light_corre_tmp)
        print(light_corre)
        break_i += 1
        if break_i == 6:
            break
        '''
        list_light_trigpos_fil.append(light_trigpos_fil)
        list_light_filamp.append(light_filamp)
        list_light_baseline.append(light_baseline)
        list_light_baselineRMS.append(light_baselineRMS)
        list_light_tv.append(light_tv)
        list_light_tvr.append(light_tvr)
        list_light_baseline_slope.append(light_baseline_slope)
        list_light_fitted_rawamp.append(light_fitted_rawamp)
        list_light_dt.append(light_dt )
        list_light_rawarea.append(light_rawarea)
        list_light_filarea.append(light_filarea)
        list_light_rawamp.append(light_rawamp)
        list_light_corre.append(light_corre)
        list_light_tvl.append(light_tvl)
        list_light_SI.append(light_SI)
        list_light_fitted_baseline.append(light_fitted_baseline)
        list_light_rt.append(light_rt)
        list_light_delayamp.append(light_delayamp)
        list_light_meantime.append(light_meantime)
        list_light_corre_narrow.append(light_corre_tmp)

    '''
    fig, ax = plt.subplots(nrows=1, ncols=1)
    ax.plot(np.arange(2*heat_length)/fs, heat_data_OF, c='r', label='OF_data_2t')
    ax.plot(np.arange(2*heat_length)/fs, heat_OF_template_shifted*heat_filamp, c='g', label='OF_template_2t')
    ax.plot(np.arange(heat_length)/fs+heat_length//2/fs, heat_data-heat_data[0], c='b', label='Data_2t')
    #ax.plot(np.arange(heat_length)/fs+heat_length//2/fs, heat_data_norm*heat_filamp, c='b', label='Data_2t')
    #ax.plot(np.arange(2*heat_length)/fs, heat_diffdata, c='b', label='Diffdata_2t')
    ax.legend()
    ax.grid(True)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Height')
    #ax.set_title(r'Histogram of Baseline: $\sigma$={0:.2f}keV'.format(abs(popt4[2])))
    plt.show()

    '''
    arr_heat_trigpos_fil = np.array(list_heat_trigpos_fil)
    arr_heat_rawamp = np.array(list_heat_rawamp)
    arr_heat_filamp = np.array(list_heat_filamp)
    arr_heat_baseline = np.array(list_heat_baseline)
    arr_heat_baselineRMS = np.array(list_heat_baselineRMS)
    arr_heat_corre = np.array(list_heat_corre)
    arr_heat_tv  = np.array(list_heat_tv)
    arr_heat_tvl = np.array(list_heat_tvl)
    arr_heat_tvr = np.array(list_heat_tvr)
    arr_heat_SI = np.array(list_heat_SI)
    arr_heat_baseline_slope = np.array(list_heat_baseline_slope)
    arr_heat_fitted_baseline = np.array(list_heat_fitted_baseline)
    arr_heat_fitted_rawamp = np.array(list_heat_fitted_rawamp)
    arr_heat_rt = np.array(list_heat_rt)
    arr_heat_dt = np.array(list_heat_dt)
    arr_heat_delayamp = np.array(list_heat_delayamp)
    arr_heat_meantime = np.array(list_heat_meantime)
    arr_heat_rawarea = np.array(list_heat_rawarea)
    arr_heat_filarea = np.array(list_heat_filarea)
    arr_heat_corre_narrow = np.array(list_heat_corre_narrow)
    arr_light_trigpos_fil = np.array(list_light_trigpos_fil)
    arr_light_rawamp = np.array(list_light_rawamp)
    arr_light_filamp = np.array(list_light_filamp)
    arr_light_baseline = np.array(list_light_baseline)
    arr_light_baselineRMS = np.array(list_light_baselineRMS)
    arr_light_corre = np.array(list_light_corre)
    arr_light_tv  = np.array(list_light_tv)
    arr_light_tvl = np.array(list_light_tvl)
    arr_light_tvr = np.array(list_light_tvr)
    arr_light_SI = np.array(list_light_SI)
    arr_light_baseline_slope = np.array(list_light_baseline_slope)
    arr_light_fitted_baseline = np.array(list_light_fitted_baseline)
    arr_light_fitted_rawamp = np.array(list_light_fitted_rawamp)
    arr_light_rt = np.array(list_light_rt)
    arr_light_dt = np.array(list_light_dt)
    arr_light_delayamp = np.array(list_light_delayamp)
    arr_light_meantime = np.array(list_light_meantime)
    arr_light_rawarea = np.array(list_light_rawarea)
    arr_light_filarea = np.array(list_light_filarea)
    arr_light_corre_narrow = np.array(list_light_corre_narrow)

    eventfile_heat = uproot.recreate(heat_path+"data/heat2.root")
    eventfile_heat["tree1"] = {"trigpos":arr_heat_trigpos_fil,"rawamp":arr_heat_rawamp,"filamp":arr_heat_filamp,"baseline":arr_heat_baseline,"baselineRMS":arr_heat_baselineRMS,"correlation":arr_heat_corre,"tv":arr_heat_tv,"tvl":arr_heat_tvl,"tvr":arr_heat_tvr,"SI":arr_heat_SI,"baseline_slope":arr_heat_baseline_slope,"fitted_baseline":arr_heat_fitted_baseline,"fitted_rawamp":arr_heat_fitted_rawamp,"risetime":arr_heat_rt,"decaytime":arr_heat_dt,"delayamp":arr_heat_delayamp,"meantime":arr_heat_meantime,"rawarea":arr_heat_rawarea,"filarea":arr_heat_filarea,"correlation_narrow":arr_heat_corre_narrow}
    eventfile_light = uproot.recreate(heat_path+"data/light2.root")
    eventfile_light["tree1"] = {"trigpos":arr_light_trigpos_fil,"rawamp":arr_light_rawamp,"filamp":arr_light_filamp,"baseline":arr_light_baseline,"baselineRMS":arr_light_baselineRMS,"correlation":arr_light_corre,"tv":arr_light_tv,"tvl":arr_light_tvl,"tvr":arr_light_tvr,"SI":arr_light_SI,"baseline_slope":arr_light_baseline_slope,"fitted_baseline":arr_light_fitted_baseline,"fitted_rawamp":arr_light_fitted_rawamp,"risetime":arr_light_rt,"decaytime":arr_light_dt,"delayamp":arr_light_delayamp,"meantime":arr_light_meantime,"rawarea":arr_light_rawarea,"filarea":arr_light_filarea,"correlation_narrow":arr_light_corre_narrow}

    print("done")
    return

_trigger()
