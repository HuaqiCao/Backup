import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window, find_peaks
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import pandas as pd
import re

# ===================== 环境配置：罗马字体与负号修复 =====================
# Set font to one that supports both Chinese and English characters
plt.rcParams['font.family'] = 'Arial Unicode MS'  # For MacOS (supports both English and Chinese)
# If 'Arial Unicode MS' is unavailable, you can use other alternatives like 'STHeiti' (if on macOS) or 'Microsoft YaHei'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False  # Ensures negative signs are displayed correctly

def process_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="选择数据文件 (可多选 TXT 文件)",
        filetypes=[("文本文件", "*.txt")]
    )

    if not file_paths:
        return

    peak_data = []  # To store peak data (frequency, peak value)
    gain_values = []  # List to store gain values
    lpsd_1_40Hz_values = []  # To store average LPSD values between 1-40Hz for each file

    # Processing each file
    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        try:
            # --- 读取 TXT 文件 ---
            if ext == '.txt':
                # Read the file assuming it's space or tab-separated
                df = pd.read_csv(file_path, delimiter=r'\s+', header=None, dtype={0: 'str', 1: 'str'}, skiprows=1)  # Skip the first row (header)

                # Remove any non-numeric characters from the time and voltage columns
                df[0] = df[0].replace(r'[^\d.]+', '', regex=True)  # Remove non-numeric characters from the time column
                df[1] = df[1].replace(r'[^\d.-]+', '', regex=True)  # Remove non-numeric characters from the voltage column

                # Convert the columns to numeric, coercing any errors (non-numeric values become NaN)
                df[0] = pd.to_numeric(df[0], errors='coerce')
                df[1] = pd.to_numeric(df[1], errors='coerce')

                # --- Remove rows where any column has NaN values (invalid data) ---
                df = df.dropna(subset=[0, 1])  # Drop rows with NaN values in either column

                # Extract time and voltage data from the first and second columns
                time_data = df.iloc[:, 0].values  # First column as time (in seconds)
                voltage_data = df.iloc[:, 1].values  # Second column as voltage (V)

                # Check the units of the second column (voltage)
                if 'mv' in filename.lower():  # If the filename contains 'mv' (case insensitive)
                    print(f"{filename}: 发现单位为毫伏 (mV)，正在转换为伏特 (V)")
                    voltage_data /= 1000  # Convert mV to V
                    
                # Ensure time_data has enough valid points (must be greater than 2)
                if len(time_data) < 2 or np.any(np.isnan(time_data)):
                    print(f"{filename}: 时间数据无效，无法计算采样率")
                    continue

                # --- Calculate Time Differences ---
                time_diff = np.diff(time_data)

                # Directly calculate the sampling rate from the time differences
                fs = 1 / np.mean(time_diff)  # Calculate sampling rate as the inverse of the average time difference
                print(f"{filename}: 计算的采样率 = {fs:.2f} Hz")

                # --- Parameters for processing ---
                sen = 0.957
                g = 9.81
                wint = 5

                # Extract gain value from the filename
                gain_match = re.search(r'gain(\d+)', filename.lower())
                if gain_match:
                    gain = float(gain_match.group(1))
                else:
                    gain = 100.0  # Default value if not found
                gain_values.append(gain)

                # --- 3. 去除前后30秒数据 ---
                num_samples_to_remove = int(30 * fs)  # 30 seconds of samples
                if len(voltage_data) > 2 * num_samples_to_remove:
                    voltage_data = voltage_data[num_samples_to_remove:-num_samples_to_remove]  # Remove 30 seconds from both ends
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

                # --- 6. 计算 1-40 Hz 区间的 LPSD 平均值 ---
                freq_range = (freqs >= 1) & (freqs <= 40)
                avg_lpsd_1_40Hz = np.mean(np.sqrt(psd_avg[freq_range]))  # 平均值计算
                lpsd_1_40Hz_values.append(avg_lpsd_1_40Hz)

                # 输出采样率和时间长度
                print(f"处理完成: {filename}, 采样率: {fs} Hz, 数据时间长度: {len(acc_data) / fs:.2f} s, 频率分辨率: {fs / nfft:.2f} Hz")
                
        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- 绘制图表 ---
    if lpsd_1_40Hz_values and gain_values:
        plt.figure(figsize=(10, 6))
        plt.plot(gain_values, lpsd_1_40Hz_values, marker='o', linestyle='-', color='b')
        plt.xlabel("Gain (m)", fontsize=12, fontname="Arial Unicode MS")
        plt.ylabel("Average LPSD (1-40 Hz)", fontsize=12, fontname="Arial Unicode MS")
        plt.title("LPSD Average (1-40 Hz) vs Gain", fontsize=14, fontname="Arial Unicode MS", fontweight='bold')
        plt.grid(True, which="both", ls="-", alpha=0.3)
        plt.tight_layout()
        plt.show()
    else:
        print("没有有效数据可用于绘制图表")

if __name__ == "__main__":
    process_files()