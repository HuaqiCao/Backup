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
from itertools import combinations

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

    save_dir = os.path.dirname(os.path.abspath(__file__))
    colors = ['#1f77b4', '#ff7f0e']

    for file_a, file_b in combinations(files, 2):
        freqs_a, psds_a = read_psd_raw(file_a)
        freqs_b, psds_b = read_psd_raw(file_b)

        if len(freqs_a) == 0 or len(freqs_b) == 0:
            continue

        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(freqs_a, psds_a, label=os.path.basename(file_a), color=colors[0], linewidth=0.8, rasterized=True, alpha=0.6)
        ax.plot(freqs_b, psds_b, label=os.path.basename(file_b), color=colors[1], linewidth=0.8, rasterized=True, alpha=0.6)

        ax.set_xscale('log')
        ax.set_xlim(0.001, 2.5)
        ax.set_ylim(-140, -20)
        ax.grid(True, which="both", ls="--", alpha=0.5, color='#cccccc')
        ax.set_xlabel('Frequency (kHz)', fontsize=12)
        ax.set_ylabel('Amplitude (dBV)', fontsize=12)
        ax.legend(loc='upper right', framealpha=0.8)

        plt.tight_layout()

        save_name = f"Compare_{os.path.splitext(os.path.basename(file_a))[0]}_vs_{os.path.splitext(os.path.basename(file_b))[0]}.png"
        save_path = os.path.join(save_dir, save_name)
        plt.savefig(save_path, dpi=150)
        plt.close()
        
        print(f"已保存: {save_path}")

if __name__ == "__main__":
    main()