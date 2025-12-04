import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from nptdms import TdmsFile
import tkinter as tk
from tkinter import filedialog


# ==========================================================
# --------------------- 多选 TDMS 文件 -----------------------
# ==========================================================
def select_tdms_files():
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select TDMS Files",
        filetypes=[("TDMS files", "*.tdms")]
    )
    return list(file_paths)


# ==========================================================
# -------------------- 打印 TDMS 文件结构 ---------------------
# ==========================================================
def print_tdms_structure(tdms):
    print("\n=== TDMS STRUCTURE ===")
    groups = tdms.groups()
    print(f"Total Groups: {len(groups)}")

    for gi, g in enumerate(groups):
        print(f"\nGroup {gi}: '{g.name}'")
        channels = g.channels()

        if len(channels) == 0:
            print("  (No channels)")
        else:
            for ci, ch in enumerate(channels):
                try:
                    length = len(ch[:])
                except:
                    length = "Unreadable"
                print(f"  Channel {ci}: '{ch.name}', length={length}")


# ==========================================================
# --------------------- 读取单个通道数据 ----------------------
# ==========================================================
def read_tdms_channel(tdms, group_index, channel_index):
    group = tdms.groups()[group_index]
    channel = group.channels()[channel_index]

    data = channel[:]
    t = channel.time_track()

    fs = 1 / (t[1] - t[0])

    print(f"[OK] Loaded {len(data)} samples from Group='{group.name}', Channel='{channel.name}', fs={fs:.2f} Hz")
    return t, data, fs, group.name, channel.name


# ==========================================================
# ------------------------ 时频图函数 ------------------------
# ==========================================================
def plot_spectrogram(t, data, fs,
                     target_fs=200,
                     window_sec=10,
                     overlap_ratio=0.5,
                     fmax=50,
                     save_name="spectrogram.png"):

    factor = int(fs / target_fs)
    if factor > 1:
        data_ds = data[::factor]
        t_ds = t[::factor]
    else:
        data_ds = data
        t_ds = t
        target_fs = fs

    nperseg = int(target_fs * window_sec)
    noverlap = int(nperseg * overlap_ratio)

    f, t_spec, Sxx = signal.spectrogram(
        data_ds, fs=target_fs, nperseg=nperseg,
        noverlap=noverlap, scaling="density", mode="psd"
    )

    plt.figure(figsize=(12, 5))
    plt.pcolormesh(t_spec/3600, f, 10*np.log10(Sxx), shading="auto", cmap="jet")
    plt.title(f"Spectrogram")
    plt.xlabel("Time [hours]")
    plt.ylabel("Frequency [Hz]")
    plt.ylim(0, fmax)
    plt.colorbar(label="PSD [dB]")
    plt.tight_layout()
    plt.savefig(save_name, dpi=200)
    plt.show(Block=False)


# ==========================================================
# ---------------------- 自动事件检测 ------------------------
# ==========================================================
def detect_events(data, fs, threshold_sigma=5, dead_time_sec=5):
    dt = signal.detrend(data)
    sigma = np.std(dt)
    thr = sigma * threshold_sigma

    idx = np.where(np.abs(dt) > thr)[0]
    if len(idx) == 0:
        print("No events detected.")
        return []

    events = []
    curr = [idx[0]]
    for i in idx[1:]:
        if i - curr[-1] < int(dead_time_sec * fs):
            curr.append(i)
        else:
            events.append(curr)
            curr = [i]
    events.append(curr)

    peaks = []
    for evt in events:
        seg = data[evt]
        peak = evt[np.argmax(np.abs(seg))]
        peaks.append(peak)

    print(f"Detected {len(peaks)} events")
    return peaks


# ==========================================================
# ------------------------ 瀑布图函数 ------------------------
# ==========================================================
def plot_waterfall(data, fs, peaks, window_sec=20, save_name="waterfall.png"):
    half = int(window_sec * fs / 2)

    pulses = []
    for t0 in peaks:
        start = max(0, t0 - half)
        end = min(len(data), t0 + half)
        pulse = data[start:end]
        if len(pulse) < 2*half:
            pulse = np.pad(pulse, (0, 2*half - len(pulse)))
        pulses.append(pulse)

    pulses = np.array(pulses)

    plt.figure(figsize=(10, 6))
    plt.imshow(pulses, aspect='auto', cmap='jet',
               extent=[-window_sec/2, window_sec/2, 0, len(peaks)])
    plt.title("Waterfall")
    plt.xlabel("Time [s]")
    plt.ylabel("Event Index")
    plt.colorbar(label="Amplitude")
    plt.tight_layout()
    plt.savefig(save_name, dpi=200)
    plt.show(Block=False)
    plt.show()      
# ==========================================================
# ---------------------------- 主程序 ------------------------
# ==========================================================
if __name__ == "__main__":

    file_list = select_tdms_files()
    if len(file_list) == 0:
        print("No files selected.")
        exit()

    print(f"\nSelected {len(file_list)} TDMS files:")
    for f in file_list:
        print(" -", f)

    for file_path in file_list:

        print("\n======================================")
        print("Processing:", file_path)
        print("======================================")

        tdms = TdmsFile.read(file_path)

        # ① 打印结构
        print_tdms_structure(tdms)

        # 对所有 group 和 channels 逐个处理
        for gi, g in enumerate(tdms.groups()):
            channels = g.channels()
            for ci, ch in enumerate(channels):

                # ② 读取单个 channel
                t, data, fs, gname, cname = read_tdms_channel(tdms, gi, ci)

                base = file_path.split("/")[-1].replace(".tdms", "")
                prefix = f"{base}_G{gi}_{gname}_C{ci}_{cname}"

                # ③ 时频图
                plot_spectrogram(
                    t, data, fs,
                    save_name=f"{prefix}_spectrogram.png"
                )

                # ④ 自动事件（可选）
                peaks = detect_events(data, fs)

                # ⑤ 瀑布图（如有事件）
                if len(peaks) > 0:
                    plot_waterfall(
                        data, fs, peaks,
                        save_name=f"{prefix}_waterfall.png"
                    )
