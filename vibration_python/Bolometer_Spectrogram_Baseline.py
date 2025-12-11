# ============================================================
#  TDMS/CSV 读取：每个通道绘制真实时间
#     1) 频谱图（Spectrogram）
#     2) 基线漂移（Baseline Drift）
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os
import re
from datetime import datetime, timedelta

plt.rcParams['font.family'] = 'Times New Roman'


# -------------------------------
# 从文件名解析真实起始时间
# -------------------------------
def parse_filename_timestamp(fname):
    """
    解析文件名中的真实时间，例如：
    记录-2025-10-20 105823 004.tdms
    """
    pattern = r"(\d{4}-\d{2}-\d{2})\s+(\d{6})"
    m = re.search(pattern, fname)
    if not m:
        print("⚠ 警告：未从文件名解析时间，将使用相对秒作为横坐标")
        return None

    date_str = m.group(1)    # 2025-10-20
    time_str = m.group(2)    # 105823

    return datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H%M%S")


# -------------------------------
# 过滤中文
# -------------------------------
def ascii_label(s):
    out = ''.join(c for c in s if ord(c) < 128)
    return out if out.strip() else "CH"


# -------------------------------
# TDMS 读取：支持 max_sec + 真实时间
# -------------------------------
def load_safe_data_tdms(ch, fname, max_sec=600, target_fs=100):
    """
    max_sec：限制采样时间（秒）
    target_fs=None：不降采样（推荐）
    """
    # 解析文件名中的起始时间
    start_time = parse_filename_timestamp(fname)

    # TDMS 相对时间（秒）
    t_full = ch.time_track()
    fs = 1 / (t_full[1] - t_full[0])

    # 限制时长
    max_samples = min(len(ch), int(fs * max_sec))
    data = ch[:max_samples]
    t_rel = t_full[:max_samples]

    # =============== 不降采样（你要求） ===============
    if target_fs is not None and target_fs < fs:
        from scipy.signal import decimate
        factor = int(fs / target_fs)
        data = decimate(data, factor, zero_phase=True)
        t_rel = t_rel[::factor]
        fs = fs / factor

    # =============== 转为真实绝对时间 ===============
    if start_time is not None:
        t_abs = np.array([start_time + timedelta(seconds=float(s)) for s in t_rel])
        t_plot = mdates.date2num(t_abs)  # matplotlib 格式
    else:
        t_plot = t_rel  # 用相对秒

    return t_plot, data, fs


# -------------------------------
# CSV 默认不处理真实时间（保持兼容）
# -------------------------------
def load_safe_data_csv(csv_path):
    print("读取 CSV:", csv_path)

    df = pd.read_csv(csv_path, skiprows=4,
                     on_bad_lines='skip', engine='python')

    if df.shape[1] == 1:
        data = df.iloc[:, 0].values
        fs = 200
        t = np.arange(len(data)) / fs
        return t, data, fs

    t = df.iloc[:, 0].values.astype(float)
    data = df.iloc[:, 1].values.astype(float)
    dt = np.diff(t)

    if np.any(dt <= 0) or np.median(dt) == 0:
        fs = 200
        t = np.arange(len(data)) / fs
        return t, data, fs

    fs = 1 / np.median(dt)
    return t, data, fs


# 选择文件
def select_files():
    root = tk.Tk()
    root.withdraw()
    return list(filedialog.askopenfilenames(
        title="选择 TDMS 或 CSV 文件",
        filetypes=[("TDMS files", "*.tdms"), ("CSV files", "*.csv")]
    ))


# 加载全部通道
def load_all_files_by_channel(file_list):
    channel_dict = {}

    for file_path in file_list:
        fname = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":
            t, data, fs = load_safe_data_csv(file_path)
            cname = ascii_label(fname.replace(".csv", ""))
            channel_dict.setdefault(cname, []).append((t, data, fs, fname))

        elif ext == ".tdms":
            tdms = TdmsFile.open(file_path)
            for g in tdms.groups():
                for ch in g.channels():
                    cname = ascii_label(ch.name)
                    t, data, fs = load_safe_data_tdms(ch, fname)
                    channel_dict.setdefault(cname, []).append((t, data, fs, fname))

    return channel_dict


# -------------------------------
# 绘制频谱图（真实时间）
# -------------------------------
def plot_spectrogram(cname, data_list, fmax=1000):

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(f"Spectrogram — {cname}")

    for t, data, fs, fname in data_list:

        nper = int(fs * 10)
        f, tt, Sxx = signal.spectrogram(
            data, fs, nperseg=nper,
            noverlap=int(nper * 0.5),
            scaling="density", mode="psd"
        )

        # 绝对时间轴：tt 是相对秒，需要加到起始时间
        if isinstance(t[0], float) and t[0] > 1e3:  
            # matplotlib 日期单位是 float 天
            tt_abs = t[0] + tt / 86400
        else:
            tt_abs = tt / 3600  # 回退方案（相对时间）

        pcm = ax.pcolormesh(
            tt_abs, f, 10*np.log10(Sxx + 1e-20),
            shading="auto", cmap="viridis"
        )

    # 格式化时间
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M:%S"))

    ax.set_ylim(0, fmax)
    ax.set_xlabel("Time (Real)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(pcm, label="PSD (dB)")
    fig.tight_layout()


# -------------------------------
# 绘制基线漂移（真实时间）
# -------------------------------
def plot_drift(cname, data_list):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Baseline Drift — {cname}")

    for t, data, fs, fname in data_list:
        N = int(fs * 60)
        baseline = np.convolve(data, np.ones(N)/N, mode="valid")
        ax.plot(t[:len(baseline)], baseline, label=ascii_label(fname))

    # 格式化日期时间
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M:%S"))

    ax.set_xlabel("Time (Real)")
    ax.set_ylabel("Baseline")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()


# 主流程
def process_channel(cname, data_list):
    print(f"\n=== 通道: {cname} ===")
    plot_spectrogram(cname, data_list)
    plot_drift(cname, data_list)


# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":

    files = select_files()
    if not files:
        exit()

    channel_dict = load_all_files_by_channel(files)

    for cname, data_list in channel_dict.items():
        process_channel(cname, data_list)

    plt.show()
