import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
from tkinter import Tk, filedialog

# ===================== 基本参数 =====================
fs = 10000                      # 采样率
f0 = 1.4                        # 基波频率
T0 = 1 / f0
N0 = int(fs * T0)               # 每周期点数
gain = 100

# ===================== 读取文件 =====================
root = Tk(); root.withdraw()
file_path = filedialog.askopenfilename(title="Select CSV File")
print("Selected:", file_path)

df = pd.read_csv(file_path, skiprows=4, header=None, encoding="gbk")
t = df.iloc[:, 0].astype(float).values
x_raw = df.iloc[:, 1].astype(float).values

x_raw_v = x_raw / gain
x_raw_v -= np.mean(x_raw_v)

# ===================== 周期分段 =====================
num_cycles = len(x_raw_v) // N0
print("可用完整周期：", num_cycles)
assert num_cycles >= 6

segments = np.array([x_raw_v[i*N0:(i+1)*N0] for i in range(num_cycles)])
segments6 = segments[:6]

# ===================== 单周期平均 =====================
avg_cycle = np.mean(segments, axis=0)
avg_cycle_smooth = savgol_filter(avg_cycle, 151, 3)

# ===================== FFT 函数 =====================
def fft_amp(sig, fs):
    w = np.hanning(len(sig))
    S = np.fft.rfft(sig * w)
    f = np.fft.rfftfreq(len(sig), 1/fs)
    return f, np.abs(S)

# ===================== 图1：6周期时域 =====================
raw6 = x_raw_v[:6*N0]
avg6 = np.tile(avg_cycle, 6)
smooth6 = np.tile(avg_cycle_smooth, 6)

# ===================== 图2：全长 FFT =====================
sig2_raw = x_raw_v[:num_cycles * N0]
sig2_avg = np.tile(avg_cycle, num_cycles)
sig2_smooth = np.tile(avg_cycle_smooth, num_cycles)

f2_raw, A2_raw = fft_amp(sig2_raw, fs)
f2_avg, A2_avg = fft_amp(sig2_avg, fs)
f2_smooth, A2_smooth = fft_amp(sig2_smooth, fs)

# ===================== 图4：4周期 FFT =====================
sig4_raw = x_raw_v[:1*N0]
sig4_avg = np.tile(avg_cycle, 1)
sig4_smooth = np.tile(avg_cycle_smooth, 1)

f4_raw, A4_raw = fft_amp(sig4_raw, fs)
f4_avg, A4_avg = fft_amp(sig4_avg, fs)
f4_smooth, A4_smooth = fft_amp(sig4_smooth, fs)

# ===================== 输出每条线的数据长度 =====================
print("\n================= 每个图每根线的数据长度 =================")
print(f"图1：Raw={len(raw6)}, Avg={len(avg6)}, Smooth={len(smooth6)}")
print(f"图2 FFT：Raw={len(A2_raw)}, Avg={len(A2_avg)}, Smooth={len(A2_smooth)}")
print(f"图3：Raw6={len(raw6)}")
print(f"图4 FFT：Raw={len(A4_raw)}, Avg={len(A4_avg)}, Smooth={len(A4_smooth)}")
print(f"图5：Avg={len(avg_cycle)}, Smooth={len(avg_cycle_smooth)}")
print("============================================================\n")

# ===================== 图4主峰提取 =====================
def top_k_peaks(f, A, k=5):
    peaks, _ = find_peaks(A)
    if len(peaks) == 0:
        return []
    idx = np.argsort(A[peaks])[::-1][:k]
    return f[peaks[idx]]

peaks_raw = top_k_peaks(f4_raw, A4_raw)
peaks_avg = top_k_peaks(f4_avg, A4_avg)
peaks_smooth = top_k_peaks(f4_smooth, A4_smooth)

print("============= 图4：4周期 FFT 前 5 个主峰 =============")
print("Raw：     ", np.round(np.sort(peaks_raw), 6))
print("Avg：     ", np.round(np.sort(peaks_avg), 6))
print("Smooth：  ", np.round(np.sort(peaks_smooth), 6))
print("======================================================\n")

# ===================== 绘图 =====================

# ---- 图1：6周期 ----
plt.figure(figsize=(10,4))
t6 = np.arange(len(raw6)) / fs
plt.plot(t6, raw6, color="#1f77b4")
plt.plot(t6, avg6, color="#2ca02c", linewidth=2.5)
plt.plot(t6, smooth6, color="#ff7f0e")
plt.title("Figure 1: Six-Cycle Comparison")
plt.xlabel("Time (s)"); plt.ylabel("Voltage (V)")
plt.grid(True); plt.legend(["Raw", "Averaged", "Smoothed"])

# ---- 图2：全长 FFT（0–60 Hz）----
plt.figure(figsize=(10,4))
mask2 = f2_raw <= 100
plt.plot(f2_raw[mask2], A2_raw[mask2], color="#1f77b4")
plt.plot(f2_avg[mask2], A2_avg[mask2], color="#2ca02c", linewidth=2.5)
plt.plot(f2_smooth[mask2], A2_smooth[mask2], color="#ff7f0e")
plt.title("Figure 2: Spectrum (0–100 Hz)")
plt.xlabel("Frequency (Hz)"); plt.ylabel("Amplitude")
plt.grid(True); plt.legend(["Raw", "Averaged", "Smoothed"])

# ---- 图3：真实数据前6周期 ----
plt.figure(figsize=(10,4))
plt.plot(t6, raw6, color="#1f77b4")
plt.title("Figure 3: First 6 Cycles of Real Data")
plt.xlabel("Time (s)"); plt.ylabel("Voltage (V)")
plt.grid(True)

# ---- 图4：单周期 FFT（log-log）----
plt.figure(figsize=(10,4))
plt.plot(f4_raw, A4_raw, color="#1f77b4")
plt.plot(f4_avg, A4_avg, color="#2ca02c", linewidth=2.5)
plt.plot(f4_smooth, A4_smooth, color="#ff7f0e")
plt.xscale("log"); plt.yscale("log")
plt.title("Figure 4: Spectrum of 1 Cycles (log-log)")
plt.xlabel("Frequency (Hz)"); plt.ylabel("Amplitude")
plt.grid(True, which="both")
plt.legend(["Raw", "Averaged", "Smoothed"])

# ---- 图5：单周期 ----
plt.figure(figsize=(10,4))
t_cycle = np.arange(N0) / fs
plt.plot(t_cycle, avg_cycle, color="#2ca02c", linewidth=2.5)
plt.plot(t_cycle, avg_cycle_smooth, color="#ff7f0e")
plt.title("Figure 5: Single Cycle (Averaged vs Smoothed)")
plt.xlabel("Time (s)"); plt.ylabel("Voltage (V)")
plt.grid(True); plt.legend(["Averaged Cycle", "Smoothed Cycle"])

plt.tight_layout()
plt.show()
