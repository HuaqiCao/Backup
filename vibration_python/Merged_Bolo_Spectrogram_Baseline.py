# ============================================================
#   TDMS + CSV 读取，绘制：
#       1) 频谱图（Spectrogram）
#       2) 基线漂移（Baseline Drift）—— 自动断轴（无空白）
#       适配 merged.tdms 格式：<name>_time + <name>_value
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import Normalize
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os
from datetime import datetime, timedelta

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['figure.dpi'] = 120


# ============================================================
# 过滤中文
# ============================================================
def ascii_label(s):
    out = ''.join(c for c in s if ord(c) < 128)
    return out if out.strip() else "CH"


# ============================================================
# 加载 merged.tdms 的某个 base 通道
# ============================================================
def load_merged_tdms_channel(tdms, base_name, target_fs=1000):

    t_raw, v_raw = None, None

    for g in tdms.groups():
        for ch in g.channels():
            if ch.name == base_name + "_time":
                t_raw = np.array(ch[:], dtype=float)
            elif ch.name == base_name + "_value":
                v_raw = np.array(ch[:], dtype=float)

    if t_raw is None or v_raw is None:
        raise RuntimeError(f"未找到 base 通道：{base_name}")

    # 原始采样率
    dt = np.median(np.diff(t_raw))
    fs = 1.0 / dt

    # 自动降采样（避免内存爆炸）
    factor = max(1, int(fs / target_fs))
    if factor > 1:
        from scipy.signal import decimate
        v_raw = decimate(v_raw, factor, zero_phase=True)
        t_raw = t_raw[::factor]
        fs = fs / factor

    return t_raw, v_raw, fs


# ============================================================
# CSV 读取（兼容单列/双列）
# ============================================================
def load_safe_data_csv(csv_path):

    df = pd.read_csv(csv_path, skiprows=4, on_bad_lines="skip", engine="python")

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

    fs = 1.0 / np.median(dt)
    return t, data, fs


# ============================================================
# 文件选择
# ============================================================
def select_files():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilenames(
        title="选择 TDMS 或 CSV 文件",
        filetypes=[("TDMS", "*.tdms"), ("CSV", "*.csv")]
    )


# ============================================================
# 加载所有文件，按通道名称分组
# ============================================================
def load_all_files_by_channel(files):

    channel_dict = {}

    for path in files:
        fname = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()

        # ================= CSV =================
        if ext == ".csv":
            print("[CSV]", fname)
            t, data, fs = load_safe_data_csv(path)
            cname = ascii_label(fname.replace(".csv", ""))
            channel_dict.setdefault(cname, []).append((t, data, fs, fname))

        # ================= TDMS ================
        else:
            print("[TDMS]", fname)
            td = TdmsFile.open(path)

            # 找所有 base 名
            base_names = set()
            for g in td.groups():
                for ch in g.channels():
                    name = ch.name
                    if name.endswith("_time"):
                        base_names.add(name[:-5])
                    elif name.endswith("_value"):
                        base_names.add(name[:-6])

            for base in base_names:
                cname = ascii_label(base)
                t, data, fs = load_merged_tdms_channel(td, base)
                channel_dict.setdefault(cname, []).append((t, data, fs, fname))

    return channel_dict


# ============================================================
# 频谱图
# ============================================================
def plot_spectrogram(cname, data_list, fmax=80):

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_title(f"Time–Frequency Spectrogram — {cname}")

    for t, data, fs, fname in data_list:

        nper = int(fs * 15)
        nover = int(nper * 0.5)

        f, tt, Sxx = signal.spectrogram(
            data, fs,
            nperseg=nper,
            noverlap=nover,
            scaling="density",
            mode="psd"
        )

        t0 = t[0]
        t_plot = t0 + tt
        t_dt = [datetime.fromtimestamp(x) for x in t_plot]

        pcm = ax.pcolormesh(
            t_dt, f,
            10 * np.log10(Sxx + 1e-20),
            cmap="turbo",
            shading="auto",
            norm=Normalize(vmin=-120, vmax=-60)
        )

    ax.set_ylim(0, fmax)
    ax.set_ylabel("Frequency (Hz)")

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))

    fig.autofmt_xdate()
    fig.colorbar(pcm, label="PSD (dB)")
    fig.tight_layout()


# ============================================================
# 基线漂移图 —— 自动断轴（broken axis）
# ============================================================
def plot_drift(cname, data_list):

    # ---- 生成 baseline 段落 ----
    segments = []
    GAP_SEC = 2  # 2 秒以上视为断档

    for t, data, fs, fname in data_list:

        N = int(fs * 60)  # 60 秒平滑
        if N < 2:
            continue

        baseline = np.convolve(data, np.ones(N) / N, mode="valid")
        t2 = t[:len(baseline)]

        dt = np.diff(t2)
        gap_idx = np.where(dt > GAP_SEC)[0]

        start = 0
        for g in gap_idx:
            segments.append((t2[start:g + 1], baseline[start:g + 1], fname))
            start = g + 1
        segments.append((t2[start:], baseline[start:], fname))

    # 自动判断断轴位置
    first_end = datetime.fromtimestamp(segments[0][0][-1])
    last_start = datetime.fromtimestamp(segments[-1][0][0])

    # ========================================================
    # 建立两个 X 轴：左一半 + 右一半
    # ========================================================
    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        sharey=True,
        figsize=(14, 4),
        gridspec_kw=dict(width_ratios=[1, 1], wspace=0.05)
    )

    fig.suptitle(f"Baseline Drift — {cname}")

    # 左轴：结束时间 < 中间断点
    for t_seg, b_seg, fname in segments:
        if datetime.fromtimestamp(t_seg[-1]) <= last_start - timedelta(seconds=1):
            ax = ax1
        else:
            ax = ax2

        t_dt = mdates.date2num([datetime.fromtimestamp(x) for x in t_seg])
        ax.plot(t_dt, b_seg, label=ascii_label(fname))

    for ax in (ax1, ax2):
        ax.grid(True)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))

    ax1.set_ylabel("Baseline")

    # ---- 断轴符号 ----
    d = .015
    kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False)
    ax1.plot((1-d, 1+d), (-d, +d), **kwargs)
    ax1.plot((1-d, 1+d), (1-d, 1+d), **kwargs)

    kwargs = dict(transform=ax2.transAxes, color='k', clip_on=False)
    ax2.plot((-d, +d), (-d, +d), **kwargs)
    ax2.plot((-d, +d), (1-d, 1+d), **kwargs)

    fig.autofmt_xdate()
    fig.tight_layout()


# ============================================================
# 处理每个通道
# ============================================================
def process_channel(cname, data_list):
    print(f"\n=== 通道: {cname} ===")
    plot_spectrogram(cname, data_list)
    plot_drift(cname, data_list)


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":

    files = select_files()
    if not files:
        print("用户取消。")
        exit()

    print("\n选中文件:")
    for f in files:
        print(" -", f)

    channel_dict = load_all_files_by_channel(files)

    for cname, data_list in channel_dict.items():
        process_channel(cname, data_list)

    print("\n处理完成。")
    plt.show()
