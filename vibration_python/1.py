#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI-based TDMS slow thermal component extraction for NTD bolometer pulses.

Key features:
- Tkinter dialog to select one or multiple TDMS files
- Explicit matplotlib Agg backend (avoids Windows TkAgg deadlock)
- Baseline subtraction
- Peak finding
- Late-tail single exponential fit (thermal slow component)
- Tail quality metrics (R2, chi2)
- Save diagnostic PNG plots

Physics motivation:
- Particle deposition events show a stable exponential thermal tail
- Vibration/microphonic events typically deviate from this behavior
"""

# ============================================================
# !!! CRITICAL FIX !!!
# Must be before importing matplotlib.pyplot
# ============================================================
import matplotlib
matplotlib.use("Agg")

# ============================================================
# Standard imports
# ============================================================
import os
import numpy as np
import matplotlib.pyplot as plt

from nptdms import TdmsFile
from scipy.optimize import curve_fit
from scipy.stats import linregress

# GUI
import tkinter as tk
from tkinter import filedialog, messagebox


# ============================================================
# Model: single exponential (slow thermal component)
# ============================================================
def exp1(t, A, tau):
    return A * np.exp(-t / tau)


# ============================================================
# TDMS channel detection
# ============================================================
def detect_time_voltage_channels(tdms):
    """
    Heuristically detect time and voltage channels from TDMS.
    Assumes:
      - time channel is mostly increasing
      - voltage channel has pulse-like structure
    """
    channels = []
    for g in tdms.groups():
        for ch in g.channels():
            arr = np.asarray(ch[:])
            if arr.ndim == 1 and arr.size > 20:
                channels.append((g.name, ch.name, arr))

    if len(channels) < 2:
        raise RuntimeError("TDMS does not contain enough 1D channels")

    # ---- find time channel ----
    scores = []
    for g, n, arr in channels:
        diff = np.diff(arr)
        inc_ratio = np.mean(diff > 0)
        score = inc_ratio + 0.1 * np.var(arr)
        scores.append(((g, n, arr), score))

    scores.sort(key=lambda x: x[1], reverse=True)
    time_arr = scores[0][0][2]

    # ---- find voltage channel ----
    best = None
    best_score = -np.inf
    for g, n, arr in channels:
        if arr.size != time_arr.size:
            continue
        x = arr - np.median(arr)
        rms = np.sqrt(np.mean(x**2)) + 1e-12
        score = np.max(np.abs(x)) / rms
        if score > best_score:
            best_score = score
            best = arr

    if best is None:
        raise RuntimeError("Failed to identify voltage channel")

    return time_arr, best


# ============================================================
# Core analysis: extract slow component
# ============================================================
def analyze_pulse(time, voltage,
                  baseline_frac=0.2,
                  tail_start_offset=0.002,
                  tail_end_margin=0.001,
                  min_positive_points=50):

    time = np.asarray(time)
    v = np.asarray(voltage)

    # Ensure increasing time
    if np.any(np.diff(time) <= 0):
        idx = np.argsort(time)
        time = time[idx]
        v = v[idx]

    # ---- baseline ----
    t0, t1 = time[0], time[-1]
    bl_mask = time < (t0 + baseline_frac * (t1 - t0))
    baseline = np.mean(v[bl_mask])
    v_bl = v - baseline

    # ---- peak ----
    peak_idx = np.argmax(v_bl)
    t_peak = time[peak_idx]
    A_peak = v_bl[peak_idx]

    # ---- tail window ----
    tail_start = t_peak + tail_start_offset
    tail_end = time[-1] - tail_end_margin

    if tail_end <= tail_start:
        raise RuntimeError("Invalid tail window")

    mask = (time >= tail_start) & (time <= tail_end)
    t_tail = time[mask] - tail_start
    v_tail = v_bl[mask]

    pos = v_tail > 0
    t_fit = t_tail[pos]
    v_fit = v_tail[pos]

    if t_fit.size < min_positive_points:
        raise RuntimeError("Not enough positive tail points for fit")

    # ---- exponential fit ----
    A0 = v_fit[0]
    tau0 = 0.2 * (t_fit[-1] - t_fit[0])

    popt, _ = curve_fit(
        exp1,
        t_fit,
        v_fit,
        p0=[A0, tau0],
        bounds=([0.0, 1e-9], [np.inf, np.inf]),
        maxfev=20000
    )

    A_s, tau_s = popt

    # ---- tail quality ----
    logv = np.log(v_fit)
    slope, intercept, r, _, _ = linregress(t_fit, logv)
    R2_tail = r**2

    pred = exp1(t_fit, A_s, tau_s)
    resid = v_fit - pred
    chi2_tail = np.mean((resid / (np.std(v_fit) + 1e-12))**2)

    # ---- reconstruct slow component ----
    slow = np.zeros_like(v_bl)
    t_full = time - tail_start
    valid = t_full >= 0
    slow[valid] = exp1(t_full[valid], A_s, tau_s)

    metrics = {
        "baseline": baseline,
        "t_peak": t_peak,
        "A_peak": A_peak,
        "A_s": A_s,
        "tau_s": tau_s,
        "R2_tail": R2_tail,
        "chi2_tail": chi2_tail,
        "tail_start": tail_start
    }

    return metrics, time, v_bl, slow


# ============================================================
# Plot and save
# ============================================================
def save_plot(out_png, time, signal, slow, metrics):
    plt.figure(figsize=(10, 6))
    plt.plot(time, signal, label="Signal (baseline subtracted)")
    plt.plot(time, slow, "--", label="Slow thermal component")
    plt.axvline(metrics["tail_start"], linestyle=":", color="k")
    plt.xlabel("Time")
    plt.ylabel("Voltage")
    plt.title(
        f"tau_s = {metrics['tau_s']:.4e} s, "
        f"R2_tail = {metrics['R2_tail']:.4f}"
    )
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


# ============================================================
# Main (GUI)
# ============================================================
def main():
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        "Select TDMS file(s)",
        "Select one or more TDMS files\n"
        "containing time & voltage channels (NTD readout)."
    )

    files = filedialog.askopenfilenames(
        title="Select TDMS file(s)",
        filetypes=[("TDMS files", "*.tdms")]
    )

    if not files:
        messagebox.showwarning("No file selected", "No TDMS file selected.")
        return

    outdir = "out_slow"
    os.makedirs(outdir, exist_ok=True)

    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        print(f"\nProcessing {name} ...")

        try:
            tdms = TdmsFile.read(fp)
            time, volt = detect_time_voltage_channels(tdms)

            metrics, t, v_bl, slow = analyze_pulse(time, volt)

            out_png = os.path.join(outdir, f"{name}_slow.png")
            save_plot(out_png, t, v_bl, slow, metrics)

            print(
                f"  tau_s = {metrics['tau_s']:.4e} s, "
                f"R2_tail = {metrics['R2_tail']:.4f}"
            )

        except Exception as e:
            print(f"  ERROR: {e}")

    messagebox.showinfo(
        "Done",
        f"Analysis finished.\nResults saved in:\n{outdir}"
    )


if __name__ == "__main__":
    main()
