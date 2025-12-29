# 没有完全整理好
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import welch, csd
from scipy.optimize import curve_fit
import tkinter as tk
from tkinter import filedialog
import os
from nptdms import TdmsFile

# ===================== 1. 参数输入界面 =====================
def get_params():
    root = tk.Tk()
    root.title("磷青铜系统参数辨识（加速度传递率）")

    # 定义输入字段：标签、内部键名、默认值
    fields = [
        ("负载质量 M (kg)", "m", "2.30"),
        ("线径 d (mm)", "d", "1.5"),
        ("外径 D_out (mm)", "dout", "16.5"),
        ("内径 D_in (mm)", "din", "13.5"),
        ("有效圈数 n", "n", "100.0"),
        ("弹簧数量 (根)", "num", "3"),
        ("传感器灵敏度 (V/um)", "sens", "1.0"),
        ("增益 Gain", "gain", "100.0")
    ]

    res, entries = {}, []
    for i, (lab, key, val) in enumerate(fields):
        tk.Label(root, text=lab).grid(row=i, column=0, sticky="e")
        e = tk.Entry(root); e.insert(0, val)
        e.grid(row=i, column=1)
        entries.append((key, e))

    def go():
        for k, e in entries:
            res[k] = float(e.get())
        root.quit()

    tk.Button(root, text="确认并选文件", command=go).grid(row=len(fields), columnspan=2)
    root.mainloop()

    # 弹出文件选择对话框
    f_in = filedialog.askopenfilename(title="选择基座加速度数据 (Input)")
    f_out = filedialog.askopenfilename(title="选择负载绝对加速度数据 (Output)")
    root.destroy()
    return res, f_in, f_out

# ===================== 2. 数据读取与预处理 =====================
def read_vibe(path, sens, gain):
    ext = os.path.splitext(path)[1].lower()

    # 处理 CSV 格式
    if ext == ".csv":
        for enc in ["utf-8", "gbk"]:
            try:
                df = pd.read_csv(path, skiprows=4, encoding=enc)
                t = df.iloc[:, 0].values
                v = df.iloc[:, 1].values
                fs = 1.0 / np.mean(np.diff(t))  # 计算采样频率
                G0 = 9.80665  # 重力加速度
                a = (v / (sens * gain)) * G0  # 电压转加速度
                a = a - np.mean(a)  # 去直流分量
                return fs, a
            except:
                continue

    # 处理 TDMS 格式
    elif ext == ".tdms":
        tdms = TdmsFile.read(path)
        g = [g for g in tdms.groups() if g.channels()][0]
        ch = g.channels()[0]
        fs = ch.properties.get("wf_samplespersec", 10000)
        G0 = 9.80665
        a = (ch.data / (sens * gain)) * G0
        a = a - np.mean(a)
        return fs, a

    raise RuntimeError("无法识别的数据格式")

# ===================== 3. SDOF 理论模型 =====================


def model(f, f0, eta):
    """单自由度加速度传递率公式"""
    r = f / f0
    return np.sqrt((1 + (2 * eta * r)**2) / ((1 - r**2)**2 + (2 * eta * r)**2))

def model_log(f, f0, eta):
    """用于拟合的对数形式模型"""
    return np.log(model(f, f0, eta))

# ===================== 4. 频谱分析主流程 =====================
p, FIN, FOUT = get_params()
fs, a_in = read_vibe(FIN, p["sens"], p["gain"])
_, a_out = read_vibe(FOUT, p["sens"], p["gain"])

# Welch法配置参数（20秒窗长，75%重叠）
nper = int(fs * 20)
nper = min(nper, len(a_in))
nover = int(0.75 * nper)

# 计算自功率谱(Pxx/Pyy)与互功率谱(Pxy)
f, Pxx = welch(a_in, fs, nperseg=nper, noverlap=nover)
_, Pyy = welch(a_out, fs, nperseg=nper, noverlap=nover)
_, Pxy = csd(a_out, a_in, fs, nperseg=nper, noverlap=nover)

# 计算相干函数与实验传递率（H1估计）
gamma2 = (np.abs(Pxy)**2) / (Pxx * Pyy)
trans = np.abs(Pxy) / Pxx

# ===================== 5. 寻峰与参数拟合 =====================
# 1. 频谱比寻峰
f_pk, Sa_in_pk = welch(a_in, fs, nperseg=nper, noverlap=nover, scaling="density")
_, Sa_out_pk = welch(a_out, fs, nperseg=nper, noverlap=nover, scaling="density")
peak_metric = Sa_out_pk / (Sa_in_pk + 1e-30)

# 2. 在1.5-3.5Hz范围内锁定共振点
fit_search_mask = (f_pk >= 1.5) & (f_pk <= 3.5)
if np.any(fit_search_mask):
    f_peak_refined = f_pk[fit_search_mask][np.argmax(peak_metric[fit_search_mask])]
else:
    f_peak_refined = 2.0
    print("[WARN] 未搜到峰，使用默认2.0Hz")

# 3. 窄带拟合策略：仅取峰值附近±5%频率点，避免噪声干扰阻尼辨识
fit_mask = (f >= f_peak_refined * 0.95) & (f <= f_peak_refined * 1.05)

# 4. 非线性拟合求解 f0 和 eta
p0_refined = [f_peak_refined, 0.001] # 初始猜想值
bounds_refined = ([0.1, 1e-6], [10.0, 0.5]) # 约束范围

