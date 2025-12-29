import numpy as np
import matplotlib.pyplot as plt
from tkinter import filedialog, Tk
from scipy.optimize import curve_fit
import os

def double_exponential(t, A_f, tau_f, A_s, tau_s, offset):
    """双指数衰减数学模型"""
    return A_f * np.exp(-t / tau_f) + A_s * np.exp(-t / tau_s) + offset

def fit_particle_signal(file_path, fs=5000):
    """对单个文件进行预处理和拟合"""
    try:
        raw_data = np.loadtxt(file_path)
        # 基础预处理：去基线
        data = raw_data - np.mean(raw_data[:50])
        # 自动翻转脉冲，确保峰值向上
        if np.abs(np.min(data)) > np.max(data):
            data = -data
            
        peak_idx = np.argmax(data)
        fit_data = data[peak_idx:]
        t_fit = np.arange(len(fit_data)) / fs
        
        # 初始参数猜测: [Af, tf, As, ts, offset]
        p0 = [max(fit_data)*0.6, 0.002, max(fit_data)*0.4, 0.015, 0]
        bounds = (0, [np.inf, 0.1, np.inf, 1.0, np.inf])

        popt, _ = curve_fit(double_exponential, t_fit, fit_data, p0=p0, bounds=bounds, maxfev=10000)
        
        return {
            "file_name": os.path.basename(file_path),
            "t_full": (np.arange(len(data)) - peak_idx) / fs,
            "d_full": data,
            "t_fit": t_fit,
            "fit_params": popt,
            "fit_curve": double_exponential(t_fit, *popt)
        }
    except Exception as e:
        print(f"文件 {file_path} 处理失败: {e}")
        return None

def main():
    # 1. 初始化文件选择
    root = Tk()
    root.withdraw()
    print("请选择粒子信号文件（按住 Ctrl 或 Shift 可多选）...")
    files = filedialog.askopenfilenames(title="选择粒子信号文件", 
                                        filetypes=[("Text/Tex files", "*.txt *.tex"), ("All files", "*.*")])
    
    if not files:
        print("未选择任何文件。")
        return

    num_files = len(files)
    print(f"已选择 {num_files} 个文件。开始分析...")

    # 2. 动态创建画布布局
    # 计算子图行数，每列放 1 个，或者根据需要调整
    fig, axes = plt.subplots(num_files, 1, figsize=(10, 4 * num_files), squeeze=False)
    
    for i, path in enumerate(files):
        res = fit_particle_signal(path)
        ax = axes[i, 0]
        
        if res:
            Af, tf, As, ts, off = res["fit_params"]
            
            # 终端输出参数
            print(f"\n>>> [{res['file_name']}]")
            print(f"  tau_fast: {tf*1000:.3f} ms | tau_slow: {ts*1000:.3f} ms")
            print(f"  幅度比 (Af/As): {Af/As:.3f}")

            # 绘图：原始数据与拟合曲线
            ax.plot(res["t_full"], res["d_full"], 'k.', alpha=0.15, label='Raw Data')
            ax.plot(res["t_fit"], res["fit_curve"], 'r-', linewidth=2, label='Total Fit')
            
            # 绘图：拆解成分
            ax.plot(res["t_fit"], Af * np.exp(-res["t_fit"]/tf) + off, 'g--', alpha=0.7, label='Fast Comp')
            ax.plot(res["t_fit"], As * np.exp(-res["t_fit"]/ts) + off, 'b--', alpha=0.7, label='Slow Comp')
            
            ax.set_title(f"File: {res['file_name']} (tf={tf*1000:.2f}ms, ts={ts*1000:.2f}ms)")
            ax.set_ylabel("ADC")
            ax.legend(loc='upper right', fontsize='small')
            ax.grid(True, alpha=0.2)
        else:
            ax.text(0.5, 0.5, "Fit Failed", ha='center')

    plt.xlabel("Time from Peak (s)")
    plt.tight_layout()
    print("\n所有文件处理完毕。")
    plt.show()

if __name__ == "__main__":
    main()