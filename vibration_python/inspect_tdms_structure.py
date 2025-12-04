# ============================================================
# 本代码用于选择多个 TDMS 文件，并逐个打印其中的所有 Group
# 与 Channel 名称及通道长度，实现 TDMS 文件结构快速查看。
# ============================================================

import tkinter as tk
from tkinter import filedialog
from nptdms import TdmsFile

def select_tdms_files():
    """弹窗选择多个 TDMS 文件"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    file_paths = filedialog.askopenfilenames(
        title="Select TDMS Files",
        filetypes=[("TDMS files", "*.tdms")]
    )
    return list(file_paths)

def inspect_tdms(file_path):
    """打印单个 TDMS 文件的 Group 和 Channel 信息"""
    print("\n====================================")
    print("Inspecting:", file_path)
    print("====================================")

    tdms = TdmsFile.read(file_path)  # 读取 TDMS

    groups = tdms.groups()
    print(f"Total groups: {len(groups)}")

    # 遍历所有 Group
    for gi, g in enumerate(groups):
        print(f"\nGroup {gi}: '{g.name}'")

        channels = g.channels()
        if len(channels) == 0:
            print("  (No channels)")
        else:
            # 遍历每个通道
            for ci, ch in enumerate(channels):
                try:
                    length = len(ch[:])  # 读取通道数据长度
                except:
                    length = "(unavailable)"

                print(f"  Channel {ci}: '{ch.name}', length={length}")

if __name__ == "__main__":
    files = select_tdms_files()

    if len(files) == 0:
        print("No files selected.")
        exit()

    # 逐个检查所选文件
    for f in files:
        inspect_tdms(f)
