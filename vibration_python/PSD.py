import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import pandas as pd

# ===================== 环境配置：罗马字体与负号修复 =====================
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

def process_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="选择数据文件 (可多选 TXT 文件)",
        filetypes=[("文本文件", "*.txt")]
    )

    if not file_paths:
        return

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    plt.figure(figsize=(10, 6))

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        try:
            # --- 读取 TXT 文件，跳过前两行标题 ---
            if ext == '.txt':
                # Read the file, skipping the first row as header
                df = pd.read_csv(file_path, delimiter='\t', header=0, dtype={0: 'float64', 1: 'float64'})  # Enforce float64 for both columns

                # Check if the file has the correct number of columns
                if df.shape[1] < 2:
                    print(f"{filename}: 数据格式不正确，必须包含时间和电压值")
                    continue

                # Extract time and voltage data from the first and second columns
                time_data = pd.to_numeric(df.iloc[:, 0], errors='coerce').values  # First column as time (in seconds)
                voltage_data = pd.to_numeric(df.iloc[:, 1], errors='coerce').values  # Second column as voltage (V)

                # Check if time_data is valid
                if len(time_data) < 2:
                    print(f"{filename}: 时间数据长度无效")
                    continue

                # Calculate the time intervals (differences between consecutive time points)
                time_diff = np.diff(time_data)

                # Ensure the time differences are positive and valid
                if np.all(time_diff > 0):
                    fs = 1 / np.mean(time_diff)  # Calculate sampling rate as the inverse of the average time difference
                    print(f"{filename}: 计算的采样率 = {fs:.2f} Hz")
                else:
                    print(f"{filename}: 时间数据无效，无法计算采样率")
                    continue

            # --- 2. 参数设置 ---
            sen = 0.957
            g = 9.81
            wint = 5

            if "gain100" in filename.lower():
                gain = 100.122
            elif "gain10" in filename.lower():
                gain = 10.003
            else:
                gain = 100.0

            # --- 3. 去除前后30秒数据 ---
            num_samples_to_remove = int(60 * fs)  # 30秒的样本数
            if len(voltage_data) > 2 * num_samples_to_remove:
                voltage_data = voltage_data[num_samples_to_remove:-num_samples_to_remove]  # 去掉前后30秒数据
            else:
                print(f"{filename}: 数据长度不足以去除30秒")
                continue

            # --- 4. 信号预处理 ---
            acc_data = voltage_data / (gain * sen) 
            acc_data = acc_data - np.mean(acc_data)  # 去除直流分量

            if len(acc_data) < fs:
                print(f"{filename}: 数据长度过短 ({len(acc_data)} points)")
                continue

            # --- 5. 信号处理 (计算 LPSD) ---
            n = int(wint * fs)
            if n > len(acc_data): 
                n = len(acc_data) // 2
                if n < fs:
                    n = fs

            nfft = 2 ** int(np.ceil(np.log2(n)))
            win = get_window("hann", n)  # 可以更改为其他窗函数，如 'hamming' 或 'blackman'
            win_power = np.sum(win**2)

            step = max(n // 2, 1)
            num_frames = max((len(acc_data) - n) // step + 1, 1)

            psd_sum = np.zeros(nfft // 2 + 1)
            valid_frames = 0

            for i in range(num_frames):
                start = i * step
                end = start + n
                if end > len(acc_data):
                    break

                seg = acc_data[start:end].copy()
                seg = seg - np.mean(seg)  # 去除每个窗段的直流分量
                seg_windowed = seg * win
                sig_fft = fft(seg_windowed, nfft)

                psd_frame = (np.abs(sig_fft[:nfft // 2 + 1])**2) / (fs * win_power)
                psd_frame[1:-1] *= 2

                psd_sum += psd_frame
                valid_frames += 1

            if valid_frames == 0:
                print(f"{filename}: 无有效数据帧")
                continue

            psd_avg = psd_sum / valid_frames
            freqs = np.linspace(0, fs / 2, nfft // 2 + 1)

            # --- 6. 绘图 ---
            lpsd = np.sqrt(psd_avg)

            plt.loglog(freqs, lpsd,
                        label=os.path.splitext(filename)[0], 
                        color=colors[idx % len(colors)], 
                        linewidth=1.2)

            # 输出采样率和时间长度
            print(f"处理完成: {filename}, 采样率: {fs} Hz, 数据时间长度: {len(acc_data) / fs:.2f} s, 频率分辨率: {fs / nfft:.2f} Hz")

        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- 7. 图表修饰 ---
    if plt.gca().has_data():
        plt.xlabel("Frequency (Hz)", fontsize=12, fontname="Times New Roman")
        plt.ylabel(r"LPSD ($g/\sqrt{Hz}$)", fontsize=12, fontname="Times New Roman")
        plt.title("Vibration Acceleration Spectrum", fontsize=14, fontname="Times New Roman", fontweight='bold')

        plt.grid(True, which="both", ls="-", alpha=0.3)
        plt.grid(True, which="minor", ls=":", alpha=0.1)

        plt.xlim(0.1, None)
        plt.legend(prop={'family': 'Times New Roman', 'size': 9}, framealpha=0.8)

        plt.tight_layout()
        plt.show()
    else:
        print("没有有效数据被绘制")

if __name__ == "__main__":
    process_files()