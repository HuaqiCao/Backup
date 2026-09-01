import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import os
import chardet
import re
from scipy import signal

# 针对 Mac 系统的中文字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

def detect_encoding(filepath):
    """自动检测文件编码"""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read(10000)
            result = chardet.detect(raw)
            encoding = result['encoding']
            if encoding and encoding.lower() in ['ascii', 'iso-8859-1']:
                return 'gbk'
            return encoding if encoding else 'gbk'
    except:
        return 'gbk'

def detect_unit(filepath, encoding):
    """增强版：读取前4行标题，智能识别电压单位 (V, mV, μV/uV)"""
    try:
        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
            header_lines = [f.readline().strip().lower() for _ in range(4)]
            header_text = " ".join(header_lines)
            
            if 'μv' in header_text or 'uv' in header_text:
                return 'uV'
            elif 'mv' in header_text or '毫伏' in header_text:
                return 'mV'
            elif 'v' in header_text:
                return 'V'
        return 'mV'
    except:
        return 'mV'

def parse_filename_info(filename):
    """
    【终极完美版】从文件名中精准提取 Gain(增益) 和 Sens(灵敏度)
    完美兼容：100gain, 1gain, 115mv:g, 957mv/g 等所有格式
    """
    name_lower = filename.lower()
    
    # 1. 【严谨提取增益】：严格匹配 "数字+gain" (如 1gain, 100gain)
    # 去掉了 \b 边界符，只要前面是数字，后面紧跟 gain 就能精准提取！
    gain_match = re.search(r'(\d+)\s*gain', name_lower)
    gain = float(gain_match.group(1)) if gain_match else 1.0
    
    # 2. 【终极修复提取灵敏度】：同时兼容 'mv/g' 和 'mv:g' (如 115mv/g 或 115mv:g)
    sens_match = re.search(r'(\d+\.?\d*)\s*(mv|v|uv)\s*[/|:]\s*g', name_lower)
    if sens_match:
        sens_val = float(sens_match.group(1))
        sens_unit = sens_match.group(2)
        # 统一转换为 V/g
        if sens_unit == 'mv':
            sensitivity = sens_val / 1000.0
        elif sens_unit == 'uv':
            sensitivity = sens_val / 1_000_000.0
        else:
            sensitivity = sens_val
    else:
        sensitivity = 1.0  # 如果没找到，默认 1 V/g
        
    return gain, sensitivity

def load_vibration_data(filepath):
    """统一加载 CSV 和 TXT 数据，前4行为标题"""
    encoding = detect_encoding(filepath)
    unit = detect_unit(filepath, encoding)
    gain, sensitivity = parse_filename_info(os.path.basename(filepath))
    
    print(f"  检测到单位: {unit} (文件编码: {encoding})")
    print(f"  【核心参数】提取到增益(Gain): {gain}, 灵敏度(Sens): {sensitivity} V/g")

    try:
        df = pd.read_csv(filepath, skiprows=4, header=None, 
                         encoding=encoding, engine='python', 
                         on_bad_lines='skip', sep=None)
    except Exception:
        delimiter = '\t' if filepath.lower().endswith('.txt') else ','
        df = pd.read_csv(filepath, skiprows=4, header=None, 
                         delimiter=delimiter, encoding=encoding, 
                         engine='python', on_bad_lines='skip')

    # 将 '-' 等无法转换为浮点数的字符替换为 NaN
    df.replace(['-∞', '∞', '-', '--', '---'], np.nan, inplace=True)
    
    t = df.iloc[:, 0].to_numpy(dtype=float)
    v = df.iloc[:, 1].to_numpy(dtype=float)

    # 【核心物理转换】：电压 -> 去增益 -> 去灵敏度(转换为真实物理量)
    if unit == 'mV':
        v = v / 1000.0
    elif unit == 'uV':
        v = v / 1_000_000.0
        
    v = v / gain          # 1. 去除放大器增益
    v = v / sensitivity   # 2. 除以灵敏度，转换为 g (重力加速度)
    v = v - np.nanmean(v) # 3. 去除直流偏置
    
    # 计算采样率和总采样时间
    dt = np.nanmedian(np.diff(t))
    fs = 1.0 / dt if dt > 0 else 1.0
    total_time = t[-1] - t[0] if len(t) > 1 else 0
    
    return t, v, fs, total_time, unit

def compute_psd(signal_data, fs, nperseg=131072, overlap_ratio=0.5):
    """计算功率谱密度 (PSD) 和幅值谱密度 (ASD)"""
    noverlap = int(nperseg * overlap_ratio)
    actual_nperseg = min(nperseg, len(signal_data))
    
    freqs, psd = signal.welch(
        signal_data, fs=fs, window='hann',       
        nperseg=actual_nperseg, noverlap=noverlap, scaling='density'    
    )
    asd = np.sqrt(psd)
    return freqs, psd, asd

