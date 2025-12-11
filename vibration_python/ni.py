# ============================================================
# TDMS → 合并真实时间轴版（人类可读时间 + 自动跨天）
# ============================================================

import numpy as np
import pandas as pd
import os
import re
from datetime import datetime
from nptdms import TdmsFile
from tkinter import Tk, filedialog

# ============================================================
# 从文件名解析日期和时间（适配文件名：记录-2024-08-19 170604 434.tdms）
# ============================================================
def parse_filename_timestamp(fname):
    base = os.path.splitext(fname)[0]

    # 找 YYYY-MM-DD
    m_date = re.search(r"\d{4}-\d{2}-\d{2}", base)
    if m_date:
        date_str = m_date.group(0)
    else:
        m_date2 = re.search(r"\b(\d{8})\b", base)
        if m_date2:
            raw = m_date2.group(1)
            date_str = datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            raise ValueError(f"未找到日期: {fname}")

    # 找 HHMMSS
    m_time = re.search(r"\b(\d{6})\b", base)
    if m_time:
        time_str = m_time.group(1)
    else:
        time_str = "000000"

    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H%M%S")
    return dt

# ============================================================
# 读取 TDMS 通道
# ============================================================
def read_tdms_channel(ch):
    data = np.array(ch[:], dtype=float)
    try:
        t_rel = np.array(ch.time_track(), dtype=float)
    except:
        fs = 2000
        t_rel = np.arange(len(data)) / fs
    return t_rel, data

# ============================================================
# 主程序
# ============================================================
def main():
    root = Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="选择 TDMS 文件",
        filetypes=[("TDMS files", "*.tdms")]
    )

    if not files:
        print("未选择文件")
        return

    # 输出目录：使用第一个文件所在路径
    input_dir = os.path.dirname(files[0])
    outdir = os.path.join(input_dir, "merged_real_time")
    os.makedirs(outdir, exist_ok=True)

    print("\n选中的文件：")
    for f in files:
        print(" -", f)

    file_info = []
    for f in files:
        fname = os.path.basename(f)
        start_dt = parse_filename_timestamp(fname)
        file_info.append((f, fname, start_dt))

    file_info.sort(key=lambda x: x[2])

    print("\n按真实时间排序后：")
    for f, name, dt in file_info:
        print(f"{name}  -->  {dt}")

    # ============================================================
    # 文件合并
    # ============================================================
    channel_dict = {}

    for tdms_path, fname, start_dt in file_info:

        print(f"\n处理文件：{fname}")
        td = TdmsFile.read(tdms_path)
        start_ts = start_dt.timestamp()

        for g in td.groups():
            for ch in g.channels():

                t_rel, data = read_tdms_channel(ch)
                t_abs = start_ts + t_rel  # UNIX 时间戳

                cname = ch.name
                channel_dict.setdefault(cname, []).append(
                    (t_abs, data)
                )

    # ============================================================
    # 保存合并结果
    # ============================================================
    for cname, data_list in channel_dict.items():

        merged_t = []
        merged_d = []

        for t_abs, data in data_list:
            merged_t.append(t_abs)
            merged_d.append(data)

        merged_t = np.concatenate(merged_t)
        merged_d = np.concatenate(merged_d)

        idx = np.argsort(merged_t)
        merged_t = merged_t[idx]
        merged_d = merged_d[idx]

        # 人类可读时间
        merged_dt = [datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                     for ts in merged_t]

        df = pd.DataFrame({
            "real_datetime": merged_dt,     # 人类可读
            "absolute_time": merged_t,      # 原始时间戳
            "value": merged_d               # 通道值
        })

        outpath = os.path.join(outdir, f"merged_{cname}.csv")
        df.to_csv(outpath, index=False, encoding="utf-8-sig")

        print(f"✔ 保存：{outpath}")

    print("\n🎉 所有通道真实时间合并完成！")


if __name__ == "__main__":
    main()
