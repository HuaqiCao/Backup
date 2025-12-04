# ============================================================
# TDMS --> CSV 所有通道（输出到当前目录 ./CSV）：
#   1) 弹框多选 TDMS 文件；
#   2) 打印结构（Group/Channel）；
#   3) 每个通道导出 CSV（含 time,value）；
#   4) 同名通道合并为 merged_<channel>.csv；
#   5) 所有文件输出到脚本当前目录下的 ./CSV 目录。
# ============================================================

import numpy as np
from nptdms import TdmsFile
from tkinter import Tk, filedialog
import os
import sys
import pandas as pd

# ============================================================
# 路径修复（中文兼容）
# ============================================================
def fix_path(path: str) -> str:
    try:
        return path.encode(sys.getfilesystemencoding()).decode(sys.getfilesystemencoding())
    except Exception:
        return path

# ============================================================
# 打印 TDMS 结构
# ============================================================
def print_tdms_structure(tdms, fname):
    print(f"\n===== TDMS Structure: {fname} =====")
    for gi, group in enumerate(tdms.groups()):
        print(f"\n Group {gi}: {group.name}")
        for ci, ch in enumerate(group.channels()):
            print(f"   Channel {ci}: {ch.name}, length={len(ch[:])}")

# ============================================================
# 读取通道 → 返回 (t,data)
# ============================================================
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

# ============================================================
# 保存单通道到 CSV
# ============================================================
def save_channel_csv(csv_folder, base, fname, group, ch_name, t, data):
    safe_ch = ch_name.replace("/", "_")
    csv_path = os.path.join(csv_folder, f"{base}_{safe_ch}.csv")

    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(f"TDMS file: {fname}\n")
        f.write(f"Group: {group}\n")
        f.write(f"Channel: {ch_name}\n")
        f.write("time,value\n")
        for ti, vi in zip(t, data):
            f.write(f"{ti},{vi}\n")

    print(f"  -> Saved: {csv_path}")
    return csv_path

# ============================================================
# 主程序：多选 TDMS → 导出 CSV → 合并通道
# ============================================================
def main():

    # 当前目录下创建 CSV 文件夹
    output_root = os.path.join(os.getcwd(), "CSV")
    os.makedirs(output_root, exist_ok=True)
    print(f"\nCSV output directory:\n  {output_root}")

    # 选择多个 TDMS
    root = Tk()
    root.withdraw()

    tdms_files = filedialog.askopenfilenames(
        title="Select TDMS files",
        filetypes=[("TDMS files", "*.tdms")]
    )

    if not tdms_files:
        print("No files selected.")
        return

    print("\nSelected files:")
    for f in tdms_files:
        print(" -", f)

    channel_csv_dict = {}

    # ===============================
    # 处理每个 TDMS 文件
    # ===============================
    for tdms_path in tdms_files:

        tdms_path = fix_path(tdms_path)
        fname = os.path.basename(tdms_path)
        base, _ = os.path.splitext(fname)

        print(f"\n========= Processing {fname} =========")
        tdms = TdmsFile.read(tdms_path)
        print_tdms_structure(tdms, fname)

        # 遍历所有 group / channel
        for group in tdms.groups():
            for ch in group.channels():

                t, data = read_channel_data(ch)
                csv_path = save_channel_csv(
                    output_root,
                    base,
                    fname,
                    group.name,
                    ch.name,
                    t,
                    data
                )

                cname = ch.name
                channel_csv_dict.setdefault(cname, []).append(csv_path)

    # ===============================
    # 合并同名通道
    # ===============================
    print("\n========= Merging channels =========")

    for cname, csv_list in channel_csv_dict.items():

        merged_path = os.path.join(
            output_root,
            f"merged_{cname.replace('/', '_')}.csv"
        )
        print(f"\nMerging channel '{cname}' -> {merged_path}")

        df_all = []

        for csv_file in csv_list:
            df = pd.read_csv(csv_file, skiprows=3)
            df_all.append(df)

        df_all = pd.concat(df_all, ignore_index=True)
        df_all = df_all.sort_values(by="time")

        df_all.to_csv(merged_path, index=False, encoding="utf-8-sig")
        print(f"  ✔ Saved merged CSV: {merged_path}")

    print("\nAll done.\nCSV files are saved under:")
    print(f"  {output_root}")


if __name__ == "__main__":
    main()
