import numpy as np
import sys
import math 
import time
import matplotlib.pyplot as plt
np.random.seed(19680801)
def _resolution():
    time_raw = np.loadtxt('../data/time_12hour_0.8Hz_40sigma.txt',dtype=float)
    energy_raw = 2.52429*np.loadtxt('../data/energy_12hour_0.8Hz_40sigma.txt',dtype=float)
    print(energy_raw.shape)
    triggered = np.loadtxt('./triggered_events.txt',dtype=float,delimiter=',',usecols=(0,1,2))
    time_triggered = triggered[:,0]
    energy_triggered_filter = triggered[:,1]
    energy_triggered_rawfit = triggered[:,2]
    i = 0
    ii = 0
    energy_triggered_raw_list = []
    exit_flag = False
    wrong_trigger_list = []
    for ii in range(0,time_triggered.shape[0]): 
        time_data = time_triggered[ii]
        while time_raw[i] < time_data:
            if math.fabs(time_data-time_raw[i]) < 0.5:
                energy_triggered_raw_list.append(energy_raw[i])
                exit_flag = True
                break
            i += 1
        if exit_flag:
            exit_flag = False
            continue
        energy_triggered_raw_list.append(0.0)
        print(f'Wrong trigger:\t%.3f\t%.3f'%(time_data,energy_triggered_filter[ii]))
        wrong_trigger_list.append(energy_triggered_filter[ii])
    i = 0
    miss_trigger_list = []
    for ii in range(0,time_raw.shape[0]): 
        time_data = time_raw[ii]
        if i > 10:
            i = i-10
        if i > time_triggered.shape[0]-1:
            break
        while time_triggered[i]-2.0 < time_data:
            if math.fabs(time_data-time_triggered[i]) < 0.5:
                exit_flag = True
                break
            i += 1
            if i > time_triggered.shape[0]-1:
                break
        if exit_flag:
            exit_flag = False
            continue
        print(f'Miss trigger:\t{time_data:f}\t{energy_raw[ii]:f}')
        miss_trigger_list.append(energy_raw[ii])
    '''
    '''
    energy_triggered_raw = np.array(energy_triggered_raw_list)
    length = energy_triggered_raw.shape[0]
    print(length)
    Nbin = 40
    Emax = 40*2.52459
    energy_fixed = (np.arange(Nbin))/Nbin*Emax
    #print(energy_fixed)
    num_arr = np.zeros(Nbin)
    energy_rawfit_mean = np.zeros(Nbin)
    energy_filter_mean = np.zeros(Nbin)
    energy_rawfit_sigma = np.zeros(Nbin)
    energy_filter_sigma = np.zeros(Nbin)
    for i in range(0,Nbin):
        energy_filter_list = []
        energy_rawfit_list = []
        time_list = []
        for j in range(0,length):
            if math.fabs(energy_triggered_raw[j]-energy_fixed[i]) < 0.1:
                energy_filter_list.append(energy_triggered_filter[j])
                energy_rawfit_list.append(energy_triggered_rawfit[j])
                time_list.append(time_triggered[j])
        if time_list == []:
            continue
        energy_filter_arr = np.array(energy_filter_list)
        energy_rawfit_arr = np.array(energy_rawfit_list)
        time_arr = np.array(time_list)
        num_arr[i] += energy_filter_arr.shape[0]
        if i == 62:
            print(energy_fixed[i])
            np.savetxt('./tmp_rawfit.txt', energy_rawfit_arr, fmt='%f',delimiter=",")
            np.savetxt('./tmp_filter.txt', energy_filter_arr, fmt='%f',delimiter=",")
            np.savetxt('./tmp_time.txt', time_arr, fmt='%f',delimiter=",")
        energy_rawfit_mean[i] += np.mean(energy_rawfit_arr)
        energy_filter_mean[i] += np.mean(energy_filter_arr)
        energy_rawfit_sigma[i] += np.std(energy_rawfit_arr)
        energy_filter_sigma[i] += np.std(energy_filter_arr)
        #energy_rawfit_sigma[i] += math.sqrt(np.sum(np.power(energy_rawfit_arr-1000*energy_fixed[i],2))/num_arr[i])
        #energy_filter_sigma[i] += math.sqrt(np.sum(np.power(energy_filter_arr-1000*energy_fixed[i],2))/num_arr[i])
        del energy_filter_list
        del energy_rawfit_list
    num_raw_arr = np.zeros(Nbin)
    for i in range(0,Nbin):
        for j in range(0,energy_raw.shape[0]):
            if time_raw[j] > 43198.9:
                continue
            if math.fabs(energy_raw[j]-energy_fixed[i]) < 1.5:
                num_raw_arr[i] +=1
    fig, axs = plt.subplots()
    axs.plot(energy_fixed[1:]/2.52429, num_arr[1:]*100/num_raw_arr[1:],'o-', label="Trigger Num")
    np.savetxt('../data/energy_x.txt', energy_fixed[1:]/2.52429, fmt='%f',delimiter=",")
    np.savetxt('../data/tri_eff.txt', num_arr[1:]*100/num_raw_arr[1:], fmt='%f',delimiter=",")
    '''
    axs.plot(energy_fixed[5:]/2.52429, (energy_filter_mean[5:]-energy_fixed[5:])/energy_fixed[5:]*100, label="Filtered mean")
    axs.plot(energy_fixed[5:]/2.52429, (energy_rawfit_mean[5:]-energy_fixed[5:])/energy_fixed[5:]*100, label="Rawfit mean")
    np.savetxt('../data/energy_x.txt', energy_fixed[4:]/2.52429, fmt='%f',delimiter=",")
    np.savetxt('../data/energy_y_filter.txt', (energy_filter_mean[4:]-energy_fixed[4:])/energy_fixed[4:]*100, fmt='%f',delimiter=",")
    np.savetxt('../data/energy_y_rawfit.txt', (energy_rawfit_mean[4:]-energy_fixed[4:])/energy_fixed[4:]*100, fmt='%f',delimiter=",")
    axs.plot(energy_fixed/2.52429, energy_filter_sigma/2.52429, label="Filtered sigma")
    axs.plot(energy_fixed/2.52429, energy_rawfit_sigma/2.52429, label="Rawfit sigma")
    axs.plot(energy_fixed/2.52429, energy_filter_sigma/2.52429, label="Filtered sigma")
    axs.plot(energy_fixed/2.52429, energy_rawfit_sigma/2.52429, label="Rawfit sigma")
    axs.plot(energy_fixed, energy_filter_sigma, label="Filtered sigma")
    axs.plot(energy_fixed, energy_rawfit_sigma, label="Rawfit sigma")
    axs.plot(energy_fixed, num_arr, label="Trigger Num")
    axs.plot(energy_fixed, num_raw_arr, label="Raw Num")
    axs.plot(energy_fixed, energy_filter_sigma/energy_fixed*100, label="Filtered sigma")
    axs.plot(energy_fixed, energy_rawfit_sigma/energy_fixed*100, label="Rawfit sigma")
    axs.plot(energy_fixed, (energy_filter_mean-1000*energy_fixed)/energy_fixed/10, label="Filtered mean")
    axs.plot(energy_fixed, (energy_rawfit_mean-1000*energy_fixed)/energy_fixed/10, label="Rawfit mean")
    np.savetxt('../data/energy_y_filter.txt', energy_filter_sigma/2.52429, fmt='%f',delimiter=",")
    np.savetxt('../data/energy_y_rawfit.txt', energy_rawfit_sigma/2.52429, fmt='%f',delimiter=",")
    '''
    '''
    axs.plot(energy_triggered_raw, energy_triggered_rawfit, label="Rawfit")
    axs.plot(energy_triggered_raw, energy_triggered_filter, label="OF")
    '''
    axs.set_xlabel('Energy (MeV)')
    axs.set_ylabel('Mean value difference (%)')
    axs.grid(True)
    axs.legend()
    fig.tight_layout()
    plt.show()
    '''
    '''
    '''
    time_x2 = np.arange(t1*10000)
    fig2, axs2 = plt.subplots()
    #axs2.plot(time_x2, noise_y2, label="Time series")
    axs2.plot(time_x2, energy_y2, label="Time series")
    axs2.set_xlabel('Time (sample points)')
    axs2.set_ylabel('Amplitude')
    #axs2.set_ylabel('Energy')
    axs2.grid(True)
    axs2.legend()
    noise_ps = np.fft.fft(noise_time)
    noise_ps2 = np.real(noise_ps*noise_ps.conjugate())
    axs[1].plot(freq[:6000], noise_ps2[:6000])
    axs[1].plot(freq[:6000], noisepsd[:6000])
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    axs[1].set_xlabel('Frequency (Hz)')
    axs[1].set_ylabel('Arbitrary unit')
    '''

    return 
_resolution()
