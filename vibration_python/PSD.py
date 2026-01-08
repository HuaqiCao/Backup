import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window, detrend
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import re
from nptdms import TdmsFile

# ===================== 环境配置：罗马字体与负号修复 =====================
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False  # 关键：修复负号显示为方框的问题

def process_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="选择数据文件 (可多选 CSV 或 TDMS)",
        filetypes=[("数据文件", "*.csv *.tdms")]
    )

    if not file_paths:
        return

    # 强对比色系
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    plt.figure(figsize=(10, 6))

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            # --- 1. 鲁棒的数据读取 ---
            if ext == '.csv':
                raw_data = np.loadtxt(file_path, delimiter=',', skiprows=4, encoding='latin1')
                data = raw_data[:, 1] if raw_data.shape[1] > 1 else raw_data.flatten()
            elif ext == '.tdms':
                tdms = TdmsFile.read(file_path)
                data = None
                for group in tdms.groups():
                    if len(group.channels()) > 0:
                        data = group.channels()[0].data
                        break
                if data is None: 
                    print(f"{filename}: 未找到有效数据")
                    continue

            # --- 2. 参数设置 ---
            sen = 1.026  # 灵敏度
            g = 9.81
            wint = 5     # 时间窗长度(s)
            
            # 增益逻辑
            if "100gain" in filename.lower():
                gain = 100.122
            elif "10gain" in filename.lower():
                gain = 10.003
            else:
                gain = 100.0  # 默认增益
            
            # 采样率提取
            match = re.search(r"(\d+)fs", filename, re.IGNORECASE)
            fs = int(match.group(1)) if match else 10000

            # --- 3. 信号预处理（关键：去除直流）---
            # 物理量转换
            acc_data = data / (gain * sen) 
            
            # 方法1：直接减去均值（去除直流）
            acc_data = acc_data - np.mean(acc_data)
            
            # 方法2：使用detrend（去除直流和线性趋势）
            # acc_data = detrend(acc_data, type='constant')  # 仅去除直流
            # acc_data = detrend(acc_data, type='linear')    # 去除线性趋势
            
            # 检查数据长度
            if len(acc_data) < fs:  # 如果数据长度小于1秒
                print(f"{filename}: 数据长度过短 ({len(acc_data)} points)")
                continue

            # --- 4. 信号处理 (计算 LPSD) ---
            n = int(wint * fs)
            if n > len(acc_data): 
                n = len(acc_data) // 2  # 如果数据太短，减小窗口
                if n < fs:  # 如果窗口小于1秒，使用1秒窗口
                    n = fs
            
            nfft = 2 ** int(np.ceil(np.log2(n)))
            win = get_window("hann", n)
            win_power = np.sum(win**2)  # 窗函数功率
            
            # 分帧平均（改进版）
            step = max(n // 2, 1)  # 确保步长至少为1
            num_frames = max((len(acc_data) - n) // step + 1, 1)
            
            psd_sum = np.zeros(nfft // 2 + 1)
            valid_frames = 0
            
            for i in range(num_frames):
                start = i * step
                end = start + n
                if end > len(acc_data):
                    break
                
                seg = acc_data[start:end].copy()
                
                # 可选：对每个分段单独去除直流（更严格的DC去除）
                seg = seg - np.mean(seg)
                
                # 应用窗函数
                seg_windowed = seg * win
                
                # FFT计算
                sig_fft = fft(seg_windowed, nfft)
                
                # PSD计算 (单位: g^2/Hz)
                psd_frame = (np.abs(sig_fft[:nfft // 2 + 1])**2) / (fs * win_power)
                psd_frame[1:-1] *= 2  # 单边谱能量修正（除0Hz和Nyquist频率）
                
                psd_sum += psd_frame
                valid_frames += 1
            
            if valid_frames == 0:
                print(f"{filename}: 无有效数据帧")
                continue
                
            psd_avg = psd_sum / valid_frames
            freqs = np.linspace(0, fs / 2, nfft // 2 + 1)
            
            # 可选：平滑处理（移动平均）
            # smooth_psd = np.convolve(np.sqrt(psd_avg), np.ones(5)/5, mode='same')

            # --- 5. 绘图 (全罗马字体) ---
            lpsd = np.sqrt(psd_avg)  # LPSD = sqrt(PSD), 单位: g/√Hz
            
            plt.loglog(freqs, lpsd,  # 包含0Hz
                label=os.path.splitext(filename)[0], 
                color=colors[idx % len(colors)], 
                linewidth=1.2)
            
            print(f"处理完成: {filename}, 采样率: {fs} Hz, 帧数: {valid_frames}, 增益: {gain}")

        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- 6. 图表修饰 ---
    if plt.gca().has_data():  # 检查是否有数据被绘制
        plt.xlabel("Frequency (Hz)", fontsize=12, fontname="Times New Roman")
        plt.ylabel(r"LPSD ($g/\sqrt{Hz}$)", fontsize=12, fontname="Times New Roman")
        plt.title("Vibration Acceleration Spectrum Comparison", fontsize=14, fontname="Times New Roman", fontweight='bold')
        
        plt.grid(True, which="both", ls="-", alpha=0.3)
        plt.grid(True, which="minor", ls=":", alpha=0.1)
        
        # 设置坐标轴范围（可选）
        plt.xlim(0.1, None)  # 从1Hz开始，避开直流区域
        
        plt.legend(prop={'family': 'Times New Roman', 'size': 9}, framealpha=0.8)
        plt.tight_layout()
        plt.show()
    else:
        print("没有有效数据被绘制")

if __name__ == "__main__":
    process_files()