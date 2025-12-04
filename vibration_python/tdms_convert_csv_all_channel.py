# ============================================================
# TDMS --> CSV（多文件，不合并，每个 TDMS 一个子文件夹（与tdms同名））
#   1) 弹框多选 TDMS 文件；
#   2) 打印结构（Group/Channel）；
#   3) 每个 TDMS 输出到 CSV/<tdms文件名>/；
#   4) 每个通道单独一个 CSV（含 time,value）；
#   5) 不合并通道，保存在CSV文件下。
# ============================================================

import numpy as np
from nptdms import TdmsFile
from tkinter import Tk, filedialog
import os
import sys
import pandas as pd

# ----------------------------- 路径修复（中文兼容） -----------------------------
def fix_path(path: str) -> str:
    try:
        return path.encode(sys.getfilesystemencoding()).decode(sys.getfilesystemencoding())
    except Exception:
        return path

# ----------------------------- 打印 TDMS 结构 -----------------------------
def print_tdms_structure(tdms, fname):
    print(f"\n===== TDMS Structure: {fname} =====")
    for gi, group in enumerate(tdms.groups()):
        print(f"\n Group {gi}: {group.name}")
        for ci, ch in enumerate(group.channels()):
            print(f"   Channel {ci}: {ch.name}, length={len(ch[:])}")

# ----------------------------- 读取通道数据 -----------------------------
def read_channel_data(channel, default_fs=2000.0):
    data = np.array(channel[:], dtype=float)
    try:
        t = np.array(channel.time_track(), dtype=float)
        if len(t) != len(data):
            raise ValueError
        return t, data
    except Exception:
        dt = 1.0 / default_fs
        t = np.arange(len(data)) * dt
        return t, data

# ----------------------------- 保存通道 CSV -----------------------------
def save_channel_csv(output_folder, base, fname, group, ch_name, t, data):
    safe_ch = ch_name.replace("/", "_")
    csv_path = os.path.join(output_folder, f"{base}_{safe_ch}.csv")

    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(f"TDMS file: {fname}\n")
        f.write(f"Group: {group}\n")
        f.write(f"Channel: {ch_name}\n")
        f.write("time,value\n")
        for ti, vi in zip(t, data):
            f.write(f"{ti},{vi}\n")

    print(f"  -> Saved: {csv_path}")
    return csv_path

# ----------------------------- 主程序 -----------------------------
def main():

    root = Tk()
    root.withdraw()

    # 选择多个 TDMS 文件
    tdms_files = filedialog.askopenfilenames(
        title="Select TDMS files",
        filetypes=[("TDMS files", "*.tdms")]
    )

    if not tdms_files:
        print("No files selected.")
        return

    print("\nSelected TDMS files:")
    for f in tdms_files:
        print(" -", f)

    # 输出路径：所选 TDMS 所在目录 /CSV
    base_folder = os.path.dirname(tdms_files[0])
    csv_root = os.path.join(base_folder, "CSV")
    os.makedirs(csv_root, exist_ok=True)

    print(f"\nCSV output root directory:\n  {csv_root}")

    # ===============================
    # 逐个处理 TDMS 文件（不合并！）
    # ===============================
    for tdms_path in tdms_files:

        tdms_path = fix_path(tdms_path)
        fname = os.path.basename(tdms_path)
        base, _ = os.path.splitext(fname)

        print(f"\n========= Processing {fname} =========")

        # 为每个 TDMS 建一个子目录
        out_folder = os.path.join(csv_root, base)
        os.makedirs(out_folder, exist_ok=True)
        print(f"Output folder: {out_folder}")

        tdms = TdmsFile.read(tdms_path)
        print_tdms_structure(tdms, fname)

        # 遍历所有通道并输出 CSV
        for group in tdms.groups():
            for ch in group.channels():
                t, data = read_channel_data(ch)
                save_channel_csv(out_folder, base, fname, group.name, ch.name, t, data)

    print("\nAll done.\nCSV files are saved under:")
    print(f"  {csv_root}")


if __name__ == "__main__":
    main()
