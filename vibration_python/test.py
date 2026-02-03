import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# 创建文件选择对话框
def choose_file():
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择数据文件",
        filetypes=[("文本文件", "*.txt")]
    )
    return file_path

# 用于去掉单位（如 '(s)'）并转换为浮动数据，确保数据有效
def remove_units(x):
    try:
        # 去除单位并尝试转换为浮动数值
        return float(x.replace('(s)', '').replace('(V)', '').strip())
    except ValueError:
        # 如果转换失败，返回 np.nan（NaN表示无效值）
        return np.nan

# 读取文件并绘制频谱
def plot_frequency_spectrum(file_path):
    # 使用 pandas 读取文件，跳过无效的行，使用 converters 去掉单位
    data = pd.read_csv(file_path, sep="\t", skiprows=1, header=None, 
                       converters={0: remove_units, 1: remove_units})

    # 删除任何包含 NaN 的行
    data.dropna(inplace=True)

    # 提取时间和信号数据
    time_data = data[0].values  # 第一列为时间数据
    signal_data = data[1].values  # 第二列为信号数据

    # 计算采样率（从时间数据推算）
    sampling_rate = 1 / (time_data[1] - time_data[0])

    # 进行快速傅里叶变换（FFT）
    n = len(signal_data)
    fft_values = np.fft.fft(signal_data)
    fft_freq = np.fft.fftfreq(n, d=(time_data[1] - time_data[0]))

    # 绘制第一个频谱图（从0.1Hz开始）
    plt.figure(figsize=(10, 6))
    plt.plot(fft_freq[:n//2], np.abs(fft_values)[:n//2])  # 只绘制正频率部分
    plt.title('Frequency Spectrum (0.1 Hz start)')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude (dB)')
    plt.xlim(0.1, max(fft_freq[:n//2]))  # 设置横轴从0.1Hz开始
    plt.ylim(0.1, 50000)  # 设置纵轴从0.1开始
    plt.grid(True)

    # 绘制第二个频谱图（从0Hz到100Hz）
    plt.figure(figsize=(10, 6))
    plt.plot(fft_freq[:n//2], np.abs(fft_values)[:n//2])  # 只绘制正频率部分
    plt.title('Frequency Spectrum (0-100 Hz)')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude (dB)')
    plt.xlim(0, 100)  # 设置横轴从0Hz到100Hz
    plt.ylim(0.1, 50000)  # 设置纵轴从0.1开始
    plt.grid(True)

    # 显示两个图
    plt.show()

# 选择文件并绘制图像
file_path = choose_file()
if file_path:
    plot_frequency_spectrum(file_path)