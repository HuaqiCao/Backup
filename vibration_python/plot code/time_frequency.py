import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import os


def detect_unit(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                second_line = lines[1].strip().lower()
                if 'mv' in second_line or '毫伏' in second_line:
                    return 'mV'
                elif 'v' in second_line and 'mv' not in second_line:
                    return 'V'
        return 'mV'
    except:
        return 'mV'


def load_vibration_data(filepath):
    unit = detect_unit(filepath)
    print(f"  检测到单位: {unit}")

    df = pd.read_csv(filepath, skiprows=2, header=None, delimiter='\t',
                     encoding='utf-8-sig', engine='python', on_bad_lines='skip')
    t = df.iloc[:, 0].to_numpy(dtype=float)
    v = df.iloc[:, 1].to_numpy(dtype=float)

    if unit == 'mV':
        v = v / 1000.0

    v = v - v.mean()
    fs = 1.0 / (t[1] - t[0])
    return t, v, fs, unit


def compute_psd(signal, fs, nfft=100000, overlap_ratio=0.5):
    N = len(signal)
    nfft = min(nfft, N)
    nfft = nfft if nfft % 2 == 0 else nfft - 1

    window_size = nfft
    overlap = int(window_size * overlap_ratio)

    window = np.hanning(window_size)
    window = window / np.sqrt(np.mean(window**2))

    step = window_size - overlap
    n_frames = (len(signal) - window_size) // step + 1

    psd_sum = np.zeros(nfft // 2)

    for i in range(n_frames):
        start = i * step
        frame = signal[start:start + window_size] * window
        fft_data = np.fft.fft(frame, nfft)
        psd_frame = np.abs(fft_data[:nfft//2])**2 / (fs * nfft)
        psd_sum += psd_frame

    psd = psd_sum / n_frames
    psd[1:-1] = 2 * psd[1:-1]

    freq = np.arange(nfft // 2) * fs / nfft
    asd = np.sqrt(np.maximum(psd, 1e-30))

    return freq, psd, asd


def plot_psd_multi(data_list, save_dir=None):
    colors = plt.cm.tab10(np.linspace(0, 1, len(data_list)))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    for idx, (name, t, v, fs, freq, asd, unit) in enumerate(data_list):
        T_SHOW = min(2.0, t[-1])
        mask = t <= T_SHOW
        ax1.plot(t[mask], v[mask], color=colors[idx], linewidth=1.0, alpha=0.7, label=name)

        f_min = max(0.05, freq[0])
        f_max = min(fs/2, 500)
        mask_f = (freq >= f_min) & (freq <= f_max)
        ax2.loglog(freq[mask_f], asd[mask_f], color=colors[idx], linewidth=1.5, alpha=0.8, label=name)

    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Voltage (V)', fontsize=12)
    ax1.set_xlim(0, 1)
    ax1.set_title('Time Domain Signals', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=10)

    ax2.set_xlabel('Frequency (Hz)', fontsize=12)
    ax2.set_xlim(0.1, 1000)
    ax2.set_ylabel(r'Amplitude Spectral Density $[V/\sqrt{Hz}]$', fontsize=12)
    ax2.set_title('Power Spectral Density (PSD)', fontsize=14, fontweight='bold')
    ax2.grid(True, which='both', ls='--', alpha=0.45)
    ax2.legend(loc='upper right', fontsize=10)

    plt.tight_layout()

    if save_dir:
        for filepath, (name, _, _, _, _, _, _) in zip(save_dir, data_list):
            save_path = os.path.join(os.path.dirname(filepath), f"{name}_psd.png")
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Figure saved to: {save_path}")
    else:
        plt.show()
    return fig


def select_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filepaths = filedialog.askopenfilenames(
        title="选择一个或多个振动数据文件",
        filetypes=[("文本文件", "*.txt"), ("CSV文件", "*.csv"), ("所有文件", "*.*")],
        initialdir=os.path.expanduser("~/Desktop")
    )
    root.destroy()
    return list(filepaths)


def main():
    print("请选择数据文件（可多选）...")
    filepaths = select_files()

    if not filepaths:
        print("未选择文件，程序退出。")
        return

    print(f"已选择 {len(filepaths)} 个文件")

    data_list = []
    for filepath in filepaths:
        try:
            name = os.path.basename(filepath).replace('.txt', '').replace('.csv', '')
            print(f"  加载: {name}...")
            t, v, fs, unit = load_vibration_data(filepath)
            freq, psd, asd = compute_psd(v, fs, nfft=100000, overlap_ratio=0.5)
            data_list.append((name, t, v, fs, freq, asd, unit))

            df = freq[1] - freq[0] if len(freq) > 1 else 1.0
            rms = np.sqrt(np.sum(asd**2 * df)) * 1000
            peak_idx = np.argmax(asd[1:]) + 1
            print(f"      RMS: {rms:.3f} mV, Peak: {asd[peak_idx]*1000:.3f} mV/√Hz @ {freq[peak_idx]:.2f} Hz")
        except Exception as e:
            print(f"  加载失败 {filepath}: {e}")

    if not data_list:
        print("没有成功加载任何文件。")
        return

    plot_psd_multi(data_list, save_dir=None)
    print("完成!")


if __name__ == '__main__':
    main()