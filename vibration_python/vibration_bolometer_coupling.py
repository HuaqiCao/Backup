import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import butter, filtfilt
import tkinter as tk
from tkinter import filedialog, simpledialog

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['figure.dpi'] = 120   # 图像分辨率（DPI）

# ===========================================================
# 读取 CSV：前 4 行表头，第 1 列时间(s)，第 2 列电压/ADC
# ===========================================================
def load_csv_with_time():
    file_path = filedialog.askopenfilename(
        title="选择 CSV 文件",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    if not file_path:
        raise ValueError("未选择文件")

    df = pd.read_csv(file_path, skiprows=4, header=None)
    time = df.iloc[:, 0].values.astype(float)
    value = df.iloc[:, 1].values.astype(float)

    return time, value, file_path


# ===========================================================
# 简单双边重采样到统一 Fs
# ===========================================================
def resample_to_common_fs(t1, x1, t2, x2):
    fs1 = 1.0 / np.mean(np.diff(t1))
    fs2 = 1.0 / np.mean(np.diff(t2))

    print(f"原始 Fs1 = {fs1:.2f} Hz, Fs2 = {fs2:.2f} Hz")

    fs = min(fs1, fs2)
    print(f"统一重采样 Fs = {fs:.2f} Hz")

    t_min = max(t1.min(), t2.min())
    t_max = min(t1.max(), t2.max())
    duration = t_max - t_min

    # 统一从 0 开始计时
    t_new = np.arange(0, duration, 1.0 / fs)

    x1_new = np.interp(t_new, t1 - t1.min(), x1)
    x2_new = np.interp(t_new, t2 - t2.min(), x2)

    return t_new, x1_new, fs, x2_new, duration


# ===========================================================
# 高频振动提取：高通滤波（用于 microphonic 分量）
# ===========================================================
def highpass(sig, fs, cutoff=5.0, order=4):
    """
    cutoff: 高通截止频率 (Hz)，这里默认 5 Hz
    只保留 >cutoff 的振动成分，用于 PCB→Bolometer 抖动耦合分析
    """
    wn = cutoff / (fs / 2.0)
    b, a = butter(order, wn, btype='highpass')
    return filtfilt(b, a, sig)


# ===========================================================
# 实测 TF（线性系统频响估计）
# ===========================================================
def compute_transfer_function(x, y, fs, nperseg=8192):
    # x: 输入 (MXC/PCB)，y: 输出 (bolometer microphonic)
    f, Pxy = signal.csd(y, x, fs=fs, nperseg=nperseg)
    f, Pxx = signal.welch(x, fs=fs, nperseg=nperseg)
    H = Pxy / Pxx
    return f, H, Pxx


# ===========================================================
# 理论 SDOF 传递函数（基座加速度 → 质量绝对加速度/位移）
# 这里只给出幅值传递函数 T(f)
# ===========================================================
def theoretical_tf(f, m, k, zeta):
    w = 2 * np.pi * f
    w0 = np.sqrt(k / m)     # 自振频率
    num = w0 ** 2
    den = np.sqrt((w0 ** 2 - w ** 2) ** 2 + (2 * zeta * w0 * w) ** 2)
    return num / den        # 幅值传递函数 |H(f)|


# ===========================================================
# 主程序
# ===========================================================
def main():
    root = tk.Tk()
    root.withdraw()

    # ----------- 输入理论参数（隔振器）-----------
    m = float(simpledialog.askstring("参数输入", "请输入质量 m (kg)："))
    k = float(simpledialog.askstring("参数输入", "请输入弹簧刚度 k (N/m)："))
    zeta = float(simpledialog.askstring("参数输入", "请输入阻尼比 zeta (0~1)："))

    # ------------------ 读取 MXC / PCB ------------------
    print("请选择 MXC (PCB 加速度计) 的 CSV：")
    t1, x1, path1 = load_csv_with_time()

    # *** MXC 去增益 100 ***
    x1 = x1 / 100.0
    print("已对 MXC(PCB) 数据执行：除以 100（去增益）")

    # ------------------ 读取 Bolometer 原始 ADC ------------------
    print("请选择 Bolometer 原始 ADC 的 CSV：")
    t2, x2, path2 = load_csv_with_time()

    # *** Bolometer 去增益 206 × 50 ***
    x2 = x2 / (206.0 * 50.0)
    print("已对 Bolometer 数据执行：除以 10300（206×50 去增益）")

    # ------------------ 重采样 ------------------
    t, x1r, fs, x2r, duration = resample_to_common_fs(t1, x1, t2, x2)

    # ------------------ 高频 microphonic 提取 ------------------
    # 为了看 PCB→Bolometer 抖动耦合，去掉低频能量脉冲，只保留 >5 Hz 振动
    cutoff_hp = 5.0  # Hz，如需调整，可改这个数
    x1_hp = highpass(x1r, fs, cutoff=cutoff_hp)   # PCB 高频振动
    x2_hp = highpass(x2r, fs, cutoff=cutoff_hp)   # Bolometer 高频 microphonic

    # ========= 命令行输出数据长度 =========
    print("\n================= 数据信息 =================")
    print(f"图像分辨率（DPI）: {plt.rcParams['figure.dpi']}")
    print(f"重采样后采样频率 Fs = {fs:.2f} Hz")
    print(f"使用数据长度：{len(t)} 点")
    print(f"数据总时长：{duration:.3f} 秒")
    print(f"高通截止频率：{cutoff_hp:.2f} Hz (仅保留 microphonic 部分)")
    print("============================================\n")

    # ------------------ 实测 PCB→Bolometer TF ------------------
    f_tf, H_meas, Pxx = compute_transfer_function(x1_hp, x2_hp, fs)

    # ------------------ 理论隔振传递函数（MXC→质量） ------------------
    H_theory = theoretical_tf(f_tf, m, k, zeta)

    # ------------------ PSD 计算 ------------------
    f_psd, Pxx_psd = signal.welch(x1_hp, fs=fs, nperseg=8192)
    f_psd2, Pyy_psd = signal.welch(x2_hp, fs=fs, nperseg=8192)

    # 理论隔振对 PCB 振动的影响：Pyy_theory = Pxx * |H_theory|^2
    H_interp = np.interp(f_psd, f_tf, H_theory)
    Pyy_theory = Pxx_psd * (H_interp ** 2)

    # ===================== 绘图 =====================
    fig, ax = plt.subplots(2, 1, figsize=(8, 9))

    # -------- 图 1：PCB→Bolometer 抖动耦合传递函数 --------
    ax[0].semilogx(f_tf, 20 * np.log10(np.abs(H_meas)), 'b', label="Measured: PCB → Bolometer microphonic")
    ax[0].semilogx(f_tf, 20 * np.log10(H_theory), 'r--', label="Theoretical SDOF (base → mass)")

    ax[0].set_title("Transfer Function Magnitude |H(f)| (dB)")
    ax[0].set_xlabel("Frequency (Hz)")
    ax[0].set_ylabel("Magnitude (dB)")
    ax[0].grid(True, which='both')
    ax[0].legend()

    # -------- 图 2：PSD & 理论隔振效果 --------
    ax[1].loglog(f_psd, np.sqrt(Pxx_psd), label="PCB @ MXC (input, high-pass)")
    ax[1].loglog(f_psd2, np.sqrt(Pyy_psd), label="Bolometer microphonic (measured)")
    ax[1].loglog(f_psd, np.sqrt(Pyy_theory), 'r--', linewidth=1.2,
                 label="Theoretical isolation (SDOF on PCB PSD)")

    ax[1].set_title("PSD (RMS / √Hz)")
    ax[1].set_xlabel("Frequency (Hz)")
    ax[1].set_ylabel("Amplitude")
    ax[1].grid(True, which='both')
    ax[1].legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
