import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window, find_peaks
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import pandas as pd

# ===================== 环境配置：确保字体可以显示中文 =====================
# For macOS, use STHeiti or PingFang SC for Chinese characters
plt.rcParams['font.family'] = 'STHeiti'  # For macOS, use 'STHeiti' or 'PingFang SC'
# If you want to use PingFang SC, you can replace with:
# plt.rcParams['font.family'] = 'PingFang SC'

plt.rcParams['axes.unicode_minus'] = False  # Ensure minus sign shows properly

def process_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="选择数据文件 (可多选 TXT 或 CSV 文件)",
        filetypes=[("文本文件", "*.txt"), ("CSV文件", "*.csv")]
    )

    if not file_paths:
        return

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']

    peak_data = []  # To store peak data (frequency, peak value)
    gain_used = []  # To store the gain used for each file

    plt.figure(figsize=(10, 6))  # Create a single figure for all files

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        try:
            # --- 读取文件 ---
            if ext == '.txt':
                # Process TXT file (space or tab-separated)
                df = pd.read_csv(file_path, delimiter=r'\s+', header=None, dtype={0: 'str', 1: 'str'}, skiprows=1)

            elif ext == '.csv':
                # Process CSV file
                df = pd.read_csv(file_path, header=None, dtype={0: 'str', 1: 'str'}, encoding='utf-8')  # Ensure UTF-8 encoding

                # Convert the second column from nanovolts (nV) to volts (V)
                df[1] = pd.to_numeric(df[1], errors='coerce') * 1e-9  # Convert nV to V

            else:
                print(f"不支持的文件格式: {filename}")
                continue

            # Remove non-numeric characters from the time and voltage columns
            df[0] = df[0].replace(r'[^\d.]+', '', regex=True)  # Remove non-numeric characters from the time column
            df[1] = df[1].replace(r'[^\d.-]+', '', regex=True)  # Remove non-numeric characters from the voltage column

            # Convert the columns to numeric, coercing any errors (non-numeric values become NaN)
            df[0] = pd.to_numeric(df[0], errors='coerce')
            df[1] = pd.to_numeric(df[1], errors='coerce')

            # --- Remove rows where any column has NaN values (invalid data) ---
            df = df.dropna(subset=[0, 1])  # Drop rows with NaN values in either column

            # Check if the file has the correct number of columns
            if df.shape[1] < 2:
                print(f"{filename}: 数据格式不正确，必须包含时间和电压值")
                continue

            # Extract time and voltage data from the first and second columns
            time_data = df.iloc[:, 0].values  # First column as time (in seconds)
            voltage_data = df.iloc[:, 1].values  # Second column as voltage (V)

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

            # Default gain is 100, with adjustments based on filename
            gain = 100.0  # Default gain value
            if "gain100" in filename.lower():
                gain = 100.122
            elif "gain10" in filename.lower():
                gain = 10.003

            gain_used.append(gain)  # Store the gain used for this file

            # --- 3. 去除前后30秒数据 ---
            num_samples_to_remove = int(60 * fs)  # 60秒的样本数
            if len(voltage_data) > 2 * num_samples_to_remove:
                voltage_data = voltage_data[num_samples_to_remove:-num_samples_to_remove]  # 去掉前后30秒数据
            else:
                print(f"{filename}: 数据长度不足以去除60秒")
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

            # --- 6. LPSD Calculation using the correct formula ---
            lpsd = np.sqrt(psd_avg)  # Correct LPSD as the square root of the average PSD

            # Plot PSD in the same figure for all files
            plt.loglog(freqs, psd_avg, label=filename, color=colors[idx % len(colors)], linewidth=1.2)

        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- Plot all PSDs in one figure ---
    plt.xlabel("Frequency (Hz)", fontsize=12, fontname="STHeiti")  # Use STHeiti for macOS
    plt.ylabel(r"PSD ($g^2/Hz$)", fontsize=12, fontname="STHeiti")
    plt.title("All Files: PSD Comparison", fontsize=14, fontname="STHeiti", fontweight='bold')
    plt.grid(True, which="both", ls="-", alpha=0.3)
    plt.grid(True, which="minor", ls=":", alpha=0.1)
    plt.xlim(1, None)
    
    # Adjust legend properties to remove the box around the text and ensure Chinese characters display correctly
    plt.legend(prop={'family': 'STHeiti', 'size': 9}, frameon=False)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    process_files()