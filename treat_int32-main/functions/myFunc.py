import numpy as np
from scipy.signal import bessel, filtfilt
from scipy.interpolate import interp1d, UnivariateSpline

def bessel_filter(x, fs, fc = 105, order = 8 ):
    Wn = fc / (fs/2)
    b, a = bessel(order, Wn, btype='low', analog=False, norm='phase')
    y = filtfilt(b, a, x)
    return y

def interpolateN(data, n):
    if n == 1:
        return data
    beforeT = np.arange(len(data)) * n
    afterT = np.arange(beforeT[-1])
    ff = interp1d(beforeT, data, kind='quadratic')
    
    return ff(afterT)