try:
    popt, _ = curve_fit(model_log, f[fit_mask], np.log(trans[fit_mask]), 
                        p0=p0_refined, bounds=bounds_refined, maxfev=20000)
    f0_fit, eta_fit = popt
    print(f"[SUCCESS] 拟合成功: f0={f0_fit:.2f}Hz, eta={eta_fit:.6f}")
except Exception as e:
    print(f"[ERROR] 拟合失败: {e}")
    f0_fit, eta_fit = f_peak_refined, 0.005

# ===================== 6. 物理刚度与阻尼计算 =====================
# 理论刚度计算 (基于磷青铜剪切模量 G=42GPa)
D_avg = (p["dout"] + p["din"]) / 2 / 1000
d_m = p["d"] / 1000
G = 42e9 
k_th = (G * d_m**4) / (8 * D_avg**3 * p["n"]) * p["num"]

# 辨识刚度与阻尼系数
k_fit = (2 * np.pi * f0_fit)**2 * p["m"]
c_fit = 2 * eta_fit * np.sqrt(k_fit * p["m"])

# ===================== 7. 绘图：传递率对比 =====================
plt.figure(figsize=(10, 6))
plt.semilogy(f, trans, color="gray", lw=1.2, label="Measured |H(f)|")
plt.semilogy(f, model(f, f0_fit, eta_fit), "r--", lw=2, label="SDOF Fit")

txt = (
    "IDENTIFIED RESULTS\n"
    "----------------------\n"
    f"f0 (Fit)   = {f0_fit:.2f} Hz\n"
    f"eta (Fit)  = {eta_fit:.5f}\n\n"
    f"k_theory   = {k_th:,.1f} N/m\n"
    f"k_fit      = {k_fit:,.1f} N/m\n\n"
    f"c_fit      = {c_fit:.4e} N·s/m"
)
plt.text(0.70, 0.45, txt, transform=plt.gca().transAxes, bbox=dict(facecolor="white", alpha=0.9), fontfamily="monospace")
plt.xlim(0, 100); plt.ylim(1e-3, 1e2); plt.xlabel("Frequency (Hz)"); plt.ylabel("|H(f)|")
plt.title("Acceleration Transmissibility (SDOF Identification)"); plt.grid(True, which="both", alpha=0.3); plt.legend(); plt.tight_layout()

# ===================== 8. LPSD 与 位移 RMS 计算 =====================
# 计算线性功率谱密度 (LPSD)
f_psd, Sa_in = welch(a_in, fs, nperseg=nper, noverlap=nover, scaling="density")
_, Sa_out_meas = welch(a_out, fs, nperseg=nper, noverlap=nover, scaling="density")

# 基于模型的理论输出预测
H_model = model(f_psd, f0_fit, eta_fit)
Sa_out_theory = Sa_in * H_model**2

LPSD_in, LPSD_out_meas, LPSD_out_theory = np.sqrt(Sa_in), np.sqrt(Sa_out_meas), np.sqrt(Sa_out_theory)

# 加速度谱转位移谱 (1/omega^4)
omega = 2 * np.pi * f_psd
Sd_in = np.zeros_like(Sa_in); Sd_out_meas = np.zeros_like(Sa_out_meas); Sd_out_theory = np.zeros_like(Sa_out_theory)
valid = omega > 0
Sd_in[valid] = Sa_in[valid] / omega[valid]**4
Sd_out_meas[valid] = Sa_out_meas[valid] / omega[valid]**4
Sd_out_theory[valid] = Sa_out_theory[valid] / omega[valid]**4

# 频段 RMS 计算函数
BANDS = [(1, 40), (40, 100), (1, 100)]
def calc_rms(f, psd, f1, f2):
    idx = (f >= f1) & (f <= f2)
    return np.sqrt(np.trapz(psd[idx], f[idx])) if np.sum(idx) > 2 else np.nan

rms_rows = []
for f1, f2 in BANDS:
    rms_rows.append((f"{f1}-{f2} Hz", calc_rms(f_psd, Sd_in, f1, f2)*1e9, 
                     calc_rms(f_psd, Sd_out_meas, f1, f2)*1e9, calc_rms(f_psd, Sd_out_theory, f1, f2)*1e9))

# ===================== 9. 绘图：LPSD 与 RMS 统计 =====================
plt.figure(figsize=(10, 6))
plt.loglog(f_psd, LPSD_in, color="gray", lw=1.2, label="Input Acc LPSD")
plt.loglog(f_psd, LPSD_out_meas, color="tab:blue", lw=1.6, label="Output Acc (Measured)")
plt.loglog(f_psd, LPSD_out_theory, "r--", lw=2.0, label="Output Acc (SDOF Theory)")

table_txt = "DISPLACEMENT RMS (nm)\n" + "-"*55 + "\nBand         | In (nm)    | Out(me) (nm) | Out(th) (nm)\n" + "-"*55 + "\n"
for lab, rin, rout_m, rout_t in rms_rows:
    table_txt += f"{lab:<12} | {rin:>10.3g} | {rout_m:>12.3g} | {rout_t:>12.3g}\n"

plt.text(0.40, 0.05, table_txt, transform=plt.gca().transAxes, bbox=dict(facecolor="white", alpha=0.9), fontfamily="monospace")
plt.xlim(1, 100); plt.xlabel("Frequency (Hz)"); plt.ylabel("LPSD [(m/s^2)/sqrt(Hz)]")
plt.title("Acceleration LPSD (Measured vs Theory Prediction)"); plt.grid(True, which="both", alpha=0.3); plt.legend(); plt.tight_layout()
plt.show()