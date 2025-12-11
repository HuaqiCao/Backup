import numpy as np
import pandas as pd
import os
import re
from datetime import datetime
from nptdms import TdmsFile, TdmsWriter, ChannelObject
from tkinter import Tk, filedialog


# ============================================================
# 从文件名解析真实时间（例如：记录-2025-10-20 105823 004.tdms）
# ============================================================
def parse_filename_timestamp(fname):
    base = os.path.splitext(fname)[0]

    # YYYY-MM-DD
    m_date = re.search(r"\d{4}-\d{2}-\d{2}", base)
    if not m_date:
        raise ValueError(f"未找到日期: {fname}")
    date_str = m_date.group(0)

    # HHMMSS
    m_time = re.search(r"\b(\d{6})\b", base)
    time_str = m_time.group(1) if m_time else "000000"

    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H%M%S")
    return dt


# ============================================================
# 主程序：合并所有 TDMS
# ============================================================
def main():

    root = Tk()
    root.withdraw()

    tdms_files = filedialog.askopenfilenames(
        title="选择多个 TDMS 文件",
        filetypes=[("TDMS files", "*.tdms")]
    )

    if not tdms_files:
        print("未选择文件")
        return

    input_dir = os.path.dirname(tdms_files[0])
    out_tdms = os.path.join(input_dir, "merged.tdms")

    # ---- 解析文件名时间 ----
    file_info = []
    for f in tdms_files:
        fname = os.path.basename(f)
        start_dt = parse_filename_timestamp(fname)
        file_info.append((f, fname, start_dt))

    # 按真实时间排序
    file_info.sort(key=lambda x: x[2])

    print("\n文件排序结果：")
    for f, name, dt in file_info:
        print(f"{name}  -->  {dt}")

    # ============================================================
    # 读取并按 channel 名称累积数据（忽略 group 名称）
    # ============================================================
    merged = {}   # key = channel name

    for tdms_path, fname, start_dt in file_info:

        td = TdmsFile.read(tdms_path)
        t0 = start_dt.timestamp()

        for g in td.groups():
            for ch in g.channels():

                data = np.array(ch[:], dtype=float)

                # 相对时间
                try:
                    t_rel = np.array(ch.time_track(), dtype=float)
                except:
                    fs = 2000
                    t_rel = np.arange(len(data)) / fs

                # 真实时间戳
                t_abs = t0 + t_rel

                cname = ch.name    # ★★ 只按 channel 名称合并 ★★

                if cname not in merged:
                    merged[cname] = {"time": [], "value": []}

                merged[cname]["time"].append(t_abs)
                merged[cname]["value"].append(data)

    # ============================================================
    # 拼接数据并按真实时间排序
    # ============================================================
    for cname in merged:
        merged[cname]["time"] = np.concatenate(merged[cname]["time"])
        merged[cname]["value"] = np.concatenate(merged[cname]["value"])

        idx = np.argsort(merged[cname]["time"])
        merged[cname]["time"] = merged[cname]["time"][idx]
        merged[cname]["value"] = merged[cname]["value"][idx]

    # ============================================================
    # 写入新的 TDMS 文件（统一保存到一个 group）
    # ============================================================
    with TdmsWriter(out_tdms) as writer:

        for cname, data_dict in merged.items():

            ch_time = ChannelObject(
                "Merged", cname + "_time", data_dict["time"]
            )
            ch_value = ChannelObject(
                "Merged", cname + "_value", data_dict["value"]
            )

            writer.write_segment([ch_time, ch_value])

    print(f"\n✔ 已生成合并 TDMS: {out_tdms}")

    # ============================================================
    # 打印前 10 行 + 后 10 行（任意通道检查）
    # ============================================================
    print("\n===== 打印检查数据（示例任意通道）=====")

    first_key = next(iter(merged))
    t = merged[first_key]["time"]
    v = merged[first_key]["value"]
    total_len = len(t)

    print(f"示例通道: {first_key}")
    print(f"共有 {total_len} 行数据\n")

    # ---- 前 10 行 ----
    print(">>> 前 10 行：")
    for i in range(min(10, total_len)):
        full = datetime.fromtimestamp(t[i]).strftime("%Y-%m-%d %H:%M:%S.%f")
        print(f"{full[:-2]}, {v[i]}")

    # ---- 后 10 行 ----
    print("\n>>> 后 10 行：")
    for i in range(max(0, total_len - 10), total_len):
        full = datetime.fromtimestamp(t[i]).strftime("%Y-%m-%d %H:%M:%S.%f")
        print(f"{full[:-2]}, {v[i]}")


if __name__ == "__main__":
    main()
