import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window, find_peaks
from scipy.fft import fft
from tkinter import Tk, filedialog, simpledialog
import os
import pandas as pd
import re

# ===================== 环境配置：罗马字体与负号修复 =====================
plt.rcParams['font.family'] = 'Arial Unicode MS'  # For MacOS
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

def extract_m_value(filename):
    """
    从文件名中提取m值（例如：文件名中的"0.5m"、"1m"等）
    返回提取到的m值（浮点数），如果没有找到则返回None
    """
    pattern = r'(\d+(?:\.\d+)?)m'
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

def get_display_name(filename):
    """
    从完整文件名中提取显示名称（去除扩展名）
    """
    return os.path.splitext(os.path.basename(filename))[0]

def select_reference_file(display_names):
    """
    让用户选择作为基准（标准1）的文件
    """
    root = Tk()
    root.withdraw()
    
    # 创建选择对话框
    dialog_text = "请选择作为基准（标准1）的文件：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(display_names)])
    
    choice = simpledialog.askinteger("选择基准文件", 
                                     dialog_text + "\n\n请输入数字 (1-{}):".format(len(display_names)),
                                     minvalue=1, maxvalue=len(display_names))
    
    if choice:
        return choice - 1  # 转换为0-based索引
    return 0  # 默认选择第一个

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
    
    # 创建两个图形
    fig1 = plt.figure(figsize=(10, 6))
    fig2 = plt.figure(figsize=(8, 6))

    peak_data = []  # 存储峰值数据
    file_data = []  # 存储 [display_name, m_value(或None), lpsd_avg, filename_without_ext]
    gain_value = None

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        display_name = get_display_name(filename)  # 显示名称（不含扩展名）
        ext = os.path.splitext(filename)[1].lower()

        try:
            # 从文件名中提取m值
            m_value = extract_m_value(filename)
            if m_value is None:
                print(f"{filename}: 未找到m值，将使用文件名作为标签")
                # 不使用m值，直接用文件名

            # --- 读取 TXT 文件 ---
            if ext == '.txt':
                df = pd.read_csv(file_path, delimiter=r'\s+', header=None, dtype={0: 'str', 1: 'str'}, skiprows=1)

                # 清理数据
                df[0] = df[0].replace(r'[^\d.]+', '', regex=True)
                df[1] = df[1].replace(r'[^\d.-]+', '', regex=True)

                df[0] = pd.to_numeric(df[0], errors='coerce')
                df[1] = pd.to_numeric(df[1], errors='coerce')

                df = df.dropna(subset=[0, 1])

                if df.shape[1] < 2:
                    print(f"{filename}: 数据格式不正确，必须包含时间和电压值")
                    continue

                time_data = df.iloc[:, 0].values
                voltage_data = df.iloc[:, 1].values

                # 单位转换
                if 'mv' in filename.lower():
                    print(f"{filename}: 发现单位为毫伏 (mV)，正在转换为伏特 (V)")
                    voltage_data /= 1000

                # 计算采样率
                if len(time_data) < 2 or np.any(np.isnan(time_data)):
                    print(f"{filename}: 时间数据无效，无法计算采样率")
                    continue

                time_diff = np.diff(time_data)
                fs = 1 / np.mean(time_diff)
                print(f"{filename}: 计算的采样率 = {fs:.2f} Hz")

                # 参数设置
                sen = 0.957
                g = 9.81
                wint = 5

                if "gain100" in filename.lower():
                    gain = 100.122
                elif "gain10" in filename.lower():
                    gain = 10.003
                else:
                    gain = 100.0
                    gain_value = gain

                # 去除前后30秒数据
                num_samples_to_remove = int(30 * fs)
                if len(voltage_data) > 2 * num_samples_to_remove:
                    voltage_data = voltage_data[num_samples_to_remove:-num_samples_to_remove]
                else:
                    print(f"{filename}: 数据长度不足以去除30秒")
                    continue 

                # 信号预处理
                acc_data = voltage_data / (gain * sen) 
                acc_data = acc_data - np.mean(acc_data)

                if len(acc_data) < fs:
                    print(f"{filename}: 数据长度过短 ({len(acc_data)} points)")
                    continue

                # 信号处理 (计算 LPSD)
                n = int(wint * fs)
                if n > len(acc_data): 
                    n = len(acc_data) // 2
                    if n < fs:
                        n = fs

                nfft = 2 ** int(np.ceil(np.log2(n)))
                win = get_window("hann", n)
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
                    seg = seg - np.mean(seg)
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

                # 计算LPSD
                lpsd = np.sqrt(psd_avg)

                # 计算1-40Hz的平均值
                freq_mask = (freqs >= 1) & (freqs <= 40)
                if np.any(freq_mask):
                    lpsd_avg_1_40 = np.mean(lpsd[freq_mask])
                    # 存储数据：显示名称、m值(或None)、LPSD平均值、完整显示名称
                    file_data.append([display_name, m_value, lpsd_avg_1_40, display_name])
                    print(f"{display_name}: {'m='+str(m_value)+'m' if m_value else '无m值'}, 1-40Hz平均LPSD={lpsd_avg_1_40:.6f} g/√Hz")
                else:
                    print(f"{display_name}: 频率范围不足1-40Hz")
                    continue

                # 找峰值
                height_threshold = np.max(lpsd) * 0.1
                peaks, _ = find_peaks(lpsd, height=height_threshold)

                for peak in peaks:
                    peak_freq = freqs[peak]
                    peak_value = lpsd[peak]
                    peak_data.append([peak_freq, peak_value])

                # 绘制频谱图
                plt.figure(fig1.number)
                # 使用display_name作为图例标签
                legend_label = f"{display_name}"
                    
                plt.loglog(freqs, lpsd,
                          label=legend_label, 
                          color=colors[idx % len(colors)], 
                          linewidth=1.2)

                print(f"处理完成: {display_name}, 采样率: {fs} Hz, 数据时间长度: {len(acc_data) / fs:.2f} s")

        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- 输出峰值数据 ---
    if peak_data:
        peak_df = pd.DataFrame(peak_data, columns=["Frequency (Hz)", "Peak Value"])
        peak_df_sorted = peak_df.sort_values(by="Peak Value", ascending=False).reset_index(drop=True)
        print("\nTop 20 Peak Data Recorded (sorted by peak value):")
        print(peak_df_sorted.head(20))

    # --- 绘制第二张图：平均值与距离/文件名的关系 ---
    if file_data:
        # 提取数据
        display_names = [item[0] for item in file_data]
        m_values = [item[1] for item in file_data]  # 可能为None
        lpsd_avg_values = [item[2] for item in file_data]
        full_labels = [item[3] for item in file_data]
        
        # 让用户选择基准文件
        print("\n" + "="*50)
        print("可用的文件列表：")
        for i, name in enumerate(display_names):
            m_info = f" (距离{m_values[i]}m)" if m_values[i] else ""
            print(f"{i+1}. {name}{m_info}")
        print("="*50)
        
        ref_index = select_reference_file(display_names)
        ref_name = display_names[ref_index]
        ref_value = lpsd_avg_values[ref_index]
        
        print(f"\n以 '{ref_name}' 为基准 (值={ref_value:.6f} g/√Hz)，计算相对比值：")
        
        # 计算相对比值
        relative_ratios = [val / ref_value for val in lpsd_avg_values]
        
        # 创建双y轴图
        fig2, ax1 = plt.subplots(figsize=(12, 6))
        
        # 检查是否所有文件都有m值
        all_have_m = all(m is not None for m in m_values)
        
        if all_have_m:
            # 所有文件都有m值：使用m值作为横坐标
            x_values = m_values
            x_label = "Distance (m)"
            
            # 按m值排序
            sorted_indices = np.argsort(x_values)
            x_values_sorted = [x_values[i] for i in sorted_indices]
            lpsd_sorted = [lpsd_avg_values[i] for i in sorted_indices]
            rel_sorted = [relative_ratios[i] for i in sorted_indices]
            labels_sorted = [display_names[i] for i in sorted_indices]
        else:
            # 有文件缺少m值：使用文件名作为横坐标（序号）
            x_values = list(range(len(display_names)))
            x_label = "File Number"
            
            # 按原始顺序
            x_values_sorted = x_values
            lpsd_sorted = lpsd_avg_values
            rel_sorted = relative_ratios
            labels_sorted = display_names
            
            # 设置x轴刻度标签为文件名
            plt.xticks(x_values, display_names, rotation=45, ha='right')
        
        # 左y轴：原始LPSD平均值
        color1 = '#1f77b4'
        ax1.set_xlabel(x_label, fontsize=14, fontname="Arial Unicode MS")
        ax1.set_ylabel(r"Average LPSD (1-40 Hz) ($g/\sqrt{Hz}$)", fontsize=14, fontname="Arial Unicode MS", color=color1)
        
        line1 = ax1.plot(x_values_sorted, lpsd_sorted, 'o-', color=color1, linewidth=2, markersize=8, 
                         markerfacecolor='white', markeredgewidth=2, label='LPSD Average')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, alpha=0.3)
        
        # 右y轴：相对比值
        color2 = '#d62728'
        ax2 = ax1.twinx()
        ax2.set_ylabel(f"Relative Ratio ('{ref_name}' = 1)", fontsize=14, fontname="Arial Unicode MS", color=color2)
        
        line2 = ax2.plot(x_values_sorted, rel_sorted, 's--', color=color2, linewidth=1.5, markersize=6, 
                         markerfacecolor='white', markeredgewidth=1.5, label='Relative Ratio')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # 添加水平参考线（y=1）
        ax2.axhline(y=1, color=color2, linestyle=':', linewidth=1, alpha=0.5)
        
        # 标记基准点的位置
        ref_x = x_values_sorted[list(lpsd_sorted).index(ref_value)] if all_have_m else ref_index
        ax2.plot(ref_x, 1, 'o', color=color2, markersize=10, 
                 markerfacecolor='yellow', markeredgewidth=2, markeredgecolor=color2)
        
        # 添加标题
        plt.title("Average Vibration Level vs. File/Distance（1-40Hz）", fontsize=18, fontname="Arial Unicode MS", fontweight='bold')
        
        # 为每个点添加标注
        for i, (x, y, name, m) in enumerate(zip(x_values_sorted, lpsd_sorted, labels_sorted, 
                                                [m_values[i] for i in (sorted_indices if all_have_m else range(len(m_values)))])):
            label_text = name
            if m:
                label_text += f" ({m}m)"
            ax1.annotate(label_text, (x, y), textcoords="offset points", xytext=(0,10), 
                         ha='center', fontsize=8, rotation=0, 
                         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
        
        # 合并图例
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper right', fontsize=10)
        
        # 打印相对比值信息
        print(f"\n各文件的相对比值（以 '{ref_name}' = 1 为基准）：")
        for i, (name, m, rel) in enumerate(zip(display_names, m_values, relative_ratios)):
            m_str = f" (距离{m}m)" if m else ""
            print(f"{name}{m_str}: {rel:.3f}")
            
        plt.tight_layout()
    else:
        print("没有有效的文件数据用于绘制关系图")

    # --- 修饰第一个图 ---
    plt.figure(fig1.number)
    if plt.gca().has_data():
        plt.xlabel("Frequency (Hz)", fontsize=14, fontname="Arial Unicode MS")
        plt.ylabel(r"LPSD ($g/\sqrt{Hz}$)", fontsize=14, fontname="Arial Unicode MS")
        plt.title("Vibration Acceleration Spectrum", fontsize=18, fontname="Arial Unicode MS", fontweight='bold')

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