def plot_psd_multi(data_list, save_dir=None):
    """核心绘图函数：将多个文件的数据画在同一张图上对比"""
    colors = plt.cm.tab10(np.linspace(0, 1, len(data_list)))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))

    for idx, (name, t, v, fs, freq, asd, total_time) in enumerate(data_list):
        # 1. 绘制时域图 (最多显示前2秒)
        T_SHOW = min(2.0, t[-1])
        mask = t <= T_SHOW
        ax1.plot(t[mask], v[mask], color=colors[idx], linewidth=1.2, alpha=0.8, label=name)

        # 2. 绘制频域图 (ASD)
        f_min = max(0.05, freq[0])
        f_max = min(fs/2, 500)
        mask_f = (freq >= f_min) & (freq <= f_max)
        ax2.loglog(freq[mask_f], asd[mask_f], color=colors[idx], linewidth=1.5, alpha=0.9, label=name)

    # 时域图设置
    ax1.set_xlabel('时间 Time (s)', fontsize=12)
    ax1.set_ylabel('加速度 Acceleration (g)', fontsize=12)
    ax1.set_xlim(0, 1)
    ax1.set_title('时域信号对比 (Time Domain Signals)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=10, framealpha=0.9)

    # 频域图设置
    ax2.set_xlabel('频率 Frequency (Hz)', fontsize=12)
    ax2.set_xlim(0.1, 100)
    ax2.set_ylabel(r'幅值谱密度 ASD $[g/\sqrt{Hz}]$', fontsize=12)
    ax2.set_title('幅值谱密度对比 (Amplitude Spectral Density)', fontsize=14, fontweight='bold')
    ax2.grid(True, which='both', ls='--', alpha=0.45)
    ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)

    plt.tight_layout()

    if save_dir:
        for filepath, (name, _, _, _, _, _, _) in zip(save_dir, data_list):
            save_path = os.path.join(os.path.dirname(filepath), f"{name}_psd.png")
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
    else:
        plt.show()
    return fig

def select_files():
    """弹出文件选择框"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filepaths = filedialog.askopenfilenames(
        title="选择需要对比的数据文件 (可多选 CSV/TXT)",
        filetypes=[("文本/CSV文件", "*.txt *.csv"), ("所有文件", "*.*")],
        initialdir=os.path.expanduser("~/Desktop")
    )
    root.destroy()
    return list(filepaths)

def main():
    print("请选择需要对比的数据文件（可多选）...")
    filepaths = select_files()

    if not filepaths:
        print("未选择文件，程序退出。")
        return

    print(f"\n已选择 {len(filepaths)} 个文件")
    print("="*80)

    # 第一步：加载所有文件并获取各自的采样率
    raw_data_list = []
    fs_list = []
    for filepath in filepaths:
        try:
            name = os.path.basename(filepath).replace('.txt', '').replace('.csv', '')
            print(f"\n  正在加载: {name}...")
            t, v, fs, total_time, unit = load_vibration_data(filepath)
            
            valid_mask = ~(np.isnan(t) | np.isnan(v))
            t, v = t[valid_mask], v[valid_mask]
            
            raw_data_list.append((name, t, v, fs, total_time, filepath))
            fs_list.append(fs)
        except Exception as e:
            print(f"  加载失败 {filepath}: {e}")

    if not raw_data_list:
        print("没有成功加载任何文件。")
        return

    # 第二步：统一采样率 (取所有文件中的最小采样率)
    target_fs = min(fs_list)
    if len(set(fs_list)) > 1:
        print(f"\n检测到不同采样率，统一重采样至最低采样率: {target_fs:.2f} Hz")
    else:
        print(f"\n所有文件采样率一致: {target_fs:.2f} Hz")

    # 第三步：重采样并计算 PSD，输出详细报告
    data_list = []
    print("\n" + "="*80)
    print(f"{'文件名':<35} {'采样率(Hz)':<12} {'采样时间(s)':<12} {'RMS(g)':<12} {'Peak(g/√Hz)':<15} {'Peak频率(Hz)'}")
    print("-"*80)
    
    for (name, t, v, fs, total_time, filepath) in raw_data_list:
        if fs != target_fs:
            num_samples = int(len(v) * target_fs / fs)
            v_resampled = signal.resample(v, num_samples)
            t_resampled = np.arange(num_samples) / target_fs
        else:
            v_resampled = v
            t_resampled = t

        freq, psd, asd = compute_psd(v_resampled, target_fs, nperseg=131072, overlap_ratio=0.5)
        data_list.append((name, t_resampled, v_resampled, target_fs, freq, asd, total_time))

        # 计算 RMS 和 Peak
        df = freq[1] - freq[0] if len(freq) > 1 else 1.0
        rms = np.sqrt(np.sum(asd**2 * df))
        peak_idx = np.argmax(asd[1:]) + 1 if len(asd) > 1 else 0
        peak_val = asd[peak_idx]
        peak_freq = freq[peak_idx]
        
        # 格式化输出
        short_name = name[:32] + '..' if len(name) > 34 else name
        print(f"{short_name:<35} {target_fs:<12.2f} {total_time:<12.2f} {rms:<12.6f} {peak_val:<15.6f} {peak_freq:.2f}")

    print("="*80)

    # 第四步：将多个文件的数据画在同一张图上进行对比
    plot_psd_multi(data_list, save_dir=None)
    print("\n对比绘图完成!")

if __name__ == '__main__':
    main()