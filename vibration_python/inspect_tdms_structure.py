import tkinter as tk
from tkinter import filedialog
from nptdms import TdmsFile

def select_tdms_files():
    """弹窗选择多个 TDMS 文件"""
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select TDMS Files",
        filetypes=[("TDMS files", "*.tdms")]
    )
    return list(file_paths)


def inspect_tdms(file_path):
    """打印一个 TDMS 文件的所有 group 和 channel 信息"""
    print("\n====================================")
    print("Inspecting:", file_path)
    print("====================================")

    tdms = TdmsFile.read(file_path)

    groups = tdms.groups()
    print(f"Total groups: {len(groups)}")

    for gi, g in enumerate(groups):
        print(f"\nGroup {gi}: '{g.name}'")

        channels = g.channels()
        if len(channels) == 0:
            print("  (No channels)")
        else:
            for ci, ch in enumerate(channels):
                try:
                    length = len(ch[:])
                except:
                    length = "(unavailable)"

                print(f"  Channel {ci}: '{ch.name}', length={length}")


if __name__ == "__main__":
    files = select_tdms_files()

    if len(files) == 0:
        print("No files selected.")
        exit()

    for f in files:
        inspect_tdms(f)
