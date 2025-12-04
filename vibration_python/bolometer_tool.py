import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog
import os



# ============================================================
# -------- 多选 TDMS 文件 + 返回文件列表 ------------------------
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
# ----------- 打印 TDMS 文件结构 ------------------------------
# ============================================================
def inspect_tdms_structure(tdms, filename):
    print(f"\n===== TDMS STRUCTURE ({filename}) =====")
    groups = tdms.groups()
    for gi, g in enumerate(groups):
        print(f"\n Group {gi}: '{g.name}'")
        channels = g.channels()
        if len(channels) == 0:
            print("   (No channels)")
        else:
            for ci, ch in enumerate(channels):
                print(f"   Channel {ci}: '{ch.name}', length={len(ch[:])}")



# ============================================================
# ------ 读取所有 TDMS 文件 → 根据 channel name 归类 ----------
# ============================================================
def load_all_tdms_by_channel(file_list):
    """
    返回一个 dict:
        channel_dict[channel_name] = list of (t, data, fs, filename)
    """
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
                fs = 1 / (t[1] - t[0])

                if cname not in channel_dict:
                    channel_dict[cname] = []

                channel_dict[cname].append((t, data, fs, name_only))

    return channel_dict



# ============================================================
# ----------------------- 时频图 ------------------------------
# ============================================================
def plot_spectrogram_multi(channel_name, data_list,
                           target_fs=200, window_sec=10, overlap_ratio=0.5, fmax=50):

    plt.figure(figsize=(12, 5))
    plt.title(f"Spectrogram: Channel {channel_name}")

    for t, data, fs, fname in data_list:

        factor = int(fs / target_fs)
        if factor > 1:
            data = data[::factor]
            t = t[::factor]
        else:
            target_fs = fs

        nper = int(window_sec * target_fs)
        nov = int(nper * overlap_ratio)

        f, tt, Sxx = signal.spectrogram(
            data, fs=target_fs, nperseg=nper, noverlap=nov,
            scaling="density", mode="psd"
        )

        plt.pcolormesh(tt/3600, f, 10*np.log10(Sxx),
                       shading="auto", cmap="jet")

    plt.xlabel("Time [hours]")
    plt.ylabel("Frequency [Hz]")
    plt.ylim(0, fmax)
    plt.colorbar(label="PSD [dB]")
    plt.tight_layout()
    plt.show(block=False)



# ============================================================
# ----------------------- PSD / Noise -------------------------
# ============================================================
def plot_noise_psd_multi(channel_name, data_list):
    plt.figure(figsize=(10, 5))
    plt.title(f"Noise PSD: Channel {channel_name}")

    for t, data, fs, fname in data_list:
        f, Pxx = signal.welch(data, fs, nperseg=fs*4)
        plt.semilogy(f, np.sqrt(Pxx), label=fname)  # Amplitude spectral density

    plt.xlabel("Frequency [Hz]")
    plt.ylabel("ASD (sqrt(PSD))")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)



# ============================================================
# ----------------------- RMS vs 时间 -------------------------
# ============================================================
def plot_rms_over_time(channel_name, data_list, window_sec=10):
    plt.figure(figsize=(10, 4))
    plt.title(f"RMS vs time: Channel {channel_name}")

    for t, data, fs, fname in data_list:
        N = int(window_sec * fs)
        rms = np.sqrt(signal.convolve(data**2, np.ones(N)/N, mode="valid"))
        tt = t[:len(rms)]
        plt.plot(tt/3600, rms, label=fname)

    plt.xlabel("Time [hours]")
    plt.ylabel("RMS")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)



# ============================================================
# ----------------------------- 主程序 ------------------------
# ============================================================
if __name__ == "__main__":

    file_list = select_tdms_files()
    if len(file_list) == 0:
        print("No files selected.")
        exit()

    print("\nSelected files:")
    for f in file_list:
        print(" -", f)

    # 读取所有 TDMS → 依 channel name 分类
    channel_dict = load_all_tdms_by_channel(file_list)

    # 对每个 channel name 单独画图
    for cname, data_list in channel_dict.items():

        print(f"\n========== PROCESS CHANNEL '{cname}' (files={len(data_list)}) ==========")

        # (1) Spectrogram
        plot_spectrogram_multi(cname, data_list)

        # (2) Noise PSD
        plot_noise_psd_multi(cname, data_list)

        # (3) RMS evolution
        plot_rms_over_time(cname, data_list)

    print("\nAll plots generated.")
    plt.show()
