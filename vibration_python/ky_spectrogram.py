import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import pywt
import pandas as pd

def read_tdms_file(file_path):
    """
    读取TDMS文件，若失败则返回模拟数据
    """
    try:
        from nptdms import TdmsFile
        tdms_file = TdmsFile.read(file_path)
        group = tdms_file.groups()[1]
        channel = group.channels()[0]
        data = channel[:]
        time = channel.time_track()
        print(f"Using nptdms: Loaded data shape: {data.shape}, {group.name}")
        return time, data
    except Exception as e:
        print(f"Error reading TDMS file: {e}")
        # 备用模拟数据
        t = np.linspace(0, 3600, 2000*60)  # 模拟1小时
        data = np.sin(2*np.pi*1*t) + 0.5*np.sin(2*np.pi*10*t) + 0.1*np.random.randn(len(t))
        return t, data

def plot_spectrogram(t, signal_data, sampling_rate, target_fs=200, freq_limit=100):
    """
    对长时间信号进行降采样 + 短时傅里叶变换，并可视化时频图
    """
    print("\n=== Spectrogram Analysis ===")

    # ===== 降采样 =====
    factor = int(sampling_rate / target_fs)
    if factor > 1:
        data_ds = signal_data[::factor]
        t_ds = t[::factor]
        print(f"降采样: {sampling_rate:.1f} Hz → {target_fs:.1f} Hz (factor={factor})")
    else:
        data_ds = signal_data
        t_ds = t

    # ===== 计算短时傅里叶变换 =====
    window_length = target_fs * 10   # 每10秒窗口
    overlap = target_fs * 5          # 50%重叠

    f, t_spec, Sxx = signal.spectrogram(
        data_ds,
        fs=target_fs,
        nperseg=window_length,
        noverlap=overlap,
        scaling='density',
        mode='psd'
    )

    print(f"STFT shape: {Sxx.shape}, Frequency range: {f[0]:.2f}–{f[-1]:.2f} Hz")

    # ===== 可视化 =====
    plt.figure(figsize=(12, 6))
    plt.pcolormesh(t_spec/3600, f, 10*np.log10(Sxx), shading='auto', cmap='jet')
    plt.title('Spectrogram (Sliding FFT)')
    plt.ylabel('Frequency [Hz]')
    plt.xlabel('Time [hours]')
    plt.colorbar(label='Power [dB]')
    plt.ylim(0, freq_limit)
    plt.tight_layout()
    plt.savefig('spectrogram_analysis.png')
    plt.show()

    # ===== 打印统计信息 =====
    total_hours = (t_ds[-1] - t_ds[0]) / 3600
    print(f"总时长约: {total_hours:.2f} 小时")
    print(f"平均功率: {np.mean(Sxx):.4e}")

def discrete_wavelet_analysis(signal_data):
    """
    可选：离散小波分解，用于粗略频段能量分析
    """
    coeffs = pywt.wavedec(signal_data, 'db4', level=4)
    fig, axes = plt.subplots(len(coeffs) + 1, 1, figsize=(12, 8))
    axes[0].plot(signal_data)
    axes[0].set_title('Original Signal')
    for i, coeff in enumerate(coeffs):
        axes[i + 1].plot(coeff)
        axes[i + 1].set_title(f'Level {i} Wavelet Coefficients')
    plt.tight_layout()
    plt.savefig('wavelet_levels.png')
    plt.show()
    return coeffs

# ==================== 主程序 ==================== #
if __name__ == "__main__":
    #file_path = "./24h.tdms"  # 替换为你的文件路径
    file_path = "./记录-2025-10-27 035157 441.tdms"  # 替换为你的文件路径
    print(f"Reading TDMS file: {file_path}")
    t, signal_data = read_tdms_file(file_path)

    # 计算采样率
    if len(t) > 1:
        sampling_rate = 1 / (t[1] - t[0])
    else:
        sampling_rate = 2000
    print(f"Data loaded - Length: {len(signal_data)}, Sampling rate: {sampling_rate:.2f} Hz")

    # ===== 滑动窗口 + FFT 可视化 =====
    plot_spectrogram(t, signal_data, sampling_rate, target_fs=200, freq_limit=100)

    # ===== 可选的离散小波分析（短片段分析用） =====
    # dwt_coeffs = discrete_wavelet_analysis(signal_data[:20000])

