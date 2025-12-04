"""
本程序功能：
1) 弹框多选 TDMS 文件；
2) 打印 TDMS 结构；
3) 按 channel name 归类所有数据；
4) 生成 5 类图像写入 PDF（Spectrogram/Noise PSD/RMS/Histogram/Drift）
5) 所有图例中文自动过滤 (ASCII only)，避免 PDF 字体警告。
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import os


# ============================================================
#  去除中文字符，只保留 ASCII，避免 PDF 字体警告
# ============================================================
def ascii_label(s):
    out = ''.join(c for c in s if ord(c) < 128)
    if out.strip() == "":
        return "file"
    return out


# ============================================================
#  选择 TDMS 文件
# ============================================================
def select_tdms_files():
    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames(
        title="Select TDMS files",
        filetypes=[("TDMS files", "*.tdms")]
    )
    return list(paths)


# ============================================================
#  打印 TDMS 结构
# ============================================================
def inspect_tdms_structure(tdms, filename):
    print(f"\n===== TDMS STRUCTURE ({filename}) =====")
    for gi, g in enumerate(tdms.groups()):
        print(f"\n Group {gi}: '{g.name}'")
        for ci, ch in enumerate(g.channels()):
            print(f"   Channel {ci}: '{ch.name}', length={len(ch[:])}")


# ============================================================
#  加载并按通道归类
# ============================================================
def load_all_tdms_by_channel(file_list):
    channel_dict = {}

    for file_path in file_list:
        name_only = os.path.basename(file_path)
        tdms = TdmsFile.read(file_path)
        inspect_tdms_structure(tdms, name_only)

        for g in tdms.groups():
            for ch in g.channels():
                cname = ch.name
                t = ch.time_track()
                data = ch[:]
                fs = 1.0 / (t[1] - t[0])

                if cname not in channel_dict:
                    channel_dict[cname] = []
                channel_dict[cname].append((t, data, fs, name_only))

    return channel_dict


# ============================================================
#  Spectrogram
# ============================================================
def plot_spectrogram_multi(channel_name, data_list, pdf,
                           target_fs=200, window_sec=10,
                           overlap_ratio=0.5, fmax=50):

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(f"Spectrogram — {channel_name}")

    for t, data, fs, fname in data_list:

        label = ascii_label(fname)

        # 降采样
        factor = max(1, int(fs / target_fs))
        data_ds = data[::factor]
        t_ds = t[::factor]
        fs2 = fs / factor

        nper = int(window_sec * fs2)
        f, tt, Sxx = signal.spectrogram(
            data_ds, fs=fs2, nperseg=nper,
            noverlap=int(nper*overlap_ratio),
            scaling="density", mode="psd"
        )

        pcm = ax.pcolormesh(tt/3600, f, 10*np.log10(Sxx),
                            shading="auto", cmap="jet")

    ax.set_ylim(0, fmax)
    ax.set_xlabel("Time [hours]")
    ax.set_ylabel("Frequency [Hz]")
    fig.colorbar(pcm, label="PSD [dB]")

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
#  Noise PSD
# ============================================================
def detect_microphonic_lines(f, Pxx, prominence_db=10.0):
    psd_db = 10*np.log10(Pxx)
    peaks, _ = signal.find_peaks(psd_db, prominence=prominence_db)
    return f[peaks]


def plot_noise_psd_multi(channel_name, data_list, pdf):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Noise PSD — {channel_name}")

    combined_f = None
    combined_Pxx = None

    for t, data, fs, fname in data_list:

        label = ascii_label(fname)

        max_sec = 600
        d_use = data[:min(len(data), int(fs * max_sec))]

        f, Pxx = signal.welch(d_use, fs, nperseg=int(fs*4))
        ax.semilogy(f, np.sqrt(Pxx), label=label)

        if combined_f is None:
            combined_f = f
            combined_Pxx = Pxx
        else:
            combined_Pxx = (combined_Pxx + Pxx) / 2

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("ASD [unit/√Hz]")
    ax.grid(True, which="both")
    ax.legend()

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    peaks = detect_microphonic_lines(combined_f, combined_Pxx)
    print(f"[{channel_name}] Microphonic peaks: {peaks}")


# ============================================================
#  RMS vs Time
# ============================================================
def plot_rms_over_time(channel_name, data_list, pdf, window_sec=10):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"RMS vs Time — {channel_name}")

    for t, data, fs, fname in data_list:

        label = ascii_label(fname)

        N = int(window_sec * fs)
        if N < 2:
            continue

        rms = np.sqrt(np.convolve(data**2, np.ones(N)/N, mode="valid"))
        ax.plot(t[:len(rms)]/3600, rms, label=label)

    ax.set_xlabel("Time [hours]")
    ax.set_ylabel("RMS")
    ax.grid(True)
    ax.legend()

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
#  Noise Histogram
# ============================================================
def plot_noise_histogram(channel_name, data_list, pdf,
                         max_samples=2_000_000):

    samples = []
    for t, data, fs, fname in data_list:
        n = min(len(data), max_samples // len(data_list))
        samples.append(data[:n])

    noise = np.concatenate(samples)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(noise, bins=200, density=True, alpha=0.7)
    ax.set_title(f"Noise Histogram — {channel_name}")
    ax.set_xlabel("Amplitude")
    ax.set_ylabel("PDF")

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
#  Baseline Drift
# ============================================================
def plot_baseline_drift(channel_name, data_list, pdf, window_sec=60):

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"Baseline Drift — {channel_name}")

    for t, data, fs, fname in data_list:

        label = ascii_label(fname)

        N = int(window_sec * fs)
        baseline = np.convolve(data, np.ones(N)/N, mode="valid")
        ax.plot(t[:len(baseline)]/3600, baseline, label=label)

    ax.set_xlabel("Time [hours]")
    ax.set_ylabel("Baseline")
    ax.grid(True)
    ax.legend()

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
#  主处理流程
# ============================================================
def process_channel(channel_name, data_list):
    pdf_name = f"Bolometer_{channel_name}_report.pdf"
    print(f"\n=== Processing '{channel_name}' → {pdf_name} ===")

    with PdfPages(pdf_name) as pdf:
        plot_spectrogram_multi(channel_name, data_list, pdf)
        plot_noise_psd_multi(channel_name, data_list, pdf)
        plot_rms_over_time(channel_name, data_list, pdf)
        plot_noise_histogram(channel_name, data_list, pdf)
        plot_baseline_drift(channel_name, data_list, pdf)

    print(f"[DONE] Saved → {pdf_name}")


# ============================================================
#  主程序入口
# ============================================================
if __name__ == "__main__":

    file_list = select_tdms_files()
    if len(file_list) == 0:
        print("User canceled.")
        raise SystemExit

    print("\nSelected TDMS files:")
    for f in file_list:
        print(" -", f)

    channel_dict = load_all_tdms_by_channel(file_list)

    for cname, data_list in channel_dict.items():
        process_channel(cname, data_list)

    print("\nAll channels processed.")
