# ============================================================
# 本代码用于批量读取多个 CSV 文件，计算它们的加速度 PSD，
# 自动识别文件中的采样率与增益，进行分帧、加窗、FFT、
# 求平均 PSD，最终以 LPSD (√PSD) 形式在同一张图中对比。
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import re

# ===================== 文件选择 =====================
root = Tk()
root.withdraw()  # 隐藏 Tk 主窗口
file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])

if not file_paths:
    exit()  # 用户没有选择文件

# 用于记录图例
legends = []

# ===================== 遍历所有文件 =====================
for file_path in file_paths:
    filename = os.path.basename(file_path)

    # 读 CSV（跳4行表头，只取第2列：电压）
    data = np.loadtxt(file_path, delimiter=',', skiprows=4)
    data = data[:, 1]

    # ===================== PSD 参数 =====================
    sen = 1.026    # 灵敏度 V/g
    g = 9.81       # 重力加速度
    wint = 5       # PSD 窗长度（秒）
    gain = 10.003  # 默认增益
    fs = 10000     # 默认采样率

    # ===================== 根据文件名判断增益 =====================
    if "1gain" in filename:
        gain = 1
    elif "10gain" in filename:
        gain = 10.003
    elif "100gain" in filename:
        gain = 100.122

    # ===================== 文件名提取采样率 fs =====================
    match = re.search(r"(\d+)fs", filename)
    if match:
        fs = int(match.group(1))

    # ===================== PSD 分帧参数 =====================
    window_size = int(wint * fs)
    nfft = 2 ** int(np.ceil(np.log2(window_size)))  # NFFT 取最近的 2^n
    overlap = nfft // 2
    f = np.linspace(0, fs/2, nfft//2, endpoint=False)

    # ===================== 电压 → g =====================
    data = data / (gain * sen)

    # ===================== Hanning 窗并归一化 =====================
    window = get_window("hann", window_size)
    window = window / np.sqrt(np.mean(window**2))   # 能量归一化

    # ===================== 将信号按步长分帧 =====================
    step = window_size - overlap
    shape = ((len(data) - overlap) // step, window_size)
    strides = (data.strides[0]*step, data.strides[0])
    framed = np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)

    # 每帧乘窗函数
    framed = framed * window

    # ===================== PSD 计算 =====================
    psd = np.zeros((nfft//2, framed.shape[0]))
    for j in range(framed.shape[0]):
        fft_data = fft(framed[j], nfft)
        psd_segment = np.abs(fft_data[:nfft//2])**2 / (fs * nfft)
        psd_segment[1:-1] *= 2  # 除 DC 和 Nyquist，双边→单边
        psd[:, j] = psd_segment

    # 对所有帧取平均 PSD
    psd_avg = np.mean(psd, axis=1)

    # ===================== 绘图：LPSD（√PSD） =====================
    plt.loglog(f, np.sqrt(psd_avg), label=os.path.splitext(filename)[0])
    plt.grid(True)

# ===================== 图形设置 =====================
plt.xlabel("Frequency (Hz)", fontsize=14)
plt.ylabel(r"PSD [$g/\sqrt{Hz}$]", fontsize=14)
plt.title("Power Spectrum Density", fontsize=16)
plt.legend(fontsize=10, loc="upper right")
plt.tight_layout()
plt.show()
