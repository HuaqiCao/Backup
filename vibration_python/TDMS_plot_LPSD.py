"""
TDMS 批量处理：振动对比分析
图例 = TDMS文件内部保存的Group/Channel名称（简化后，只保留到 .../g 部分）
时域显示 = 去掉增益后的传感器原始电压 [mV]
"""

from nptdms import TdmsFile
import numpy as np
import tkinter as tk
from tkinter import filedialog
import os
import glob
import time
import matplotlib.pyplot as plt
from scipy import signal


# ========== 硬件参数 ==========
FS = 5000               # 采样率 [Hz]
SENS_MV_G = 957         # 传感器灵敏度 [mV/g]
GAIN = 100              # 放大器增益 [V/V]

# 系统总灵敏度 [V/g]
SENS_TOTAL_V_G = SENS_MV_G * 1e-3 * GAIN  # 95.7 V/g


def select_folder():
    """弹框选文件夹"""
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="选择TDMS文件夹", initialdir=os.path.expanduser("~/Desktop"))
    root.destroy()
    return folder


def get_stats(data_v, data_v_no_gain=None):
    """
    统计信息
    
    参数:
        data_v: 测量电压 [V]（含增益）
        data_v_no_gain: 传感器原始电压 [V]（去掉增益后），可选
    """
    rms_v = np.sqrt(np.mean(data_v**2))
    pk_v = np.max(np.abs(data_v))
    
    # 如果没有提供无增益数据，计算
    if data_v_no_gain is None:
        data_v_no_gain = data_v / GAIN
    
    rms_v_no_gain = np.sqrt(np.mean(data_v_no_gain**2))
    pk_v_no_gain = np.max(np.abs(data_v_no_gain))
    
    # 加速度转换（基于测量电压）
    rms_g = rms_v / SENS_TOTAL_V_G
    pk_g = pk_v / SENS_TOTAL_V_G
    
    return {
        'rms_v': rms_v,                    # 测量电压 [V]
        'pk_v': pk_v,                      # 测量电压峰值 [V]
        'rms_v_no_gain': rms_v_no_gain,    # 传感器原始电压 [V]
        'pk_v_no_gain': pk_v_no_gain,      # 传感器原始电压峰值 [V]
        'rms_g': rms_g,                    # 加速度 [g]
        'pk_g': pk_g                       # 加速度峰值 [g]
    }


def simplify_legend(full_path):
    """
    只保留 group 名称到 /g 部分
    "chamber_noPT_mxc_gain100_957mv/g/1/Input 0" → "chamber_noPT_mxc_gain100_957mv/g"
    """
    if '/' in full_path:
        parts = full_path.split('/')
        result_parts = []
        for i, part in enumerate(parts):
            result_parts.append(part)
            if part.lower() == 'g' and i < len(parts) - 1:
                if i + 1 < len(parts) and parts[i+1].isdigit():
                    break
        return '/'.join(result_parts)
    return full_path


def process_tdms(filepath):
    """读取TDMS，过滤capture类型，简化图例名称"""
    tdms = TdmsFile.read(filepath)
    fname = os.path.basename(filepath)
    
    # 检查是否为 capture 类型
    file_props = tdms.properties
    tdms_type = file_props.get('type') or file_props.get('Type') or file_props.get('TYPE')
    
    if tdms_type and str(tdms_type).lower() == 'capture':
        print(f"  [跳过] 文件类型为 'capture': {fname}")
        return None
    
    # 检查 group 名称是否包含 capture
    for group in tdms.groups():
        if 'capture' in group.name.lower():
            print(f"  [跳过] Group名称包含'capture': {group.name}")
            return None
    
    results = []
    for group in tdms.groups():
        for ch in group.channels():
            # 读取原始数据
            raw_data = ch[:].astype(np.float64)
            
            # 判断数据单位（启发式）
            data_range = np.max(np.abs(raw_data))
            
            if data_range > 100:
                # 可能是mV单位，转换为V
                data_v_measured = raw_data * 1e-3
            else:
                data_v_measured = raw_data  # 假设已经是V
            
            # 【关键】计算去掉增益后的传感器原始电压
            # 传感器输出 = 测量电压 / 增益
            data_v_sensor = data_v_measured / GAIN
            
            # 简化图例名称
            legend = simplify_legend(group.name)
            print(f"    原始名称: '{group.name}' → 简化后: '{legend}'")
            print(f"    数据范围: 测量={np.min(data_v_measured)*1e3:.3f}~{np.max(data_v_measured)*1e3:.3f}mV, "
                  f"传感器原始={np.min(data_v_sensor)*1e3:.3f}~{np.max(data_v_sensor)*1e3:.3f}mV")
            
            results.append({
                'legend': legend,
                'data_v_measured': data_v_measured,   # 测量电压 [V]（含增益）
                'data_v_sensor': data_v_sensor,        # 传感器原始电压 [V]（去掉增益）
                'stats': get_stats(data_v_measured, data_v_sensor),
                'fs': FS,
                'fname': fname
            })
    return results


