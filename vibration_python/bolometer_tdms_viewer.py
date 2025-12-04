# ============================================================
# 1）弹窗选择多个 TDMS 文件；
# 2）打印 TDMS 内的 Group / Channel 结构；
# 3）按 channel name 自动归类所有数据（自动 ASCII 过滤）；
# 4）对每个通道绘制瀑布图、噪声 PSD、RMS、直方图、基线漂移；
# 5）自动对大文件“只加载部分数据 + 自动降采样”加速处理；
# 6）所有图一次性 show()。
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import os

# 全局字体
plt.rcParams['font.family'] = 'Times New Roman'


# ============================================================
#  过滤中文字符：解决 Times New Roman 无法渲染中文的问题
# ============================================================
def ascii_label(s):
    out = ''.join(c for c in s if ord(c) < 128)
    return out if out.strip() else "CH"


# ============================================================
#  仅读前 max_sec 秒 + 自动降采样
# ============================================================
def load_safe_data(ch, max_sec=600, target_fs=200):

    t_full = ch.time_track()
    fs = 1 / (t_full[1] - t_full[0])

    # 只读前 max_sec 秒
    max_samples = min(len(ch), int(fs * max_sec))
    data = ch[:max_samples]
    t = t_full[:max_samples]

    # 自动降采样：把 5 kHz → 200 Hz，加速 25x
    factor = max(1, int(fs / target_fs))
    if factor > 1:
        from scipy.signal import decimate
        data = decimate(data, factor, zero_phase=True)
        t = t[::factor]
        fs = fs / factor

    return t, data, fs


# ============================================================
#  选择 TDMS 文件
# ============================================================
def select_tdms_files():
    root = tk.Tk()
    root.withdraw()
    return list(filedialog.askopenfilenames(
        title="选择 TDMS 文件",
        filetypes=[("TDMS files", "*.tdms")]
    ))


# ============================================================
#  打印 TDMS 结构（metadata 级别，不读数据）
# ============================================================
def inspect_tdms_structure(tdms, filename):
    print(f"\n===== TDMS STRUCTURE ({filename}) =====")
    for gi, g in enumerate(tdms.groups()):
        print(f"\n Group {gi}: '{g.name}'")
        for ci, ch in enumerate(g.channels()):
            try:
                length = len(ch)     # 最稳妥
            except:
                length = "N/A"
            print(f"   Channel {ci}: '{ch.name}', len={length}")

# ============================================================
#  加载 metadata 并按通道分类（加速）
# ============================================================
def load_all_tdms_by_channel(file_list):
    channel_dict = {}

    for file_path in file_list:
        fname = os.path.basename(file_path)

        # ★ 以“打开文件流”的方式读取（不会被关闭）
        tdms = TdmsFile.open(file_path)  
        inspect_tdms_structure(tdms, fname)

        # 遍历组和通道
        for g in tdms.groups():
            for ch in g.channels():

                cname = ascii_label(ch.name)

                # ★ 读取部分数据 + 自动降采样
                t, data, fs = load_safe_data(
                    ch, 
                    max_sec=600,       # 读取前 600s
                    target_fs=200      # 自动降到 200 Hz
                )

                # 加入 dict
                channel_dict.setdefault(cname, []).append((t, data, fs, fname))

    return channel_dict

# ============================================================
#  Spectrogram（瀑布图）
# ============================================================
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

        pcm = ax.pcolormesh(tt/3600, f, 10*np.log10(Sxx),
                            shading="auto", cmap="jet")

    ax.set_ylim(0, fmax)
    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(pcm, label="PSD (dB)")
    fig.tight_layout()


# ============================================================
#  Noise PSD
# ============================================================
def plot_noise_psd(cname, data_list):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Noise PSD — {cname}")

    combined_f = None
    combined_Pxx = None

    for t, data, fs, fname in data_list:

        f, Pxx = signal.welch(data, fs, nperseg=int(fs*4))
        ax.semilogy(f, np.sqrt(Pxx), label=ascii_label(fname))

        if combined_f is None:
            combined_f, combined_Pxx = f, Pxx
        else:
            combined_Pxx = (combined_Pxx + Pxx)/2

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("ASD (unit/√Hz)")
    ax.grid(True, which="both")
    ax.legend()
    fig.tight_layout()


# ============================================================
#  RMS vs Time
# ============================================================
def plot_rms(cname, data_list):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"RMS vs Time — {cname}")

    for t, data, fs, fname in data_list:
        N = int(fs * 10)  # 10 秒平均
        rms = np.sqrt(np.convolve(data**2, np.ones(N)/N, mode="valid"))
        ax.plot(t[:len(rms)]/3600, rms, label=ascii_label(fname))

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("RMS")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()


# ============================================================
#  Noise Histogram
# ============================================================
def plot_hist(cname, data_list):

    samples = []
    for t, data, fs, fname in data_list:
        samples.append(data[:200000])  # 截取部分即可

    noise = np.concatenate(samples)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(noise, bins=200, density=True, alpha=0.7)
    ax.set_title(f"Noise Histogram — {cname}")
    ax.set_xlabel("Amplitude")
    ax.set_ylabel("PDF")
    fig.tight_layout()


# ============================================================
#  Baseline Drift
# ============================================================
def plot_drift(cname, data_list):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Baseline Drift — {cname}")

    for t, data, fs, fname in data_list:
        N = int(fs * 60)  # 60 秒平均
        baseline = np.convolve(data, np.ones(N)/N, mode="valid")
        ax.plot(t[:len(baseline)]/3600, baseline, label=ascii_label(fname))

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Baseline")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()


# ============================================================
#  处理单个通道
# ============================================================
def process_channel(cname, data_list):

    print(f"\n=== Processing channel '{cname}' ===")

    plot_spectrogram(cname, data_list)
    plot_noise_psd(cname, data_list)
    plot_rms(cname, data_list)
    plot_hist(cname, data_list)
    plot_drift(cname, data_list)

    print(f"[DONE] Channel '{cname}' finished.\n")


# ============================================================
#  主程序入口
# ============================================================
if __name__ == "__main__":

    files = select_tdms_files()
    if not files:
        print("用户取消")
        exit()

    print("\nSelected TDMS files:")
    for f in files:
        print(" -", f)

    channel_dict = load_all_tdms_by_channel(files)

    for cname, data_list in channel_dict.items():
        process_channel(cname, data_list)

    print("\nAll channels processed.")

    plt.show()  # 一次性弹出全部图
