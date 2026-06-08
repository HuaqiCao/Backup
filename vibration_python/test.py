import matplotlib
try:
    matplotlib.use('Qt5Agg')
except ImportError:
    matplotlib.use('TkAgg')

import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import os
import re

def read_psd_raw(file_path):
    freqs, psds = [], []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f.readlines():
                line = line.strip()
                if re.match(r'^\s*[\d\.e\-]', line):
                    parts = re.split(r'\s+', line)
                    if len(parts) >= 2:
                        try:
                            freqs.append(float(parts[0]))
                            psds.append(float(parts[1]))
                        except ValueError:
                            continue
    except Exception as e:
        print(f"读取文件出错: {e}")
    return np.array(freqs), np.array(psds)

def main():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    files = filedialog.askopenfilenames(title="选择 PSD 数据文件", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    root.destroy()

    if not files:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    for idx, path in enumerate(files):
        freqs, psds = read_psd_raw(path)
        if len(freqs) == 0:
            continue
        filename = os.path.basename(path)
        color = colors[idx % len(colors)]
        ax.plot(freqs, psds, label=filename, color=color, linewidth=0.8, rasterized=True)

    ax.set_xscale('log')
    ax.set_xlim(0.001, 2.5)
    ax.set_ylim(-140, -20)
    ax.grid(True, which="both", ls="--", alpha=0.5, color='#cccccc')
    ax.set_xlabel('Frequency (kHz)', fontsize=12)
    ax.set_ylabel('Amplitude (dBV)', fontsize=12)
    ax.legend(loc='upper right', framealpha=0.8)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()