import os
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import plotly.graph_objects as go
import plotly.io as pio

# ======================== 用户配置区 ========================
DATA_ROOT = "./HQ_Noise_Test"
SAMPLING_RATE = 5000
BIN_DTYPE = np.uint32
NFFT = 131072  # ✅ 提高分辨率：增加FFT点数
NOVERLAP = NFFT // 2
PULSE_THRESHOLD = 5.0
PULSE_WINDOW = 5
CHANNEL_LABELS = {0:"pulser_clock", 1:"CROSS-NAT", 2: "NBU_M_001", 3: "SICCAS_M_001", 4:"Gecosi21", 5:"frame_41B3X1N001"}
RUN_FREQ_MAP = {77: 0, 78: 120,79: 110, 80: 100, 81: 90, 82: 80, 83: 70, 84: 60, 85: 50, 86: 40, 87: 30, 88: 20, 89:10}
# ✅ 颜色区分：使用tab20支持最多20个run不重复
COLORS = plt.cm.tab20(np.linspace(0, 1, 20))
# ===========================================================

def rgba_to_hex(rgba):
    """将 (0-1) 范围的 RGBA 元组转换为十六进制颜色字符串"""
    # 只转换 RGB 三个通道，忽略 Alpha 通道
    return '#{:02x}{:02x}{:02x}'.format(
        int(rgba[0] * 255),
        int(rgba[1] * 255),
        int(rgba[2] * 255)
    )
def extract_run_and_channel(filepath):
    basename = os.path.basename(filepath)
    parts = basename.replace(".bin", "").split("_")
    run = int(parts[0])
    channel = int(parts[2])
    return run, channel


def remove_pulse(data, threshold=5.0, window=5):
    """
    使用鲁棒的 MAD (中值绝对偏差) 检测脉冲，并使用 NumPy 卷积快速扩展窗口
    """
    if len(data) == 0:
        return data

    # 1. 转换为浮点型，防止后续插值被截断，同时避免污染原数据
    clean = data.astype(np.float64)

    # 2. 计算中值和 MAD (比均值/标准差鲁棒得多，不怕超大脉冲)
    median_val = np.median(clean)
    abs_deviation = np.abs(clean - median_val)
    mad = np.median(abs_deviation)
    
    if mad == 0:
        # 如果数据太干净或者全是常数，改用标准差兜底
        mad = np.std(clean)
        if mad == 0: return clean

    # 3. 3. 门限检测 (1.4826 是将 MAD 缩放到等效标准差的常数)
    # 低于此标准的判定为正常信号
    sigma_robust = 1.4826 * mad
    pulse_mask = abs_deviation > (threshold * sigma_robust)

    if not np.any(pulse_mask):
        return clean

    # 4. 快速扩展窗口：使用一维卷积（box blur效果）代替 Python 的 for 循环
    # 只要周围 window 范围内有 True，卷积结果就会大于 0
    kernel = np.ones(2 * window + 1)
    extended_mask = signal.convolve(pulse_mask.astype(float), kernel, mode='same') > 0.1

    # 5. 线性插值替换
    valid_indices = np.where(~extended_mask)[0]
    if len(valid_indices) > 1:
        extended_indices = np.where(extended_mask)[0]
        clean[extended_mask] = np.interp(
            extended_indices,
            valid_indices,
            clean[valid_indices]
        )
    else:
        clean[extended_mask] = median_val

    return clean

# 找到原来的整个 compute_psd 函数：
def compute_psd(data, fs, nfft=NFFT, noverlap=NOVERLAP, gain=10300):
    f, psd = signal.welch(
        data, fs=fs,
        nperseg=nfft, noverlap=noverlap,
        scaling="density"
    )
    psd = psd / (gain ** 2)  # ✅ 将 PSD 从 counts²/Hz 转换为 V²/Hz
    return f, psd

# 替换为下面这个更稳健的版本：
def compute_psd(data, fs, nfft=NFFT, noverlap=NOVERLAP, gain=10300):
    nperseg = min(len(data), nfft)  # 防止短数据导致内部隐式缩减报错
    f, psd = signal.welch(
        data, fs=fs,
        nperseg=nperseg, noverlap=noverlap, nfft=nfft,  # 显式固定 nfft
        scaling="density"
    )
    psd = psd / (gain ** 2)
    return f, psd


