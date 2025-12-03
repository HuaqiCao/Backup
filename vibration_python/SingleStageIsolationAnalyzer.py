"""
本程序用于处理加速度传感器采集的时域信号，主要功能包括：
1) 读取 CSV（时间、电压）并转换为加速度；
2) 使用 Welch 方法计算加速度 PSD 与位移 PSD（LPSD）；
3) 基于单自由度模型计算弹簧刚度 k、阻尼 c、固有频率 fn；
4) 计算不同频段的加速度与位移 RMS；
5) 绘制输入/输出的 LPSD、PSD 与 FFT 图；
6) 保存 RMS 结果为 Excel 文件（与 CSV 同目录）。
"""

import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from scipy.signal import welch, detrend
from math import pi, sqrt
from numpy import trapezoid
import os

# ================= 常量设置 =================
SENS_V_PER_G = 1.026       # 传感器灵敏度 (V/g)
GAIN = 100.0               # 放大倍数
G0 = 9.80665               # 重力加速度 (m/s²)

DEFAULT_G = 41e9           # 磷铜剪切模量
DEFAULT_ZETA = 0.001       # 阻尼比
FMIN_VALID = 1.0           # PSD 有效下限频率

# RMS 频段
BANDS = np.array([[1, 40], [40, 1000], [1, 1000]])
BAND_LABELS = ["[1–40) Hz", "(40–1000] Hz", "[1–1000] Hz"]


# ============= 单自由度加速度传递率 =============
def transmissibility(f, fn, zeta):
    """计算单自由度系统的加速度传递率 TR_a"""
    r = f / fn
    num = np.sqrt(1 + (2 * zeta * r)**2)
    den = np.sqrt((1 - r**2)**2 + (2 * zeta * r)**2)
    den[den == 0] = 1e-16
    return num / den


# ============= 打印 RMS 结果 =============
def print_rms_console_excel_style(rms_rows, filename):
    """以表格形式在终端打印 RMS 结果"""
    print("\n================ RMS Summary ================\n")
    print(f"File: {filename}\n")

    print(f"{'Acc RMS (µg) 1–40':>20} | "
          f"{'Acc RMS (µg) 40–1000':>22} | "
          f"{'Acc RMS (µg) 1–1000':>22} | "
          f"{'Disp RMS (nm) 1–40':>20} | "
          f"{'Disp RMS (nm) 40–1000':>23} | "
          f"{'Disp RMS (nm) 1–1000':>23}")
    print("-" * 135)

    print(f"{rms_rows[0]['acc_ug']:>20.2f} | "
          f"{rms_rows[1]['acc_ug']:>22.2f} | "
          f"{rms_rows[2]['acc_ug']:>22.2f} | "
          f"{rms_rows[0]['disp_nm']:>20.2f} | "
          f"{rms_rows[1]['disp_nm']:>23.2f} | "
          f"{rms_rows[2]['disp_nm']:>23.2f}")

    print("\n============================================================\n")


