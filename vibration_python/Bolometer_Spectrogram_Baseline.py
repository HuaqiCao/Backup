# ============================================================
#  TDMS/CSV 读取：每个通道绘制
#     1) 频谱图（Spectrogram）
#     2) 基线漂移（Baseline Drift）
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os

plt.rcParams['font.family'] = 'Times New Roman'

# 过滤中文
def ascii_label(s):
    out = ''.join(c for c in s if ord(c) < 128)
    return out if out.strip() else "CH"

# TDMS 读取（限制时长 + 降采样）
def load_safe_data_tdms(ch, max_sec=600, target_fs=200):

    t_full = ch.time_track()
    fs = 1 / (t_full[1] - t_full[0])

    max_samples = min(len(ch), int(fs * max_sec))
    data = ch[:max_samples]
    t = t_full[:max_samples]

    # 降采样
    factor = max(1, int(fs / target_fs))
    if factor > 1:
        from scipy.signal import decimate
        data = decimate(data, factor, zero_phase=True)
        t = t[::factor]
        fs = fs / factor

    return t, data, fs

# CSV 读取（默认跳过前4行）
def load_safe_data_csv(csv_path):

    print("读取 CSV:", csv_path)

    df = pd.read_csv(
        csv_path,
        skiprows=4,
        on_bad_lines='skip',
        engine='python'
    )

    # 一列 → 自动生成时间
    if df.shape[1] == 1:
        data = df.iloc[:, 0].values
        N = len(data)
        fs = 200
        t = np.arange(N) / fs
        return t, data, fs

    # 正常两列：time + value
    t = df.iloc[:, 0].values.astype(float)
    data = df.iloc[:, 1].values.astype(float)

    # 时间异常 → 自动生成
    dt = np.diff(t)
    if np.any(dt <= 0) or np.median(dt) == 0:
        N = len(data)
        fs = 200
        t = np.arange(N) / fs
        return t, data, fs

    fs = 1.0 / np.median(dt)
    return t, data, fs

# 文件选择
def select_files():
    root = tk.Tk()
    root.withdraw()
    return list(filedialog.askopenfilenames(
        title="选择 TDMS 或 CSV 文件",
        filetypes=[("TDMS files", "*.tdms"), ("CSV files", "*.csv")]
    ))

# 加载全部文件，按通道名归类
def load_all_files_by_channel(file_list):
    channel_dict = {}

    for file_path in file_list:
        fname = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        # CSV
        if ext == ".csv":
            print(f"[CSV] {fname}")
            t, data, fs = load_safe_data_csv(file_path)
            cname = ascii_label(fname.replace(".csv", ""))
            channel_dict.setdefault(cname, []).append((t, data, fs, fname))

        # TDMS
        elif ext == ".tdms":
            print(f"[TDMS] {fname}")
            tdms = TdmsFile.open(file_path)
            for g in tdms.groups():
                for ch in g.channels():
                    cname = ascii_label(ch.name)
                    t, data, fs = load_safe_data_tdms(ch)
                    channel_dict.setdefault(cname, []).append((t, data, fs, fname))

        else:
            print("未知文件：", fname)

    return channel_dict

# 绘制频谱图
def plot_spectrogram(cname, data_list, fmax=50):

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(f"Spectrogram — {cname}")

    for t, data, fs, fname in data_list:

        nper = int(fs * 10)  # 10 秒窗口
        f, tt, Sxx = signal.spectrogram(
            data, fs, nperseg=nper,
            noverlap=int(nper * 0.5),
            scaling="density", mode="psd"
        )

        pcm = ax.pcolormesh(
            tt/3600, f, 10*np.log10(Sxx + 1e-20),
            shading="auto", cmap="viridis"
        )

    ax.set_ylim(0, fmax)
    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(pcm, label="PSD (dB)")
    fig.tight_layout()

# 绘制基线漂移
def plot_drift(cname, data_list):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Baseline Drift — {cname}")

    for t, data, fs, fname in data_list:
        N = int(fs * 60)  # 60秒平均
        if N <= 1:
            continue
        baseline = np.convolve(data, np.ones(N)/N, mode="valid")
        ax.plot(t[:len(baseline)]/3600, baseline, label=ascii_label(fname))

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Baseline")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()

# 处理每个通道
def process_channel(cname, data_list):
    print(f"\n=== 通道: {cname} ===")
    plot_spectrogram(cname, data_list)
    plot_drift(cname, data_list)

# 主程序
if __name__ == "__main__":

    files = select_files()
    if not files:
        print("用户取消")
        exit()

    print("\n选中文件:")
    for f in files:
        print(" -", f)

    channel_dict = load_all_files_by_channel(files)

    for cname, data_list in channel_dict.items():
        process_channel(cname, data_list)

    print("\n处理完成.")
    plt.show()
