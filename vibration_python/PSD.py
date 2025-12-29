import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import re
from nptdms import TdmsFile

# ===================== 文件选择 =====================
root = Tk()
root.withdraw()
file_paths = filedialog.askopenfilenames(filetypes=[("数据文件", "*.csv *.tdms")])

if not file_paths:
    exit()

# 设置强对比色系
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
plt.figure(figsize=(10, 6))

# ===================== 遍历处理 =====================
for idx, file_path in enumerate(file_paths):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        # --- 鲁棒的数据读取 ---
        if ext == '.csv':
            data = np.loadtxt(file_path, delimiter=',', skiprows=4)[:, 1]
        elif ext == '.tdms':
            tdms = TdmsFile.read(file_path)
            # 修复：遍历所有组，跳过空的 'Default' 组
            data = None
            for group in tdms.groups():
                if len(group.channels()) > 0:
                    data = group.channels()[0].data
                    break
            if data is None: continue
        
        # --- 参数解析 ---
        sen, g, wint = 1.026, 9.81, 5
        # 增益判断
        gain = 100.122 if "100gain" in filename else (10.003 if "10gain" in filename else 1)
        # 采样率提取
        match = re.search(r"(\d+)fs", filename)
        fs = int(match.group(1)) if match else 10000

        # --- 信号处理 ---
        data = data / (gain * sen)  # 电压转加速度
        
        n = int(wint * fs)
        nfft = 2 ** int(np.ceil(np.log2(n)))
        overlap = nfft // 2
        step = n - overlap
        
        # 窗函数归一化
        win = get_window("hann", n)
        win /= np.sqrt(np.mean(win**2))

        # 分帧累加求平均
        psd_sum = np.zeros(nfft//2)
        num_frames = (len(data) - overlap) // step
        for i in range(num_frames):
            seg = data[i*step : i*step+n] * win
            spec = np.abs(fft(seg, nfft)[:nfft//2])**2 / (fs * nfft)
            spec[1:-1] *= 2
            psd_sum += spec
        
        psd_avg = psd_sum / num_frames
        f = np.linspace(0, fs/2, nfft//2, endpoint=False)

        # --- 绘图：实线、粗线、强对比 ---
        plt.loglog(f, np.sqrt(psd_avg), 
                   label=os.path.splitext(filename)[0], 
                   color=colors[idx % len(colors)], 
                   linewidth=1.5, alpha=0.9)

    except Exception as e:
        print(f"处理 {filename} 时出错: {e}")

# ===================== 强对比图像设置 =====================
plt.xlabel("Frequency (Hz)", fontsize=12, fontweight='bold')
plt.ylabel(r"LPSD [$g/\sqrt{Hz}$]", fontsize=12, fontweight='bold')
plt.title("Acceleration PSD Comparison", fontsize=14, pad=15)

# 实虚结合的网格线：主网格实线，次网格虚线
plt.grid(True, which="major", ls="-", color='gray', alpha=0.4)
plt.grid(True, which="minor", ls=":", color='gray', alpha=0.2)

plt.legend(fontsize=9, loc="upper right", framealpha=0.8)
plt.tight_layout()
plt.show()