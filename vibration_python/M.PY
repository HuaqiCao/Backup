import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import os

# =============================
# 手动设置两个文件的 Y 轴上限
# =============================
YMAX_FILE1 = 0.000002      # 第一个文件的纵轴上限（单位：V）
YMAX_FILE2 = 0.02        # 第二个文件的纵轴上限（单位：V）

# =============================
# 手动设置两个文件的 X 轴上限（频率范围 Hz）
# =============================
XMAX_FILE1 = 100           # 第一个文件的横轴最大频率
XMAX_FILE2 = 400           # 第二个文件的横轴最大频率
# 若想自动：设为 None 或 0
# =============================


def read_csv_with_header(path):
    """读取 CSV 文件（跳过前 4 行标题），返回时间(s)和信号(V)"""
    df = pd.read_csv(path, skiprows=4, header=None)
    t = df[0].values
    v = df[1].values
    return t, v


def compute_fft(time, signal):
    """对信号做 FFT，并返回频率与幅度谱"""
    N = len(signal)
    dt = time[1] - time[0]
    fs = 1.0 / dt

    fft_vals = np.fft.rfft(signal)
    fft_freq = np.fft.rfftfreq(N, dt)
    fft_amp = np.abs(fft_vals) * 2.0 / N  # 单边幅度谱

    return fft_freq, fft_amp, fs


def plot_fft(freq, amp, title, y_limit=None, x_limit=None, loglog=False):
    plt.figure(figsize=(10, 5))

    # ----------- 判断是否画 log-log ----------
    if loglog:
        plt.loglog(freq, amp, linewidth=1.0)
    else:
        plt.plot(freq, amp, linewidth=1.0)

    plt.xlabel("Frequency (Hz)", fontsize=12)
    plt.ylabel("Amplitude (V)", fontsize=12)
    plt.title(title, fontsize=14)
    plt.grid(True, which='both')

    # 横轴范围
    if x_limit is not None and x_limit > 0:
        plt.xlim(1e-6 if loglog else 0, x_limit)
    else:
        plt.xlim(1e-6 if loglog else 0, max(freq))

    # 纵轴范围
    if y_limit is not None and y_limit > 0:
        if loglog:
            plt.ylim(1e-12, y_limit)
        else:
            plt.ylim(0, y_limit)

    plt.tight_layout()
    plt.show()


# ============================
# 主程序：选择两个文件 + 绘图
# ============================

root = Tk()
root.withdraw()

file_paths = filedialog.askopenfilenames(
    title="选择两个 CSV 噪声文件",
    filetypes=[("CSV files", "*.csv")]
)

if len(file_paths) != 2:
    print("❌ 请选择两个 CSV 文件！")
    exit()

# 分别处理两个文件
y_limits = [YMAX_FILE1, YMAX_FILE2]
x_limits = [XMAX_FILE1, XMAX_FILE2]

for i, (fp, y_lim, x_lim) in enumerate(zip(file_paths, y_limits, x_limits)):
    file_name = os.path.basename(fp)

    print(f"\nProcessing: {fp}")

    time, voltage = read_csv_with_header(fp)
    freq, amp, fs = compute_fft(time, voltage)

    print(f"采样率 fs = {fs:.2f} Hz, 数据点数 = {len(time)}")

    # ----------- 第一张图：线性 -----------
    if i == 0:
        title = f"FFT Spectrum – {file_name} (Linear)"
        plot_fft(freq, amp, title, y_limit=y_lim, x_limit=x_lim, loglog=False)

    # ----------- 第二张图：log-log -----------
    else:
        title = f"FFT Spectrum – {file_name} (Log-Log)"
        plot_fft(freq, amp, title, y_limit=y_lim, x_limit=x_lim, loglog=True)