def main():
    bin_files = []
    for root, dirs, files in os.walk(DATA_ROOT):
        for f in files:
            if f.endswith(".bin"):
                bin_files.append(os.path.join(root, f))

    if not bin_files:
        print(f"未在 {DATA_ROOT} 下找到任何 .bin 文件")
        return

    channel_runs = {}
    print(f"共找到 {len(bin_files)} 个 bin 文件，开始处理...")

    for filepath in bin_files:
        try:
            run, channel = extract_run_and_channel(filepath)
        except (IndexError, ValueError):
            print(f"跳过无法解析的文件: {filepath}")
            continue

        data = np.fromfile(filepath, dtype=BIN_DTYPE)
        if data.size == 0:
            print(f"空文件，跳过: {filepath}")
            continue

        data_clean = remove_pulse(data)
        f, psd = compute_psd(data_clean, fs=SAMPLING_RATE)

        if channel not in channel_runs:
            channel_runs[channel] = {}
        channel_runs[channel][run] = {"f": f, "psd": psd}
        print(f"  处理完成: run={run}, ch={channel}, 样本数={len(data)}")

    if not channel_runs:
        print("没有有效数据可绘制")
        return

    # # ======================== ✅ 独立绘图 + 对数坐标 ========================
    # for channel, runs_data in sorted(channel_runs.items()):
    #     label = CHANNEL_LABELS.get(channel, f"Ch{channel}")
    #     # 每个channel独立创建figure
    #     fig, ax = plt.subplots(figsize=(12, 6))

    #     for run_idx, (run, data_dict) in enumerate(sorted(runs_data.items())):
    #         f = data_dict["f"]
    #         psd = data_dict["psd"]
    #         # ✅ 颜色区分：每个run使用tab20中的唯一颜色
    #         color = COLORS[run_idx % len(COLORS)]
    #         freq = RUN_FREQ_MAP.get(run, run)
    #         ax.plot(f, psd, label=f"Frequency:{freq} Hz", color=color, alpha=0.8, linewidth=1.0)

    #         # ✅ 对数坐标：直接绘制原始PSD，由坐标轴处理对数变换
    #         # ax.plot(f, psd, label=f"Run {run}", color=color, alpha=0.8, linewidth=1.0)

    #     # ✅ 对数坐标设置
    #     ax.set_xscale('log')
    #     ax.set_yscale('log')
    #     ax.set_xlabel("Frequency (Hz)")
    #     ax.set_ylabel("PSD (V²/Hz)")
    #     ax.set_title(f"Noise PSD - Channel: {label} (Log Scale, NFFT={NFFT})")
    #     ax.legend(fontsize=8, loc="upper right", ncol=2)
    #     ax.grid(True, alpha=0.3, which='both')

    #     plt.tight_layout()

    #     # ✅ 独立保存：每个channel单独保存
    #     out_path = os.path.join(DATA_ROOT, f"psd_ch{channel}_{label}.png")
    #     plt.savefig(out_path, dpi=150, bbox_inches='tight')
    #     print(f"图像已保存: {out_path}")
    #     plt.show()


    # 在 main() 函数中，替换原有的 matplotlib 绘图循环：
    for channel, runs_data in sorted(channel_runs.items()):
        label = CHANNEL_LABELS.get(channel, f"Ch{channel}")
        fig = go.Figure()

        for run_idx, (run, data_dict) in enumerate(sorted(runs_data.items())):
            f = data_dict["f"]
            psd = data_dict["psd"]
            
            rgba_color = COLORS[run_idx % len(COLORS)]
            color = rgba_to_hex(rgba_color)
            freq = RUN_FREQ_MAP.get(run, run)

            # ✅ 优化 1：改用 go.Scattergl 开启 WebGL 加速，数十万点丝滑不卡顿
            # ✅ 优化 2：[1:] 切片剔除 0 频（DC 分量），防止对数坐标轴崩溃
            fig.add_trace(go.Scattergl(
                x=f[1:], y=psd[1:],
                mode='lines',
                name=f"{freq} Hz",
                line=dict(color=color, width=1.0),
                opacity=0.8
            ))

        # ✅ 对数坐标 + 标签设置
        fig.update_layout(
            xaxis_type="log",
            yaxis_type="log",
            xaxis_title="Frequency (Hz)",
            yaxis_title="PSD (V²/Hz)",
            title=f"Noise PSD - Channel: {label} (Log Scale, NFFT={NFFT})",
            # legend=dict(fontsize=10, orientation="h", yanchor="top", y=1.0, xanchor="right", x=1.0),
            legend=dict(
                font=dict(size=10),  # ✅ 使用 font 字典设置字体大小
                orientation="h",
                yanchor="top",
                y=1.0,
                xanchor="right",
                x=1.0
            ),
            width=1200,
            height=600,
            hovermode="x unified",  # ✅ 交互：鼠标悬停统一显示所有曲线数据
            template="plotly_white"
        )

        # ✅ 导出为交互式 HTML
        out_path = os.path.join(DATA_ROOT, f"psd_ch{channel}_{label}.html")
        pio.write_html(fig, file=out_path, auto_open=False)
        print(f"HTML 已保存: {out_path}")

if __name__ == "__main__":
    main()