# ================= 主分析函数 =================
def run_analysis(params):
    """执行全部分析流程：读取数据、PSD、RMS、绘图"""

    # -------- 读 CSV 数据（跳 4 行表头）--------
    df = pd.read_csv(params["csv_path"], skiprows=4, header=None)
    time = df[0].values
    volt = df[1].values

    dt = np.median(np.diff(time))
    fs = 1 / dt
    N = len(time)
    print(f"\n采样率 fs = {fs:.3f} Hz, N = {N}")

    # -------- 电压 → 加速度 --------
    a_g = volt / (GAIN * SENS_V_PER_G)
    a_ms2 = a_g * G0
    a_ms2 -= np.mean(a_ms2)     # 去直流

    # -------- 计算弹簧参数 --------
    d = float(params["d_mm"]) * 1e-3
    Dout = float(params["Dout_mm"]) * 1e-3
    Din = float(params["Din_mm"]) * 1e-3
    N_turns = float(params["N_turns"])
    m = float(params["m_kg"])

    D = (Dout + Din) / 2
    k = DEFAULT_G * d**4 / (8 * D**3 * N_turns)   # 弹簧刚度
    fn = (1/(2*pi)) * sqrt(k/m)                   # 固有频率
    zeta = DEFAULT_ZETA
    c = 2 * zeta * sqrt(k * m)                    # 阻尼系数

    print("\n===== 单自由度系统参数 =====")
    print(f"k   = {k:.6f} N/m")
    print(f"c   = {c:.6f} N·s/m")
    print(f"fn  = {fn:.3f} Hz")
    print("============================\n")

    # -------- Welch PSD 计算 --------
    seglen = int(min(round(fs * 10), N))
    window = np.hamming(seglen)
    overlap = seglen // 2

    f, Sa = welch(
        a_ms2, fs=fs, window=window,
        nperseg=seglen, noverlap=overlap,
        nfft=seglen, scaling="density"
    )

    pos = f >= FMIN_VALID

    # -------- 加速度 PSD → 位移 PSD --------
    w = 2 * pi * f
    Sd = np.zeros_like(Sa)
    valid = pos & (w > 0)
    Sd[valid] = Sa[valid] / (w[valid]**4)

    LPSD_disp = np.zeros_like(Sd)
    LPSD_disp[valid] = np.sqrt(Sd[valid]) * 1e9  # m→nm

    # -------- 输出 PSD（乘以传递率）--------
    TR = transmissibility(f, fn, zeta)
    Sa_out = Sa * TR**2
    Sd_out = Sd * TR**2

    LPSD_disp_out = np.zeros_like(Sd_out)
    LPSD_disp_out[valid] = np.sqrt(Sd_out[valid]) * 1e9

    # -------- 输入/输出 FFT --------
    a_ms2_dt = detrend(a_ms2)
    A_fft = np.fft.rfft(a_ms2_dt)
    f_fft = np.fft.rfftfreq(N, dt)
    Amp_in = np.abs(A_fft) / N

    TR_fft = transmissibility(f_fft, fn, zeta)
    Amp_out = Amp_in * TR_fft

    # -------- RMS 计算 --------
    rms_rows = []
    for (f1, f2), label in zip(BANDS, BAND_LABELS):
        if label.startswith("[1–40"):
            idx = (f >= f1) & (f < f2)
        elif label.startswith("(40"):
            idx = (f > f1) & (f <= f2)
        else:
            idx = (f >= f1) & (f <= f2)

        idx &= pos
        acc_rms = np.sqrt(trapezoid(Sa[idx], f[idx]))
        disp_rms = np.sqrt(trapezoid(Sd[idx], f[idx]))

        rms_rows.append({
            "band": label,
            "acc_ug": acc_rms / G0 * 1e6,
            "disp_nm": disp_rms * 1e9
        })

    # 打印 RMS 到终端
    filename_only = os.path.basename(params["csv_path"])
    print_rms_console_excel_style(rms_rows, filename_only)

    # -------- 保存 RMS 为 Excel --------
    rms_excel = pd.DataFrame([{
        "File": filename_only,
        "Acc RMS (µg) 1–40": rms_rows[0]["acc_ug"],
        "Acc RMS (µg) 40–1000": rms_rows[1]["acc_ug"],
        "Acc RMS (µg) 1–1000": rms_rows[2]["acc_ug"],
        "Disp RMS (nm) 1–40": rms_rows[0]["disp_nm"],
        "Disp RMS (nm) 40–1000": rms_rows[1]["disp_nm"],
        "Disp RMS (nm) 1–1000": rms_rows[2]["disp_nm"],
    }])

    csv_dir = os.path.dirname(params["csv_path"])
    save_path = os.path.join(csv_dir, os.path.splitext(filename_only)[0] + "_RMS.xlsx")
    rms_excel.to_excel(save_path, index=False)
    print(f"RMS 结果已保存至：\n{save_path}\n")

    # ======================= 绘图 =======================
    import matplotlib as mpl
    mpl.rcParams['font.family'] = 'Times New Roman'    
    mpl.rcParams['mathtext.fontset'] = 'cm'          
    mpl.rcParams['axes.unicode_minus'] = False        

    # ---- LPSD（输入/输出）----
    plt.figure()
    plt.loglog(f[pos], LPSD_disp[pos], label="Input")
    plt.loglog(f[pos], LPSD_disp_out[pos], label="Output")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel(r"LPSD [nm/$\sqrt{\mathrm{Hz}}$]")
    plt.title("Displacement LPSD (Input vs Output)")
    plt.grid(True, which="both")
    plt.legend()

    # ---- FFT（输入/输出）----
    plt.figure()
    plt.plot(f_fft, Amp_in, label="Input FFT")
    plt.plot(f_fft, Amp_out, label="Output FFT")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.title("FFT Amplitude (Input vs Output)")
    plt.grid(True)
    plt.legend()
    plt.xlim(0, 100)

    ABS_Y_LIMIT = 0.001
    y_max = max(np.max(Amp_in), np.max(Amp_out))
    plt.ylim(0, min(y_max * 1.1, ABS_Y_LIMIT) if y_max > 0 else ABS_Y_LIMIT)

    # ---- PSD（输入/输出）----
    plt.figure()
    plt.loglog(f[pos], Sa[pos], label="Input PSD")
    plt.loglog(f[pos], Sa_out[pos], label="Output PSD")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel(r"PSD [$(\mathrm{m/s^2})^2$/Hz]")
    plt.title("Acceleration PSD (Input vs Output)")
    plt.grid(True, which="both")
    plt.legend()

    # ----时域（输入/输出) ----
    A_fft = np.fft.rfft(a_ms2_dt)
    A_out_fft = A_fft * TR_fft
    a_out_ms2 = np.fft.irfft(A_out_fft, n=N)
    t_show = time[:1000]       
    a_in_show = a_ms2_dt[:1000]
    a_out_show = a_out_ms2[:1000]

    plt.figure()
    plt.plot(t_show, a_in_show, label="Input (before isolation)")
    plt.plot(t_show, a_out_show, label="Output (after isolation)")
    plt.xlabel("Time (s)")
    plt.ylabel("Acceleration (m/s²)")
    plt.title("Time-Domain Signal (Before vs After Isolation)")
    plt.legend()
    plt.grid(True)

    plt.show()

