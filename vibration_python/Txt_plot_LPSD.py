"""
TXT batch vibration analysis

TXT format:
Time        Channel A
(s)         (mV)

0.0008      -103.122
0.0010      -107.044
...

Column 1: Time [s]
Column 2: Measured voltage [mV], including amplifier gain

Time domain: sensor voltage after gain removal [mV]
Frequency domain: LPSD [g/√Hz]
"""

import os
import glob
import time
import tkinter as tk
from tkinter import filedialog

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal


# ============================================================
# Parameters
# ============================================================

FS_DEFAULT = 5000       # Default sampling rate [Hz]
SENS_MV_G = 957         # Sensor sensitivity [mV/g]
GAIN = 100              # Amplifier gain
NFFT = 2**14            # Welch segment length target
TIME_DISPLAY = 2.0      # Time-domain display length [s]

# Total sensitivity [V/g]
SENS_TOTAL_V_G = SENS_MV_G * 1e-3 * GAIN


# ============================================================
# Select folder
# ============================================================

def select_folder():
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="Select TXT Folder",
        initialdir=os.path.expanduser("~/Desktop")
    )

    root.destroy()
    return folder


# ============================================================
# Read TXT
# ============================================================

def load_txt_data(filepath):
    """Read time [s] and voltage [mV]."""

    encodings = [
        "utf-8-sig",
        "utf-8",
        "gbk",
        "gb2312"
    ]

    lines = None

    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None:
        raise ValueError("Cannot recognize TXT encoding.")

    data_rows = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Support tab, spaces, comma and semicolon
        parts = (
            line.replace(",", " ")
                .replace(";", " ")
                .split()
        )

        if len(parts) < 2:
            continue

        try:
            t = float(parts[0])
            v = float(parts[1])

            if np.isfinite(t) and np.isfinite(v):
                data_rows.append([t, v])

        except ValueError:
            # Ignore header lines
            continue

    if len(data_rows) < 2:
        raise ValueError(
            f"Not enough valid data points: {len(data_rows)}"
        )

    data = np.asarray(data_rows, dtype=np.float64)

    return data[:, 0], data[:, 1]


# ============================================================
# Sampling rate
# ============================================================

def calculate_fs(time_s):
    """Calculate Fs from median time interval."""

    dt = np.diff(time_s)
    dt = dt[np.isfinite(dt) & (dt > 0)]

    if len(dt) == 0:
        print(
            f"    Warning: cannot determine Fs, "
            f"use {FS_DEFAULT} Hz"
        )
        return float(FS_DEFAULT)

    return 1.0 / np.median(dt)


# ============================================================
# Process TXT
# ============================================================

def process_txt(filepath):
    """Read and convert one TXT file."""

    fname = os.path.basename(filepath)

    # Legend = filename only, without extension
    legend = os.path.splitext(fname)[0]

    time_s, raw_mv = load_txt_data(filepath)

    fs = calculate_fs(time_s)

    # Measured voltage: mV -> V
    data_v_measured = raw_mv * 1e-3

    # Sensor voltage after removing gain
    data_v_sensor = data_v_measured / GAIN

    dt = np.diff(time_s)
    dt = dt[np.isfinite(dt) & (dt > 0)]

    dt_median = np.median(dt) if len(dt) else np.nan

    print(f"    Legend: {legend}")
    print(f"    Samples: {len(raw_mv):,}")
    print(
        f"    Time: {time_s[0]:.6f} ~ "
        f"{time_s[-1]:.6f} s"
    )
    print(f"    dt: {dt_median:.9f} s")
    print(f"    Fs: {fs:.3f} Hz")

    return {
        "legend": legend,
        "time_s": time_s,
        "data_v_measured": data_v_measured,
        "data_v_sensor": data_v_sensor,
        "fs": fs,
        "fname": fname
    }


# ============================================================
# Welch parameters
# ============================================================

