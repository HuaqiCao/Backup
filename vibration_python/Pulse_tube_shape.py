import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
from tkinter import Tk, filedialog

f0 = 1.4
T0 = 1 / f0
gain = 100

root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(title="Select CSV File")
print("Selected:", file_path)

#df = pd.read_csv(file_path, skiprows=4, header=None, encoding="utf-8-sig")
df = pd.read_csv(file_path, skiprows=4, header=None, encoding="gbk")
t = df.iloc[:, 0].astype(float).values
x_raw = df.iloc[:, 1].astype(float).values

dt = np.mean(np.diff(t))
fs = 1 / dt
print(f"自动计算的采样率 fs = {fs:.2f} Hz")

N0 = int(fs * T0)

x_raw_v = x_raw / gain
x_raw_v -= np.mean(x_raw_v)

num_cycles = len(x_raw_v) // N0
print("可用完整周期：", num_cycles)
assert num_cycles >= 6

segments = np.array([x_raw_v[i*N0:(i+1)*N0] for i in range(num_cycles)])
segments6 = segments[:6]

all_cycles_smooth = np.array([savgol_filter(segments[i], 151, 3) for i in range(num_cycles)])
print(f"所有周期平滑后的波形形状: {all_cycles_smooth.shape}")

single_cycle_smooth = all_cycles_smooth[0]
print(f"单个脉冲平滑后的波形形状: {single_cycle_smooth.shape}")

avg_cycle = np.mean(segments, axis=0)
avg_cycle_smooth = savgol_filter(avg_cycle, 151, 3)

np.save(r"D:\Backup\all_cycles_smoothed_springs.npy", all_cycles_smooth)
print(f"已保存所有周期平滑后的波形: D:\\Backup\\all_cycles_smoothed_springs.npy (形状: {all_cycles_smooth.shape})")
np.save(r"D:\Backup\single_cycle_smoothed_springs.npy", single_cycle_smooth)
print(f"已保存单个脉冲平滑后的波形: D:\\Backup\\single_cycle_smoothed_springs.npy (形状: {single_cycle_smooth.shape})")

print("\n所有波形数据已保存完成！")

def fft_amp(sig, fs):
    w = np.hanning(len(sig))
    S = np.fft.rfft(sig * w)
    f = np.fft.rfftfreq(len(sig), 1/fs)
    return f, np.abs(S)

raw6 = x_raw_v[:6*N0]
avg6 = np.tile(avg_cycle, 6)
smooth6 = np.tile(avg_cycle_smooth, 6)

sig2_raw = x_raw_v[:num_cycles * N0]
sig2_avg = np.tile(avg_cycle, num_cycles)
sig2_smooth = np.tile(avg_cycle_smooth, num_cycles)

f2_raw, A2_raw = fft_amp(sig2_raw, fs)
f2_avg, A2_avg = fft_amp(sig2_avg, fs)
f2_smooth, A2_smooth = fft_amp(sig2_smooth, fs)

sig4_raw = x_raw_v[:1*N0]
sig4_avg = np.tile(avg_cycle, 1)
sig4_smooth = np.tile(avg_cycle_smooth, 1)

f4_raw, A4_raw = fft_amp(sig4_raw, fs)
f4_avg, A4_avg = fft_amp(sig4_avg, fs)
f4_smooth, A4_smooth = fft_amp(sig4_smooth, fs)

plt.figure(figsize=(10,4))
t6 = np.arange(len(raw6)) / fs
plt.plot(t6, raw6, color="#1f77b4")
plt.plot(t6, avg6, color="#2ca02c", linewidth=2.5)
plt.plot(t6, smooth6, color="#ff7f0e")
plt.title("Figure 1: Six-Cycle Comparison")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.grid(True)
plt.legend(["Raw", "Averaged", "Smoothed"])

plt.figure(figsize=(10,4))
mask2 = f2_raw <= 100
plt.plot(f2_raw[mask2], A2_raw[mask2], color="#1f77b4")
plt.plot(f2_avg[mask2], A2_avg[mask2], color="#2ca02c", linewidth=2.5)
plt.plot(f2_smooth[mask2], A2_smooth[mask2], color="#ff7f0e")
plt.title("Figure 2: Spectrum (0–100 Hz)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude")
plt.grid(True)
plt.legend(["Raw", "Averaged", "Smoothed"])

plt.figure(figsize=(10,4))
plt.plot(t6, raw6, color="#1f77b4")
plt.title("Figure 3: First 6 Cycles of Real Data")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.grid(True)

plt.figure(figsize=(10,4))
plt.plot(f4_raw, A4_raw, color="#1f77b4")
plt.plot(f4_avg, A4_avg, color="#2ca02c", linewidth=2.5)
plt.plot(f4_smooth, A4_smooth, color="#ff7f0e")
plt.xscale("log")
plt.yscale("log")
plt.title("Figure 4: Spectrum of 1 Cycles (log-log)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude")
plt.grid(True, which="both")
plt.legend(["Raw", "Averaged", "Smoothed"])

plt.figure(figsize=(10,4))
x_axis_5000 = np.arange(N0) / 5000
plt.plot(x_axis_5000, sig4_raw, color="#1f77b4", alpha=0.5, label="Raw Cycle")
plt.plot(x_axis_5000, avg_cycle, color="#2ca02c", linewidth=2.5, label="Averaged Cycle")
plt.plot(x_axis_5000, avg_cycle_smooth, color="#ff7f0e", label="Smoothed Cycle")
plt.title("Figure 5: Single Cycle Comparison (Raw vs Avg vs Smooth)")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()