import matplotlib.pyplot as plt
import numpy as np
from scipy.fftpack import fft
import tkinter as tk
from tkinter import filedialog
import time
import pandas as pd

# 打开文件选择对话框
root = tk.Tk()
root.withdraw()
file_path = filedialog.askopenfilename(filetypes=[("Two Column CSV", "*.csv")])
print(file_path)

# 加载并清洗数据
tic = time.perf_counter()
df = pd.read_csv(file_path, header=0, low_memory=False)

# 将前两列转换为浮点数，非数字设为 NaN
t = pd.to_numeric(df.iloc[:, 0], errors='coerce')
x = pd.to_numeric(df.iloc[:, 1], errors='coerce')

# 删除包含 NaN 的行
valid = (~t.isna()) & (~x.isna())
t = t[valid].to_numpy()
x = x[valid].to_numpy()

toc = time.perf_counter()
print("Load Time:", toc - tic)

# 检查采样点数量是否合理
N = len(t)
if N < 2 or t[1] == t[0]:
    raise ValueError("Time data is invalid or too short for sampling rate calculation.")

Fs = 1 / (t[1] - t[0])  # 采样频率
T = 1 / Fs              # 采样周期
print("# Samples:", N)
print("Sampling Rate (Hz):", Fs)

# 绘制时域图像
tic = time.perf_counter()
plt.figure(1)
plt.plot(t, x)
plt.xlabel('Time (seconds)')
plt.ylabel('Accel (g)')
plt.title(file_path)
plt.grid()
toc = time.perf_counter()
print("Plot Time:", toc - tic)

# 计算并绘制 RMS
tic = time.perf_counter()
w = int(np.floor(Fs))  # 1 秒窗口
steps = int(np.floor(N / w))
t_RMS = np.zeros((steps, 1))
x_RMS = np.zeros((steps, 1))
for i in range(steps):
    t_RMS[i] = np.mean(t[i * w:(i + 1) * w])
    x_RMS[i] = np.sqrt(np.mean(x[i * w:(i + 1) * w] ** 2))

plt.figure(2)
plt.plot(t_RMS, x_RMS)
plt.xlabel('Time (seconds)')
plt.ylabel('RMS Accel (g)')
plt.title('RMS - ' + file_path)
plt.grid()
toc = time.perf_counter()
print("RMS Time:", toc - tic)

# 计算并绘制 FFT
tic = time.perf_counter()
plt.figure(3)
xf = np.linspace(0.0, 1.0 / (2.0 * T), N // 2)
yf = fft(x)
plt.plot(xf, 2.0 / N * np.abs(yf[0:N // 2]))
plt.grid()
plt.xlabel('Frequency (Hz)')
plt.ylabel('Accel (g)')
plt.title('FFT - ' + file_path)
toc = time.perf_counter()
print("FFT Time:", toc - tic)

# 展示所有图
plt.show()
