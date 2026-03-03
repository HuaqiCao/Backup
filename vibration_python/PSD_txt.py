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

def extract_m_value(filename):
    """
    从文件名中提取m值（例如：文件名中的"0.5m"、"1m"等）
    返回提取到的m值（浮点数），如果没有找到则返回None
    """
    # 匹配模式：数字后跟m（如：0.5m, 1m, 2.5m等）
    pattern = r'(\d+(?:\.\d+)?)m'
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

def get_display_name(filename):
    """
    从完整文件名中提取显示名称（去除扩展名）
    例如：'5m_L.txt' -> '5m_L'
    """
    return os.path.splitext(os.path.basename(filename))[0]

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
    
    # 创建两个图形：一个用于频谱图，一个用于m值关系图
    fig1 = plt.figure(figsize=(10, 6))
    fig2 = plt.figure(figsize=(10, 6))

    peak_data = []  # To store peak data (frequency, peak value)
    m_value_data = []  # To store [display_name, m value, average LPSD (1-40Hz)]
    gain_value = None  # Variable to store gain value for output

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        display_name = get_display_name(filename)  # 获取显示名称（如"5m_L"）
        ext = os.path.splitext(filename)[1].lower()

        try:
            # 从文件名中提取m值
            m_value = extract_m_value(filename)
            if m_value is None:
                print(f"{filename}: 未找到m值，跳过该文件")
                continue

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

                # Check if the file has the correct number of columns
                if df.shape[1] < 2:
                    print(f"{filename}: 数据格式不正确，必须包含时间和电压值")
                    continue

                # Extract time and voltage data from the first and second columns
                time_data = df.iloc[:, 0].values  # First column as time (in seconds)
                voltage_data = df.iloc[:, 1].values  # Second column as voltage (V)

                # Check the units of the second column (voltage)
                # Assuming the user mentions "mV" or "milliVolt" as part of the filename for mV data
                if 'mv' in filename.lower():  # If the filename contains 'mv' (case insensitive)
                    print(f"{filename}: 发现单位为毫伏 (mV)，正在转换为伏特 (V)")
                    voltage_data /= 1000  # Convert mV to V
                    
                # Debugging: print the time data to check for invalid entries
                print(f"Time data after conversion: {time_data[:10]}")  # Print the first 10 values of time data

                # Ensure time_data has enough valid points (must be greater than 2)
                if len(time_data) < 2 or np.any(np.isnan(time_data)):
                    print(f"{filename}: 时间数据无效，无法计算采样率")
                    continue

                # --- Calculate Time Differences ---
                time_diff = np.diff(time_data)

                # Debugging: print time differences to check for irregularities
                print(f"Time differences: {time_diff[:10]}")  # Print the first 10 time differences

                # Directly calculate the sampling rate from the time differences
                fs = 1 / np.mean(time_diff)  # Calculate sampling rate as the inverse of the average time difference
                print(f"{filename}: 计算的采样率 = {fs:.2f} Hz")

                # --- Parameters for processing ---
                sen = 0.957
                g = 9.81
                wint = 5

                if "gain100" in filename.lower():
                    gain = 100.122
                elif "gain10" in filename.lower():
                    gain = 10.003
                else:
                    gain = 100.0
                    gain_value = gain  # Store gain value for output

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

                # --- 6. 计算LPSD ---
                lpsd = np.sqrt(psd_avg)

                # --- 7. 计算1-40Hz的平均值 ---
                # 找到1-40Hz频率范围的索引
                freq_mask = (freqs >= 1) & (freqs <= 40)
                if np.any(freq_mask):
                    lpsd_avg_1_40 = np.mean(lpsd[freq_mask])
                    # 存储显示名称、m值、LPSD平均值
                    m_value_data.append([display_name, m_value, lpsd_avg_1_40])
                    print(f"{display_name}: m={m_value}m, 1-40Hz平均LPSD={lpsd_avg_1_40:.6f} g/√Hz")
                else:
                    print(f"{display_name}: 频率范围不足1-40Hz")

                # Find peaks in the LPSD data (with height threshold)
                height_threshold = np.max(lpsd) * 0.1  # Only consider peaks that are 10% of the maximum peak height
                peaks, _ = find_peaks(lpsd, height=height_threshold)  # Find peaks with height greater than threshold

                # Record peak data (frequency, peak value)
                for peak in peaks:
                    peak_freq = freqs[peak]
                    peak_value = lpsd[peak]
                    peak_data.append([peak_freq, peak_value])  # Only store frequency and peak value

                # Plot the data with peaks on the first figure
                plt.figure(fig1.number)
                plt.loglog(freqs, lpsd,
                            label=f"{display_name} | Gain: {gain} | Sen: {sen}", 
                            color=colors[idx % len(colors)], 
                            linewidth=1.2)

                # 输出采样率和时间长度
                print(f"处理完成: {display_name}, 采样率: {fs} Hz, 数据时间长度: {len(acc_data) / fs:.2f} s, 频率分辨率: {fs / nfft:.2f} Hz")
                
                # --- Output last row of data ---
                last_row = df.iloc[-1]  # Extract the last row
                print(f"Last row of {display_name}: {last_row}")

        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- Output peak data as a DataFrame ---
    peak_df = pd.DataFrame(peak_data, columns=["Frequency (Hz)", "Peak Value"])
    # Sort peak data by peak value in descending order
    peak_df_sorted = peak_df.sort_values(by="Peak Value", ascending=False).reset_index(drop=True)
    
    # Print the top 20 peaks (sorted by peak value)
    print("\nTop 20 Peak Data Recorded (sorted by peak value):")
    print(peak_df_sorted.head(20))

    # --- 绘制m值与1-40Hz平均LPSD的关系图（双y轴，38m归一化为1）---
    if m_value_data:
        # 提取数据 - 现在每个item是 [display_name, m_value, lpsd_value]
        display_names = [item[0] for item in m_value_data]
        m_values = [item[1] for item in m_value_data]
        lpsd_avg_values = [item[2] for item in m_value_data]
        
        # 找到38m对应的平均值（作为基准值）
        ref_index = None
        for i, m in enumerate(m_values):
            if abs(m - 38.0) < 0.1:  # 允许0.1的误差
                ref_index = i
                break
        
        if ref_index is not None:
            ref_value = lpsd_avg_values[ref_index]
            print(f"\n以38m ({ref_value:.6f} g/√Hz) 为基准，计算相对比值：")
            
            # 计算相对比值（38m的比值为1）
            relative_ratios = [val / ref_value for val in lpsd_avg_values]
            
            # 创建双y轴图
            fig2, ax1 = plt.subplots(figsize=(10, 6))
            
            # 左y轴：原始LPSD平均值
            color1 = '#1f77b4'
            ax1.set_xlabel("Distance (m)", fontsize=12, fontname="Arial Unicode MS")
            ax1.set_ylabel(r"Average LPSD (1-40 Hz) ($g/\sqrt{Hz}$)", fontsize=12, fontname="Arial Unicode MS", color=color1)
            
            # 使用折线图连接点
            line1 = ax1.plot(m_values, lpsd_avg_values, 'o-', color=color1, linewidth=2, markersize=8, 
                             markerfacecolor='white', markeredgewidth=2, label='LPSD Average')
            ax1.tick_params(axis='y', labelcolor=color1)
            ax1.grid(True, alpha=0.3)
            
            # 右y轴：相对比值（38m归一化为1）
            color2 = '#d62728'
            ax2 = ax1.twinx()
            ax2.set_ylabel(r"Relative Ratio (38m = 1)", fontsize=12, fontname="Arial Unicode MS", color=color2)
            
            # 绘制相对比值曲线（在右y轴上）
            line2 = ax2.plot(m_values, relative_ratios, 's--', color=color2, linewidth=1.5, markersize=6, 
                             markerfacecolor='white', markeredgewidth=1.5, label='Relative Ratio')
            ax2.tick_params(axis='y', labelcolor=color2)
            
            # 添加水平参考线（y=1）- 对应38m
            ax2.axhline(y=1, color=color2, linestyle=':', linewidth=1, alpha=0.5)
            
            # 标记38m点的位置
            if ref_index is not None:
                ax2.plot(m_values[ref_index], 1, 'o', color=color2, markersize=8, 
                         markerfacecolor='white', markeredgewidth=2)
            
            # 添加标题
            plt.title("Average Vibration Level vs. Distance", fontsize=14, fontname="Arial Unicode MS", fontweight='bold')
            
            # 为每个点添加标注（显示完整显示名称，如"5m_L"）
            for i, (m, y, name) in enumerate(zip(m_values, lpsd_avg_values, display_names)):
                ax1.annotate(name, (m, y), textcoords="offset points", xytext=(0,10), 
                             ha='center', fontsize=8, rotation=0, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
            
            # 合并图例
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper right', fontsize=10)
            
            # 打印相对比值信息
            print(f"\n各文件的相对比值（以38m=1为基准）：")
            for name, m, rel in zip(display_names, m_values, relative_ratios):
                print(f"{name} (距离{m}m): {rel:.3f}")
                
        else:
            print(f"\n未找到38m数据，无法进行归一化。将使用原始数据绘制。")
            
            # 如果没有38m数据，只绘制左y轴的原始数据
            fig2, ax1 = plt.subplots(figsize=(10, 6))
            
            color1 = '#1f77b4'
            ax1.set_xlabel("Distance (m)", fontsize=12, fontname="Arial Unicode MS")
            ax1.set_ylabel(r"Average LPSD (1-40 Hz) ($g/\sqrt{Hz}$)", fontsize=12, fontname="Arial Unicode MS", color=color1)
            line1 = ax1.plot(m_values, lpsd_avg_values, 'o-', color=color1, linewidth=2, markersize=8, 
                             markerfacecolor='white', markeredgewidth=2, label='LPSD Average')
            ax1.tick_params(axis='y', labelcolor=color1)
            ax1.grid(True, alpha=0.3)
            
            # 为每个点添加标注（显示完整显示名称，如"5m_L"）
            for i, (m, y, name) in enumerate(zip(m_values, lpsd_avg_values, display_names)):
                ax1.annotate(name, (m, y), textcoords="offset points", xytext=(0,10), 
                             ha='center', fontsize=8, rotation=0, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
            
            plt.title("Average Vibration Level vs. Distance", fontsize=14, fontname="Arial Unicode MS", fontweight='bold')
            ax1.legend(loc='upper right', fontsize=10)
        
        plt.tight_layout()
    else:
        print("没有有效的m值数据用于绘制关系图")

    # --- 7. 图表修饰 (第一个图) ---
    plt.figure(fig1.number)
    if plt.gca().has_data():
        plt.xlabel("Frequency (Hz)", fontsize=12, fontname="Arial Unicode MS")
        plt.ylabel(r"LPSD ($g/\sqrt{Hz}$)", fontsize=12, fontname="Arial Unicode MS")
        plt.title("Vibration Acceleration Spectrum", fontsize=14, fontname="Arial Unicode MS", fontweight='bold')

        plt.grid(True, which="both", ls="-", alpha=0.3)
        plt.grid(True, which="minor", ls=":", alpha=0.1)

        plt.xlim(1, None)
        plt.legend(prop={'family': 'Arial Unicode MS', 'size': 9}, framealpha=0.8)
        plt.tight_layout()
    else:
        print("没有有效数据被绘制")
    
    plt.show()

if __name__ == "__main__":
    process_files()