def plot_lpsd_g(ax, data_v_measured, fs, label, nfft=2**18):
    """LPSD绘制，单位为 g/√Hz（使用测量电压计算）"""
    nperseg = min(nfft, len(data_v_measured) // 4)
    nperseg = max(nperseg, 256)
    
    if len(data_v_measured) > 4 * nfft:
        nperseg = nfft
    
    noverlap = nperseg * 3 // 4
    
    f, Pxx = signal.welch(data_v_measured, fs, nperseg=nperseg, noverlap=noverlap,
                          window='hann', scaling='density')
    
    # V/√Hz → g/√Hz（使用测量电压和总灵敏度）
    v_to_g = 1.0 / SENS_TOTAL_V_G
    lpsd_v = np.sqrt(Pxx)
    lpsd_g = lpsd_v * v_to_g
    
    mask = (f > 0.1) & (f <= fs/2)
    ax.loglog(f[mask], lpsd_g[mask], label=label, alpha=0.8, linewidth=1)
    
    return {
        'nfft_requested': nfft,
        'nfft_actual': nperseg,
        'df': fs / nperseg,
        'duration': len(data_v_measured) / fs
    }


def plot_lpsd_only(all_ch, folder, nfft=2**18):
    """
    【新增】单独绘制LPSD图像，不包含时域图
    
    参数:
        all_ch: 通道数据列表
        folder: 保存路径
        nfft: FFT点数
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))  # 单独一个画布，横向更宽一些
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_ch)))
    plot_params = []
    
    for i, ch in enumerate(all_ch):
        c = colors[i]
        st = ch['stats']
        legend_name = ch['legend']
        
        # 构建图例标签（包含统计信息）
        label = (f"{legend_name}\n"
                 f"  RMS={st['rms_g']:.6f}g, PK={st['pk_g']:.6f}g")
        
        # 使用已有的plot_lpsd_g函数，但传入当前ax
        nperseg = min(nfft, len(ch['data_v_measured']) // 4)
        nperseg = max(nperseg, 256)
        
        if len(ch['data_v_measured']) > 4 * nfft:
            nperseg = nfft
        
        noverlap = nperseg * 3 // 4
        
        f, Pxx = signal.welch(ch['data_v_measured'], ch['fs'], nperseg=nperseg, 
                              noverlap=noverlap, window='hann', scaling='density')
        
        # V/√Hz → g/√Hz
        v_to_g = 1.0 / SENS_TOTAL_V_G
        lpsd_v = np.sqrt(Pxx)
        lpsd_g = lpsd_v * v_to_g
        
        mask = (f > 0.1) & (f <= ch['fs']/2)
        ax.loglog(f[mask], lpsd_g[mask], label=label, alpha=0.8, 
                  linewidth=1.2, color=c)
        
        plot_params.append({
            'legend': legend_name,
            'file': ch['fname'],
            'nfft_requested': nfft,
            'nfft_actual': nperseg,
            'df': ch['fs'] / nperseg,
            'duration': len(ch['data_v_measured']) / ch['fs']
        })
    
    # 设置图表属性
    ax.set_xlabel('Frequency [Hz]', fontsize=11)
    ax.set_ylabel('LPSD [g/√Hz]', fontsize=11)
    ax.set_title(f'Linear Power Spectral Density\n'
                 f'Sensor={SENS_MV_G}mV/g, Gain={GAIN}, Fs={FS}Hz', 
                 fontsize=12)
    ax.legend(loc='upper right', fontsize=7, ncol=1)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim([0.5, FS/2])
    
    # 可以添加一些参考线（可选）
    # ax.axhline(y=1e-6, color='r', linestyle='--', alpha=0.3, label='1μg/√Hz ref')
    
    plt.tight_layout()
    
    # 保存
    save_path = os.path.join(folder, f"LPSD_Only_{SENS_MV_G}mVg_gain{GAIN}_gUnits.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n【单独LPSD图已保存】: {save_path}")
    
    # 打印参数汇总
    print("\n" + "=" * 60)
    print("【单独LPSD图 - 频域分析参数汇总】")
    print("=" * 60)
    for p in plot_params:
        print(f"\n文件: {p['file']}")
        print(f"  图例名: {p['legend']}")
        print(f"  数据时长: {p['duration']:.3f} s")
        print(f"  请求nfft: {p['nfft_requested']:,}")
        print(f"  实际nfft: {p['nfft_actual']:,}")
        print(f"  频率分辨率: {p['df']:.4f} Hz")
        print(f"  LPSD单位: g/√Hz")
    
    plt.show()
    return fig, ax


def main():
    folder = select_folder()
    if not folder:
        return
    
    files = sorted(glob.glob(os.path.join(folder, "*.tdms")) + 
                   glob.glob(os.path.join(folder, "*.TDMS")))
    if not files:
        print("无TDMS文件")
        return
    
    print(f"\n找到 {len(files)} 个文件")
    print(f"硬件参数: 灵敏度={SENS_MV_G}mV/g, 增益={GAIN}")
    print(f"时域显示: 传感器原始电压（去掉增益后）")
    print("=" * 60)
    
    all_ch = []
    for f in files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"\n读取: {os.path.basename(f)} ({size_mb:.2f} MB)")
        t0 = time.time()
        results = process_tdms(f)
        t1 = time.time()
        print(f"  解析耗时: {t1-t0:.3f}s")
        
        if results is None:
            continue
            
        for r in results:
            st = r['stats']
            print(f"  最终图例: '{r['legend']}'")
            print(f"    测量电压: RMS={st['rms_v']*1e3:.3f}mV, PK={st['pk_v']*1e3:.3f}mV")
            print(f"    传感器原始: RMS={st['rms_v_no_gain']*1e3:.3f}mV, PK={st['pk_v_no_gain']*1e3:.3f}mV")
        all_ch.extend(results)
    
    if not all_ch:
        print("\n没有有效的通道数据可绘制")
        return
    
    # ========== 绘制组合图（时域+频域） ==========
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_ch)))
    
    plot_params = []
    
    for i, ch in enumerate(all_ch):
        c = colors[i]
        st = ch['stats']
        legend_name = ch['legend']
        
        # 【关键修改】时域标签显示去掉增益后的电压
        # 使用 data_v_sensor（去掉增益后的传感器原始电压）
        label = (f"{legend_name}\n"
                 f"  RMS={st['rms_v_no_gain']*1e3:.3f}mV ({st['rms_g']:.6f}g)\n"  # 显示无增益电压
                 f"  PK={st['pk_v_no_gain']*1e3:.3f}mV ({st['pk_g']:.6f}g)")
        
        # 【关键修改】时域绘图使用去掉增益后的电压
        n_pts = min(2*FS, len(ch['data_v_sensor']))
        t = np.arange(n_pts) / FS
        # 转换为mV显示，使用传感器原始电压（去掉增益）
        axes[0].plot(t, ch['data_v_sensor'][:n_pts]*1e3, color=c, alpha=0.7, 
                     label=label, linewidth=0.8)
        
        # 频域仍使用测量电压计算（保证加速度正确）
        params = plot_lpsd_g(axes[1], ch['data_v_measured'], ch['fs'], label=legend_name)
        params['legend'] = legend_name
        params['file'] = ch['fname']
        plot_params.append(params)
    
    # 【关键修改】时域图Y轴标签改为传感器原始电压
    axes[0].set_xlabel('Time [s]')
    axes[0].set_ylabel('Sensor Voltage [mV] (Gain Removed)')  # 明确标注去掉增益
    axes[0].set_title(f'Time Domain | Sensor={SENS_MV_G}mV/g, Gain={GAIN} (Removed), Fs={FS}Hz')
    axes[0].legend(loc='upper right', fontsize=7, ncol=2)
    axes[0].grid(True, alpha=0.3)
    
    # 频域图（不变，仍是g/√Hz）
    axes[1].set_xlabel('Frequency [Hz]')
    axes[1].set_ylabel('LPSD [g/√Hz]')
    axes[1].set_title('Linear Power Spectral Density')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3, which='both')
    axes[1].set_xlim([0.5, FS/2])
    
    plt.tight_layout()
    
    # 保存组合图
    save_path = os.path.join(folder, f"LPSD_{SENS_MV_G}mVg_gain{GAIN}_gUnits_sensorV.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n已保存组合图: {save_path}")
    
    # ========== 【新增】绘制单独的LPSD图 ==========
    print("\n" + "=" * 60)
    print("正在生成单独的LPSD图...")
    plot_lpsd_only(all_ch, folder)
    
    # ========== 参数汇总（组合图） ==========
    print("\n" + "=" * 60)
    print("【组合图 - 频域分析参数汇总】")
    print(f"注意: 时域显示为传感器原始电压（去掉增益{GAIN}后）")
    print("=" * 60)
    for p in plot_params:
        print(f"\n文件: {p['file']}")
        print(f"  图例名: {p['legend']}")
        print(f"  数据时长: {p['duration']:.3f} s")
        print(f"  请求nfft: {p['nfft_requested']:,}")
        print(f"  实际nfft: {p['nfft_actual']:,}")
        print(f"  频率分辨率: {p['df']:.4f} Hz")
        print(f"  LPSD单位: g/√Hz")
    
    plt.show()


if __name__ == "__main__":
    main()
