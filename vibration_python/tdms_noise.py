# ============================================================
# 本程序用于：
# 1) 选择两个 CSV 噪声文件（跳过前 4 行，包含 time/voltage）；
# 2) 对每个文件计算 ASD（V/√Hz）；
# 3) 绘制 Linear ASD，并自动绘制白噪声水平线；
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

    # ======== 1. 去直流分量 ========
    signal = signal - np.mean(signal)

    N = len(signal)
    dt = time[1] - time[0]
    fs = 1.0 / dt
    df = fs / N  # frequency resolution

    # ======== 2. FFT（单边）========
    fft_vals = np.fft.rfft(signal)
    fft_freq = np.fft.rfftfreq(N, dt)

    # ======== 3. 幅度谱（严格单边缩放）========
    amp = np.abs(fft_vals) / N       # 先做统一 1/N 缩放

    if N > 2:
        amp[1:-1] *= 2.0             # 中间频点乘 2，DC 和 Nyquist 不乘 2

    # ======== 4. ASD（V/√Hz）========
    asd = amp / np.sqrt(df)

    return fft_freq, asd, fs, signal


def plot_fft(freq, amp, fs, signal, title):
    """绘制线性 ASD 图 + 从频谱中自动估计白噪声水平"""

    # ---- 自动选择白噪声频段（避开1/f噪声与roll-off） ----
    f_min = 3                    # 避开 1/f
    f_max = fs / 10              # 避开 roll-off

    mask = (freq > f_min) & (freq < f_max)

    # ---- 使用中值而不是平均值（对白噪声更鲁棒）----
    if np.sum(mask) > 20:
        white_noise_level = np.median(amp[mask])   # 更稳健的白噪声估计
    else:
        white_noise_level = np.median(amp)         # 极端情况 fallback

    plt.figure(figsize=(10, 5))
    plt.plot(freq, amp, linewidth=1.0, label="ASD")

    # ---- 绘制白噪声水平线（基于 ASD 平坦段计算）----
    plt.axhline(white_noise_level, color='red', linestyle='--',
                linewidth=1.2, label=f"White noise ≈ {white_noise_level:.3e} V/√Hz")

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("ASD (V/√Hz)")
    plt.title(title)
    plt.grid(True)
    plt.legend()

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
    freq, asd, fs, sig_dc_removed = compute_fft_asd(time, voltage)

    print(f"Sampling rate fs = {fs:.2f} Hz, N = {len(time)}")

    title = f"ASD Spectrum – {fname} (Linear)"
    plot_fft(freq, asd, fs, sig_dc_removed, title)