# ================= GUI 界面 =================
def main():
    """图形界面：选择 CSV 并输入弹簧参数"""
    root = tk.Tk()
    root.withdraw()

    csv_path = filedialog.askopenfilename(
        title="选择 CSV 文件",
        filetypes=[("CSV files", "*.csv")]
    )
    if not csv_path:
        print("未选择文件，程序退出。")
        return

    win = tk.Tk()
    win.title("输入弹簧参数与质量")

    labels = ["线径 d (mm)", "外径 Dout (mm)", "内径 Din (mm)", "圈数 N", "质量 m (kg)"]
    defaults = ["1", "11", "9", "100", "1"]

    entries = {}
    for i, (lab, defval) in enumerate(zip(labels, defaults)):
        tk.Label(win, text=lab).grid(row=i, column=0)
        ent = tk.Entry(win)
        ent.insert(0, defval)
        ent.grid(row=i, column=1)
        entries[lab] = ent

    def submit():
        params = {
            "csv_path": csv_path,
            "d_mm": entries["线径 d (mm)"].get(),
            "Dout_mm": entries["外径 Dout (mm)"].get(),
            "Din_mm": entries["内径 Din (mm)"].get(),
            "N_turns": entries["圈数 N"].get(),
            "m_kg": entries["质量 m (kg)"].get(),
        }
        win.destroy()
        run_analysis(params)

    tk.Button(win, text="开始计算", command=submit).grid(
        row=len(labels), column=0, columnspan=2
    )
    win.mainloop()


if __name__ == "__main__":
    main()
