import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import get_window, detrend
from scipy.fft import fft
from tkinter import Tk, filedialog
import os
import re
from nptdms import TdmsFile
import pandas as pd

# ===================== 环境配置：罗马字体与负号修复 =====================
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

def process_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="选择数据文件 (可多选 CSV 或 TDMS)",
        filetypes=[("数据文件", "*.csv *.tdms")]
    )

    if not file_paths:
        return

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    plt.figure(figsize=(10, 6))

    for idx, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        try:
            # --- 鲁棒的数据读取 ---
            if ext == '.csv':
                df = pd.read_csv(file_path, encoding='latin1')
                numeric_cols = df.select_dtypes(include=[np.number]).columns

                if len(numeric_cols) == 0:
                    print(f"{filename}: 未找到数值列")
                    continue
                elif len(numeric_cols) >= 2:
                    data = df[numeric_cols[1]].values
                else:
                    data = df[numeric_cols[0]].values

                # 删除 NaN 和 Inf 值
                data = data[~np.isnan(data)]
                data = data[~np.isinf(data)]
                
                if len(data) == 0:
                    print(f"{filename}: 数值数据为空")
                    continue
                
                # 估算采样率（假设数据均匀采样）
                if 'time' in df.columns:
                    time_data = df['time'].values
                    time_interval = np.mean(np.diff(time_data))  # 获取平均时间间隔
                    fs = 1 / time_interval  # 计算采样率
                else:
                    time_span = len(data) / 1000.0  # 假设数据时间跨度为秒数（根据需要调整）
                    fs = len(data) / time_span  # 估算采样率

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
            num_samples_to_remove = int(30 * fs)  # 30秒的样本数
            if len(data) > 2 * num_samples_to_remove:
                data = data[num_samples_to_remove:-num_samples_to_remove]  # 去掉前后30秒数据
            else:
                print(f"{filename}: 数据长度不足以去除30秒")
                continue

            # --- 4. 信号预处理 ---
            acc_data = data / (gain * sen) 
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