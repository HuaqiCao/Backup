import numpy as np
from nptdms import TdmsFile
from tkinter import Tk, filedialog
import os
import sys

def fix_path(path: str) -> str:
    """Normalize path for Chinese characters on Windows."""
    try:
        return path.encode(sys.getfilesystemencoding()).decode(sys.getfilesystemencoding())
    except Exception:
        return path

def read_tdms_lmo(file_path, default_fs=2000.0):
    """
    Read TDMS file and extract time and LMO data.
    If no time info, build a uniform time axis with default_fs.
    """
    tdms = TdmsFile.read(file_path)

    lmo_channel = None
    lmo_group = None

    # Search channel whose name contains 'lmo' (case-insensitive)
    for group in tdms.groups():
        for ch in group.channels():
            if 'lmo' in ch.name.lower():
                lmo_channel = ch
                lmo_group = group
                break
        if lmo_channel is not None:
            break

    if lmo_channel is None:
        raise RuntimeError("No channel name contains 'lmo'.")

    # Read data as numpy array
    lmo_data = np.array(lmo_channel[:], dtype=float)

    # Try to get time track from TDMS
    try:
        t = np.array(lmo_channel.time_track(), dtype=float)
        if t.size != lmo_data.size:
            raise ValueError("Time length mismatch, using default Fs.")
        print("Using time_track from TDMS.")
    except Exception:
        # Build time axis from assumed sampling rate
        dt = 1.0 / float(default_fs)
        t = np.arange(lmo_data.size) * dt
        print(f"No valid time info, using default Fs = {default_fs} Hz.")

    return t, lmo_data, lmo_group.name, lmo_channel.name

def save_time_lmo_csv(csv_path, t, lmo, file_name, group_name, channel_name):
    """
    Save time and LMO data to CSV.
    First 4 lines are header.
    """
    with open(csv_path, 'w', encoding='utf-8-sig') as f:
        # 4 header lines
        f.write(f"TDMS file: {file_name}\n")
        f.write(f"Group: {group_name}\n")
        f.write(f"Channel: {channel_name}\n")
        f.write("time,lmo\n")  # real column header

        # Data lines
        for ti, vi in zip(t, lmo):
            f.write(f"{ti},{vi}\n")

    print(f"CSV saved: {csv_path}")

def main():
    # Hide Tk window
    root = Tk()
    root.withdraw()

    # Choose TDMS file
    tdms_path = filedialog.askopenfilename(
        title="Select TDMS file",
        filetypes=[("TDMS files", "*.tdms")]
    )
    if not tdms_path:
        print("No file selected.")
        return

    tdms_path = fix_path(os.path.abspath(tdms_path))
    folder, fname = os.path.split(tdms_path)
    base, _ = os.path.splitext(fname)

    print(f"Reading TDMS file: {tdms_path}")

    # Read time and LMO data
    t, lmo, group_name, channel_name = read_tdms_lmo(tdms_path, default_fs=2000.0)

    # Output CSV in the same folder
    csv_path = fix_path(os.path.join(folder, f"{base}_lmo.csv"))
    save_time_lmo_csv(csv_path, t, lmo, fname, group_name, channel_name)

if __name__ == "__main__":
    main()