def get_welch_params(data_length, nfft=NFFT):
    """Generate safe Welch parameters."""

    if data_length < 2:
        raise ValueError("Signal is too short.")

    target = max(data_length // 4, 256)

    nperseg = min(
        nfft,
        target,
        data_length
    )

    nperseg = max(nperseg, 2)

    noverlap = 3 * nperseg // 4
    noverlap = min(noverlap, nperseg - 1)

    return nperseg, noverlap


# ============================================================
# Calculate LPSD
# ============================================================

def calculate_lpsd(data_v_measured, fs, nfft=NFFT):
    """Return frequency and LPSD [g/√Hz]."""

    nperseg, noverlap = get_welch_params(
        len(data_v_measured),
        nfft
    )

    f, Pxx = signal.welch(
        data_v_measured,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        scaling="density"
    )

    # V/√Hz -> g/√Hz
    lpsd_g = np.sqrt(Pxx) / SENS_TOTAL_V_G

    return f, lpsd_g, nperseg


# ============================================================
# Plot one LPSD curve
# ============================================================

def plot_lpsd(
        ax,
        data_v_measured,
        fs,
        label,
        color=None,
        nfft=NFFT
):
    f, lpsd_g, nperseg = calculate_lpsd(
        data_v_measured,
        fs,
        nfft
    )

    mask = (
        (f > 0.1) &
        (f <= fs / 2)
    )

    ax.loglog(
        f[mask],
        lpsd_g[mask],
        label=label,
        color=color,
        linewidth=1.2,
        alpha=0.8
    )

    return {
        "nfft_requested": nfft,
        "nfft_actual": nperseg,
        "df": fs / nperseg,
        "duration": len(data_v_measured) / fs
    }


# ============================================================
# Separate LPSD figure
# ============================================================

def plot_lpsd_only(all_ch, folder):
    fig, ax = plt.subplots(figsize=(12, 7))

    colors = plt.cm.tab10(
        np.linspace(0, 1, len(all_ch))
    )

    plot_params = []

    for i, ch in enumerate(all_ch):

        params = plot_lpsd(
            ax,
            ch["data_v_measured"],
            ch["fs"],
            label=ch["legend"],
            color=colors[i]
        )

        params["legend"] = ch["legend"]
        params["file"] = ch["fname"]
        params["fs"] = ch["fs"]

        plot_params.append(params)

    ax.set_xlabel(
        "Frequency [Hz]",
        fontsize=11
    )

    ax.set_ylabel(
        "LPSD [g/√Hz]",
        fontsize=11
    )

    ax.set_title(
        "Linear Power Spectral Density"
    )

    ax.legend(
        loc="upper right",
        fontsize=8
    )

    ax.grid(
        True,
        alpha=0.3,
        which="both"
    )

    max_frequency = min(
        ch["fs"] / 2
        for ch in all_ch
    )

    ax.set_xlim(
        0.5,
        max_frequency
    )

    plt.tight_layout()

    save_path = os.path.join(
        folder,
        f"LPSD_Only_{SENS_MV_G}mVg_"
        f"gain{GAIN}_gUnits.png"
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    print(f"\nLPSD figure saved:")
    print(save_path)

    print("\n" + "=" * 60)
    print("LPSD Analysis Parameters")
    print("=" * 60)

    for p in plot_params:

        print(f"\nFile: {p['file']}")
        print(f"  Legend: {p['legend']}")
        print(f"  Fs: {p['fs']:.3f} Hz")
        print(f"  Duration: {p['duration']:.3f} s")
        print(f"  NFFT: {p['nfft_actual']:,}")
        print(f"  df: {p['df']:.6f} Hz")

    return fig, ax


# ============================================================
# Main
# ============================================================

def main():

    folder = select_folder()

    if not folder:
        return

    # Find TXT files
    files = sorted(
        glob.glob(os.path.join(folder, "*.txt")) +
        glob.glob(os.path.join(folder, "*.TXT"))
    )

    if not files:
        print("No TXT files found.")
        return

    print(f"\nFound {len(files)} TXT files")
    print(f"Sensor sensitivity: {SENS_MV_G} mV/g")
    print(f"Amplifier gain: {GAIN}")
    print(f"Total sensitivity: {SENS_TOTAL_V_G:.3f} V/g")
    print("=" * 60)

    # --------------------------------------------------------
    # Read all files
    # --------------------------------------------------------

    all_ch = []

    for filepath in files:

        size_mb = os.path.getsize(filepath) / 1024 / 1024

        print(
            f"\nReading: "
            f"{os.path.basename(filepath)} "
            f"({size_mb:.2f} MB)"
        )

        t0 = time.time()

        try:
            result = process_txt(filepath)
            all_ch.append(result)

        except Exception as e:
            print(f"    Failed: {e}")
            continue

        print(
            f"    Processing time: "
            f"{time.time() - t0:.3f} s"
        )

    if not all_ch:
        print("No valid data.")
        return

    # ========================================================
    # Combined figure
    # ========================================================

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(14, 10)
    )

    colors = plt.cm.tab10(
        np.linspace(0, 1, len(all_ch))
    )

    plot_params = []

    for i, ch in enumerate(all_ch):

        color = colors[i]
        label = ch["legend"]

        fs = ch["fs"]

        # ----------------------------------------------------
        # Time domain
        # ----------------------------------------------------

        n_pts = min(
            int(TIME_DISPLAY * fs),
            len(ch["data_v_sensor"])
        )

        # Start time at zero
        t = (
            ch["time_s"][:n_pts] -
            ch["time_s"][0]
        )

        axes[0].plot(
            t,
            ch["data_v_sensor"][:n_pts] * 1e3,
            color=color,
            label=label,
            linewidth=0.8,
            alpha=0.7
        )

        # ----------------------------------------------------
        # LPSD
        # ----------------------------------------------------

        params = plot_lpsd(
            axes[1],
            ch["data_v_measured"],
            fs,
            label=label,
            color=color
        )

        params["legend"] = label
        params["file"] = ch["fname"]
        params["fs"] = fs

        plot_params.append(params)

    # ========================================================
    # Time-domain settings
    # ========================================================

    axes[0].set_xlabel(
        "Time [s]"
    )

    axes[0].set_ylabel(
        "Sensor Voltage [mV] (Gain Removed)"
    )

    axes[0].set_title(
        "Time Domain"
    )

    axes[0].legend(
        loc="upper right",
        fontsize=8
    )

    axes[0].grid(
        True,
        alpha=0.3
    )

    # ========================================================
    # LPSD settings
    # ========================================================

    axes[1].set_xlabel(
        "Frequency [Hz]"
    )

    axes[1].set_ylabel(
        "LPSD [g/√Hz]"
    )

    axes[1].set_title(
        "Linear Power Spectral Density"
    )

    axes[1].legend(
        loc="upper right",
        fontsize=8
    )

    axes[1].grid(
        True,
        alpha=0.3,
        which="both"
    )

    max_frequency = min(
        ch["fs"] / 2
        for ch in all_ch
    )

    axes[1].set_xlim(
        0.5,
        max_frequency
    )

    plt.tight_layout()

    # ========================================================
    # Save combined figure
    # ========================================================

    save_path = os.path.join(
        folder,
        f"LPSD_{SENS_MV_G}mVg_"
        f"gain{GAIN}_gUnits_sensorV.png"
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    print(f"\nCombined figure saved:")
    print(save_path)

    # ========================================================
    # Separate LPSD figure
    # ========================================================

    plot_lpsd_only(
        all_ch,
        folder
    )

    # ========================================================
    # Summary
    # ========================================================

    print("\n" + "=" * 60)
    print("Frequency Analysis Summary")
    print("=" * 60)

    for p in plot_params:

        print(f"\nFile: {p['file']}")
        print(f"  Legend: {p['legend']}")
        print(f"  Fs: {p['fs']:.3f} Hz")
        print(f"  Duration: {p['duration']:.3f} s")
        print(f"  NFFT: {p['nfft_actual']:,}")
        print(f"  df: {p['df']:.6f} Hz")

    plt.show()


if __name__ == "__main__":
    main()
