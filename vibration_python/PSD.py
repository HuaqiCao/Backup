import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import re

# 打开文件选择对话框
root = Tk()
root.withdraw()  # 隐藏主窗口
file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])

if not file_paths:
    exit()  # 用户取消

# 初始化图例列表
legends = []

# 遍历每个选定的文件
for file_path in file_paths:
    filename = os.path.basename(file_path)
    data = np.loadtxt(file_path, delimiter=',', skiprows=4)
    data = data[:, 1]  # 只取第2列

    # PSD 参数
    sen = 1.026  # 灵敏度 V/g
    g = 9.81     # m/s²
    wint = 5     # 窗口时长（秒）
    gain = 10.003  # 默认增益
    fs = 10000     # 默认采样率

    # 根据文件名确定增益
    if "1gain" in filename:
        gain = 1
    elif "10gain" in filename:
        gain = 10.003
    elif "100gain" in filename:
        gain = 100.122

    # 从文件名中提取 fs
    match = re.search(r"(\d+)fs", filename)
    if match:
        fs = int(match.group(1))

    window_size = int(wint * fs)
    nfft = 2 ** int(np.ceil(np.log2(window_size)))
    overlap = nfft // 2
    f = np.linspace(0, fs/2, nfft//2, endpoint=False)

    # 将数据从 V 转换为 g
    data = data / (gain * sen)

    # Hanning 窗函数并归一化
    window = get_window("hann", window_size)
    window = window / np.sqrt(np.mean(window**2))

    # 将数据分帧
    step = window_size - overlap
    shape = ((len(data) - overlap) // step, window_size)
    strides = (data.strides[0]*step, data.strides[0])
    framed = np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)

    # 应用窗函数
    framed = framed * window

    # PSD 计算
    psd = np.zeros((nfft//2, framed.shape[0]))
    for j in range(framed.shape[0]):
        fft_data = fft(framed[j], nfft)
        psd_segment = np.abs(fft_data[:nfft//2])**2 / (fs * nfft)
        psd_segment[1:-1] *= 2  # 除直流与 Nyquist
        psd[:, j] = psd_segment

    psd_avg = np.mean(psd, axis=1)

    # 画图
    plt.loglog(f, np.sqrt(psd_avg), label=os.path.splitext(filename)[0])
    plt.grid(True)

# 设置图例和标签
plt.xlabel("Frequency (Hz)", fontsize=14)
plt.ylabel(r"PSD [$g/\sqrt{Hz}$]", fontsize=14)
plt.title("Power Spectrum Density", fontsize=16)
plt.legend(fontsize=10, loc="upper right")
plt.tight_layout()
plt.show()
