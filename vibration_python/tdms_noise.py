# ============================================================
# 本程序用于：
# 1) 选择两个 CSV 噪声文件（跳过前 4 行，包含 time/voltage）；
# 2) 对每个文件计算 ASD（Amplitude Spectral Density, V/√Hz）；
# 3) 每个文件绘制 Linear ASD（共 2 张图）；
# 4) 坐标范围自动调整，无需手动设置。
# ============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import os

plt.rcParams['font.family'] = 'Times New Roman'


def read_csv_with_header(path):
    """读取 CSV（跳过前4行），返回 t(s), v(V)"""
    df = pd.read_csv(path, skiprows=4, header=None)
    return df[0].values, df[1].values


def compute_fft_asd(time, signal):
    """计算单边 ASD（Amplitude Spectral Density，V/√Hz）"""

    # ======== 唯一新增：去直流分量 ========
    signal = signal - np.mean(signal)

    N = len(signal)
    dt = time[1] - time[0]
    fs = 1.0 / dt
    df = fs / N  # frequency resolution

    fft_vals = np.fft.rfft(signal)
    fft_freq = np.fft.rfftfreq(N, dt)

    # 单边幅度（V）
    amp = np.abs(fft_vals) * 2.0 / N

    # 转换为 ASD（V/√Hz）
    asd = amp / np.sqrt(df)

    return fft_freq, asd, fs


def plot_fft(freq, amp, title):
    """只绘制线性 ASD 图"""
    plt.figure(figsize=(10, 5))
    plt.plot(freq, amp, linewidth=1.0)

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("ASD (V/√Hz)")
    plt.title(title)
    plt.grid(True)

    plt.tight_layout()
    plt.show()


# ============================
# 主程序
# ============================

root = Tk()
root.withdraw()

file_paths = filedialog.askopenfilenames(
    title="Select Two CSV Noise Files",
    filetypes=[("CSV files", "*.csv")]
)

if len(file_paths) != 2:
    print("❌ Please select exactly TWO CSV files.")
    exit()

# ============================
# 画图
# ============================
for fp in file_paths:

    fname = os.path.basename(fp)
    print(f"\nProcessing: {fp}")

    time, voltage = read_csv_with_header(fp)
    freq, asd, fs = compute_fft_asd(time, voltage)
    print(f"Sampling rate fs = {fs:.2f} Hz, N = {len(time)}")

    title = f"ASD Spectrum – {fname} (Linear)"
    plot_fft(freq, asd, title)
