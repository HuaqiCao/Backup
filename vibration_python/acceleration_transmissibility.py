import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import welch, csd
from scipy.optimize import curve_fit
import tkinter as tk
from tkinter import filedialog
import os
from nptdms import TdmsFile

# ===================== 1. 参数输入 =====================
def get_params():
    root = tk.Tk()
    root.title("磷青铜系统参数辨识（加速度传递率）")

    fields = [
        ("负载质量 M (kg)", "m", "2.30"),
        ("线径 d (mm)", "d", "1.5"),
        ("外径 D_out (mm)", "dout", "16.5"),
        ("内径 D_in (mm)", "din", "13.5"),
        ("有效圈数 n", "n", "100.0"),
        ("弹簧数量 (根)", "num", "3"),
        ("传感器灵敏度 (V/um)", "sens", "1.026"),
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

    tk.Button(root, text="确认并选文件", command=go)\
        .grid(row=len(fields), columnspan=2)
    root.mainloop()

    f_in = filedialog.askopenfilename(title="基座加速度 (Input)")
    f_out = filedialog.askopenfilename(title="负载绝对加速度 (Output)")
    root.destroy()
    return res, f_in, f_out


# ===================== 2. 数据读取 =====================
def read_vibe(path, sens, gain):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        for enc in ["utf-8", "gbk"]:
            try:
                df = pd.read_csv(path, skiprows=4, encoding=enc)
                t = df.iloc[:, 0].values
                v = df.iloc[:, 1].values
                fs = 1.0 / np.mean(np.diff(t))
                G0 = 9.80665  # m/s^2
                a = (v / (sens * gain)) * G0   
                a = a - np.mean(a)           
                return fs, a
            except:
                continue

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


# ===================== 3. 主流程 =====================
p, FIN, FOUT = get_params()
fs, a_in = read_vibe(FIN, p["sens"], p["gain"])
_,  a_out = read_vibe(FOUT, p["sens"], p["gain"])

# Welch / CSD 参数
nper = int(fs * 20)           
nper = min(nper, len(a_in))  
nover = int(0.75 * nper)

# PSD / CSD（H1 估计）
f, Pxx = welch(a_in, fs, nperseg=nper, noverlap=nover)
_, Pyy = welch(a_out, fs, nperseg=nper, noverlap=nover)
_, Pxy = csd(a_out, a_in, fs, nperseg=nper, noverlap=nover)

gamma2 = (np.abs(Pxy)**2) / (Pxx * Pyy)

# 加速度传递率 |A_out / A_in|
trans = np.abs(Pxy) / Pxx


# ===================== 4. 理论刚度 =====================
D_avg = (p["dout"] + p["din"]) / 2 / 1000
d_m = p["d"] / 1000
G = 42e9  # Pa

k_th = (G * d_m**4) / (8 * D_avg**3 * p["n"]) * p["num"]
f0_th = (1 / (2 * np.pi)) * np.sqrt(k_th / p["m"])


# ===================== 5. 自动选择拟合频段 =====================
# 初始相干阈值（工程推荐）
gamma_thr = 0.7

while True:
    valid = (f > 0.5) & (f < 10) & (gamma2 > gamma_thr)

    if np.any(valid):
        break

    gamma_thr -= 0.1
    if gamma_thr < 0.2:
        raise RuntimeError(
            "No valid frequency points with sufficient coherence. "
            "Check excitation level or sensor placement."
        )

print(f"[INFO] Using coherence threshold γ² > {gamma_thr:.2f}")

f_peak = f[valid][np.argmax(trans[valid])]

# 窄带拟合（主模态 ±30%）
f_low  = 0.7 * f_peak
f_high = 1.3 * f_peak

mask = (
    (f >= f_low) &
    (f <= f_high) &
    (gamma2 > gamma_thr)
)

# ===================== 6. SDOF 加速度传递率模型 =====================
def model(f, f0, eta):
    r = f / f0
    return np.sqrt(
        (1 + (2 * eta * r)**2) /
        ((1 - r**2)**2 + (2 * eta * r)**2)
    )

def model_log(f, f0, eta):
    return np.log(model(f, f0, eta))

popt, _ = curve_fit(
    model_log,
    f[mask],
    np.log(trans[mask]),
    p0=[f_peak, 0.02],
    bounds=([0.1, 1e-4], [10.0, 0.5]),  # 物理约束
    maxfev=10000
)

f0_fit, eta_fit = popt


# ===================== 7. 物理参数 =====================
k_fit = (2 * np.pi * f0_fit)**2 * p["m"]
c_fit = 2 * eta_fit * np.sqrt(k_fit * p["m"])


# ===================== 8. 绘图 =====================
plt.figure(figsize=(10, 6))

plt.semilogy(f, trans, color="gray", lw=1.2, label="Measured |H(f)|")
plt.semilogy(f, model(f, f0_fit, eta_fit), "r--", lw=2,
             label="SDOF Fit")
# 结果框
txt = (
    "RESULTS\n"
    "----------------------\n"
    f"f0        = {f0_fit:.2f} Hz\n"
    f"eta_fit   = {eta_fit:.5f}\n\n"
    f"k_theory  = {k_th:,.1f} N/m\n"
    f"k_fit     = {k_fit:,.1f} N/m\n\n"
    f"c_fit     = {c_fit:.4e} N·s/m"
)

plt.text(
    0.70, 0.50, txt,
    transform=plt.gca().transAxes,
    bbox=dict(facecolor="white", alpha=0.9),
    fontfamily="monospace"
)

fig = plt.gcf()
fig.text(
    0.5, 0.90,
    r"$\left|H(f)\right|"
    r"=\left|\frac{A_{\mathrm{out}}(f)}{A_{\mathrm{in}}(f)}\right|"
    r"=\sqrt{\frac{1+(2\eta r)^2}{(1-r^2)^2+(2\eta r)^2}},\ "
    r"r=\frac{f}{f_0}$",
    ha="center", va="top",
    fontsize=18, 
    bbox=dict(facecolor="white", alpha=0.9)
)

plt.xlim(0, 100)
plt.ylim(1e-3, 1e2)
plt.xlabel("Frequency (Hz)")
plt.ylabel("|H(f)|")
plt.title("Acceleration Transmissibility")
plt.grid(True, which="both", alpha=0.3)
plt.legend()
plt.tight_layout()


# ===================== 9. 高分辨率 PSD / LPSD（输入+真实输出+理论输出） =====================

# 频率分辨率提高：建议 20s；不足则用全长
nper_hr = int(fs * 20)
nper_hr = min(nper_hr, len(a_in))
nover_hr = int(0.75 * nper_hr)

# 输入 / 输出（真实）PSD
f_psd, Sa_in = welch(a_in, fs, nperseg=nper_hr, noverlap=nover_hr, scaling="density")
_,     Sa_out_meas = welch(a_out, fs, nperseg=nper_hr, noverlap=nover_hr, scaling="density")

# 用“拟合模型”得到理论 FRF（更适合你要的理论对比）
H_model = model(f_psd, f0_fit, eta_fit)          # |Aout/Ain|
Sa_out_theory = Sa_in * H_model**2

# LPSD
LPSD_in = np.sqrt(Sa_in)
LPSD_out_meas = np.sqrt(Sa_out_meas)
LPSD_out_theory = np.sqrt(Sa_out_theory)

# ===================== 10. 加速度 PSD -> 位移 PSD =====================
omega = 2 * np.pi * f_psd
valid = omega > 0

Sd_in = np.zeros_like(Sa_in)
Sd_out_meas = np.zeros_like(Sa_out_meas)
Sd_out_theory = np.zeros_like(Sa_out_theory)

Sd_in[valid] = Sa_in[valid] / omega[valid]**4
Sd_out_meas[valid] = Sa_out_meas[valid] / omega[valid]**4
Sd_out_theory[valid] = Sa_out_theory[valid] / omega[valid]**4

# ===================== 11. RMS（位移 nm） =====================
BANDS = [(1, 40), (40, 100), (1, 100)]
band_labels = ["1–40 Hz", "40–100 Hz", "1–100 Hz"]


def calc_rms(f, psd, f1, f2, fmin=1.0):
    idx = (f >= max(f1, fmin)) & (f <= f2)
    if np.sum(idx) < 2:
        return np.nan
    return np.sqrt(np.trapz(psd[idx], f[idx]))

rms_rows = []
for (f1, f2), lab in zip(BANDS, band_labels):
    rin = calc_rms(f_psd, Sd_in, f1, f2) * 1e9
    rout_m = calc_rms(f_psd, Sd_out_meas, f1, f2) * 1e9
    rout_t = calc_rms(f_psd, Sd_out_theory, f1, f2) * 1e9
    rms_rows.append((lab, rin, rout_m, rout_t))

# ===================== 12. 画加速度 LPSD（加 3 条线） =====================
plt.figure(figsize=(10, 6))

plt.loglog(f_psd, LPSD_in, color="gray", lw=1.2, label="Input Acc LPSD")
plt.loglog(f_psd, LPSD_out_meas, color="tab:blue", lw=1.6, label="Output Acc LPSD (measured)")
plt.loglog(f_psd, LPSD_out_theory, "r--", lw=2.0, label="Output Acc LPSD (SDOF theory)")

plt.xlim(1, 100)
plt.xlabel("Frequency (Hz)")
plt.ylabel(r"Acceleration LPSD [$(m/s^2)/\sqrt{Hz}$]")
plt.title("Acceleration LPSD (Measured vs Theory)")
plt.grid(True, which="both", alpha=0.3)
plt.legend()

# ===================== 13. RMS 表格（nm，避免显示成 0） =====================
table_txt = (
    "DISPLACEMENT RMS (nm)\n"
    "-------------------------------------------------------\n"
    f"{'Band':<12} | {'In (nm)':>10} | {'Out(me) (nm)':>13} | {'Out(th) (nm)':>13}\n"
    "-------------------------------------------------------\n"
)

for lab, rin, rout_m, rout_t in rms_rows:
    table_txt += (
        f"{lab:<12} | "
        f"{rin:>10.3g} | "
        f"{rout_m:>13.3g} | "
        f"{rout_t:>13.3g}\n"
    )

plt.text(
    0.40, 0.05, table_txt,
    transform=plt.gca().transAxes,
    bbox=dict(facecolor="white", alpha=0.9),
    fontfamily="monospace"
)

plt.tight_layout()
plt.show()
