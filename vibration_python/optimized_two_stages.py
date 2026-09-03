# -*- coding: utf-8 -*-
"""
TU0 two-stage extension-spring optimizer + measured-vibration isolation simulation

Features
--------
1) Integer wire diameter d and integer outside diameter OD.
2) Each end Hook axial length ~= outside diameter OD.
3) N_body = physical body-coil count.
4) N_eff  = equivalent active coils used for spring-rate calculation:
       N_eff = N_body + 1
   where the two full hooks together are approximated as +1 equivalent coil.
5) Two-stage spring optimization.
6) File-selection dialog for measured CSV/TXT vibration data.
7) FFT -> complex 2-DOF transfer function -> IFFT.
8) Plots:
   - theoretical transmissibility
   - measured time-domain before/after isolation
   - measured spectrum before/after isolation
   - measured PSD before/after isolation
9) Program starts with the file-selection dialog.
10) All results are saved beside the selected measured CSV/TXT file.

CSV defaults
------------
- Skip first 4 rows
- Column 1 = time
- Column 2 = measured voltage / vibration signal

Important
---------
A passive spring isolator cannot isolate true 0 Hz (DC/static motion).
The response below 100 Hz is therefore evaluated from a small positive frequency.
"""

import math
import csv
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 1. USER INPUTS
# ============================================================

g = 9.80665

# TU0 preliminary material values.
# Replace with actual mill certificate / spring-manufacturer data for production.
G_MPa = 44_000.0
UTS_MPa = 345.0

BODY_TORSION_ALLOW_RATIO = 0.35
HOOK_TORSION_ALLOW_RATIO = 0.30
HOOK_BENDING_ALLOW_RATIO = 0.55

BODY_TORSION_ALLOW_MPa = BODY_TORSION_ALLOW_RATIO * UTS_MPa
HOOK_TORSION_ALLOW_MPa = HOOK_TORSION_ALLOW_RATIO * UTS_MPa
HOOK_BENDING_ALLOW_MPa = HOOK_BENDING_ALLOW_RATIO * UTS_MPa

PROOF_LOAD_FACTOR = 1.50
MAX_ALLOWABLE_UTILIZATION = 0.85

# Masses
M1_kg = 90.0
M2_kg = 0.8
N_STAGE1_SPRINGS = 3

# Worst-case Stage-1 load sharing
STAGE1_LOAD_SHARE_FACTOR = 1.10

# Damping
ZETA_STAGE1 = 0.03
ZETA_STAGE2 = 0.03

# Frequency range of interest.
# 0 Hz itself cannot be isolated; numerical curves start above zero.
ISO_EVAL_MIN_Hz = 0.05
ISO_EVAL_MAX_Hz = 100.0

# Geometry
STAGE1_MAX_EQUILIBRIUM_LENGTH_mm = 300.0
STAGE_LENGTH_CLEARANCE_mm = 0.0

C_MIN = 4.0
C_MAX = 12.0

# Hook flexibility:
HOOK_EQUIVALENT_COILS_TOTAL = 1.0

# Requested Hook axial-length approximation:
HOOK_LENGTH_TO_OD_RATIO = 1.0

# Initial tension
INITIAL_TENSION_COEFF = 0.40
MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL = 0.80

# Integer design spaces
STAGE1_WIRE_DIAMETERS_mm = range(5, 13)
STAGE1_OUTSIDE_DIAMETERS_mm = range(30, 121)
STAGE1_BODY_COILS = range(4, 181)

STAGE2_WIRE_DIAMETERS_mm = range(1, 6)
STAGE2_OUTSIDE_DIAMETERS_mm = range(6, 61)
STAGE2_BODY_COILS = range(10, 321)

# CSV input format
CSV_SKIP_ROWS = 4
CSV_TIME_COLUMN = 0
CSV_SIGNAL_COLUMN = 1

# "auto", "s", "ms", "us"
TIME_UNIT = "auto"

OUTPUT_DIR_NAME = "TU0_isolation_results"


# ============================================================
# 2. DATA STRUCTURE
# ============================================================

@dataclass
class SpringDesign:
    stage: str
    number_parallel: int

    d_mm: int
    OD_mm: int
    D_mm: float
    ID_mm: float
    spring_index_C: float

    N_body: int
    N_eff: float

    k_N_per_mm: float
    initial_tension_N: float

    body_length_mm: float
    hook_length_each_mm: float
    free_length_mm: float
    extension_at_equilibrium_mm: float
    equilibrium_length_mm: float

    local_natural_frequency_Hz: float

    nominal_force_per_spring_N: float
    proof_force_per_spring_N: float

    max_rated_force_per_spring_N: float
    max_supported_mass_kg: float

    utilization_at_proof: float


# ============================================================
# 3. SPRING FORMULAS
# ============================================================

def wahl_factor(C):
    if C <= 1.0:
        return float("inf")
    return (4.0 * C - 1.0) / (4.0 * C - 4.0) + 0.615 / C


def spring_rate_N_per_mm(d_mm, D_mm, N_eff):
    return G_MPa * d_mm**4 / (8.0 * D_mm**3 * N_eff)


def body_shear_MPa(F_N, d_mm, D_mm):
    C = D_mm / d_mm
    return (
        wahl_factor(C)
        * 8.0 * F_N * D_mm
        / (math.pi * d_mm**3)
    )


def hook_bending_A_MPa(F_N, d_mm, D_mm):
    C1 = D_mm / d_mm
    if C1 <= 1.0:
        return float("inf")

    K_A = (
        (4.0 * C1**2 - C1 - 1.0)
        / (4.0 * C1 * (C1 - 1.0))
    )

    return F_N * (
        K_A * 16.0 * D_mm / (math.pi * d_mm**3)
        + 4.0 / (math.pi * d_mm**2)
    )


def hook_torsion_B_MPa(F_N, d_mm, D_mm):
    C2 = 4.0
    K_B = (4.0 * C2 - 1.0) / (4.0 * C2 - 4.0)

    return (
        K_B
        * 8.0 * F_N * D_mm
        / (math.pi * d_mm**3)
    )


def initial_tension_N(d_mm, D_mm, C):
    tau_i = INITIAL_TENSION_COEFF * UTS_MPa / C
    return math.pi * d_mm**3 * tau_i / (8.0 * D_mm)


def extension_from_force_mm(F_N, Fi_N, k_N_per_mm):
    if F_N <= Fi_N:
        return 0.0
    return (F_N - Fi_N) / k_N_per_mm


def stress_utilization(F_N, d_mm, D_mm):
    u_body = body_shear_MPa(F_N, d_mm, D_mm) / BODY_TORSION_ALLOW_MPa
    u_hook_A = hook_bending_A_MPa(F_N, d_mm, D_mm) / HOOK_BENDING_ALLOW_MPa
    u_hook_B = hook_torsion_B_MPa(F_N, d_mm, D_mm) / HOOK_TORSION_ALLOW_MPa
    return max(u_body, u_hook_A, u_hook_B)


def max_rated_static_force_per_spring_N(d_mm, D_mm):
    body_per_N = body_shear_MPa(1.0, d_mm, D_mm)
    hookA_per_N = hook_bending_A_MPa(1.0, d_mm, D_mm)
    hookB_per_N = hook_torsion_B_MPa(1.0, d_mm, D_mm)

    max_proof_force = min(
        MAX_ALLOWABLE_UTILIZATION * BODY_TORSION_ALLOW_MPa / body_per_N,
        MAX_ALLOWABLE_UTILIZATION * HOOK_BENDING_ALLOW_MPa / hookA_per_N,
        MAX_ALLOWABLE_UTILIZATION * HOOK_TORSION_ALLOW_MPa / hookB_per_N,
    )

    return max_proof_force / PROOF_LOAD_FACTOR


# ============================================================
# 4. TWO-STAGE VIBRATION MODEL
# ============================================================

def two_dof_transfer_complex(stage1, stage2, frequencies_Hz):
    """
    Base displacement Y -> absolute displacement X1, X2.

    Returns
    -------
    H1 = X1/Y
    H2 = X2/Y
    """
    f = np.asarray(frequencies_Hz, dtype=float)

    m1 = M1_kg
    m2 = M2_kg

    k1 = stage1.number_parallel * stage1.k_N_per_mm * 1000.0
    k2 = stage2.k_N_per_mm * 1000.0

    c1 = 2.0 * ZETA_STAGE1 * math.sqrt(k1 * m1)
    c2 = 2.0 * ZETA_STAGE2 * math.sqrt(k2 * m2)

    M = np.array([
        [m1, 0.0],
        [0.0, m2],
    ], dtype=float)

    K = np.array([
        [k1 + k2, -k2],
        [-k2,       k2],
    ], dtype=float)

    C = np.array([
        [c1 + c2, -c2],
        [-c2,       c2],
    ], dtype=float)

    H1 = np.zeros(len(f), dtype=complex)
    H2 = np.zeros(len(f), dtype=complex)

    for i, fi in enumerate(f):
        w = 2.0 * math.pi * fi

        if abs(w) < 1e-15:
            H1[i] = 1.0 + 0j
            H2[i] = 1.0 + 0j
            continue

        A = -w*w*M + 1j*w*C + K
        B = np.array([k1 + 1j*w*c1, 0.0], dtype=complex)

        X = np.linalg.solve(A, B)
        H1[i] = X[0]
        H2[i] = X[1]

    return H1, H2


def two_dof_undamped_natural_frequencies_Hz(stage1, stage2):
    m1 = M1_kg
    m2 = M2_kg

    k1 = stage1.number_parallel * stage1.k_N_per_mm * 1000.0
    k2 = stage2.k_N_per_mm * 1000.0

    M = np.array([
        [m1, 0.0],
        [0.0, m2],
    ], dtype=float)

    K = np.array([
        [k1 + k2, -k2],
        [-k2,       k2],
    ], dtype=float)

    eigvals = np.linalg.eigvals(np.linalg.solve(M, K))
    eigvals = np.maximum(np.real(eigvals), 0.0)

    return np.sort(np.sqrt(eigvals) / (2.0 * math.pi))


# ============================================================
# 5. CANDIDATE EVALUATION
# ============================================================

def evaluate_candidate(stage, d_mm, OD_mm, N_body):
    d_mm = int(d_mm)
    OD_mm = int(OD_mm)
    N_body = int(N_body)

    D_mm = OD_mm - d_mm
    ID_mm = OD_mm - 2.0 * d_mm

    if D_mm <= 0 or ID_mm <= 0:
        return None

    C = D_mm / d_mm
    if not (C_MIN <= C <= C_MAX):
        return None

    # N_body = actual body turns.
    # N_eff = stiffness-equivalent turns, including hook flexibility.
    N_eff = N_body + HOOK_EQUIVALENT_COILS_TOTAL

    k = spring_rate_N_per_mm(d_mm, D_mm, N_eff)

    if stage == "Stage 1":
        number_parallel = N_STAGE1_SPRINGS
        total_static_force = (M1_kg + M2_kg) * g

        F_nom = (
            total_static_force
            / number_parallel
            * STAGE1_LOAD_SHARE_FACTOR
        )

        modal_mass_kg = M1_kg + M2_kg

    elif stage == "Stage 2":
        number_parallel = 1
        F_nom = M2_kg * g
        modal_mass_kg = M2_kg

    else:
        raise ValueError("Unknown stage.")

    Fi = initial_tension_N(d_mm, D_mm, C)

    if Fi >= F_nom:
        return None

    if Fi / F_nom > MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL:
        return None

    F_proof = PROOF_LOAD_FACTOR * F_nom
    utilization = stress_utilization(F_proof, d_mm, D_mm)

    if utilization > MAX_ALLOWABLE_UTILIZATION:
        return None

    x_eq = extension_from_force_mm(F_nom, Fi, k)

    # Close-wound body length.
    L_body = N_body * d_mm

    # Requested approximation: each Hook length ~= OD.
    L_hook_each = HOOK_LENGTH_TO_OD_RATIO * OD_mm

    L_free = L_body + 2.0 * L_hook_each
    L_eq = L_free + x_eq

    k_total_N_per_m = number_parallel * k * 1000.0

    fn_local = (
        1.0
        / (2.0 * math.pi)
        * math.sqrt(k_total_N_per_m / modal_mass_kg)
    )

    F_rated_max = max_rated_static_force_per_spring_N(d_mm, D_mm)

    if stage == "Stage 1":
        max_supported_mass_kg = (
            F_rated_max * number_parallel
            / (STAGE1_LOAD_SHARE_FACTOR * g)
        )
    else:
        max_supported_mass_kg = F_rated_max / g

    return SpringDesign(
        stage=stage,
        number_parallel=number_parallel,

        d_mm=d_mm,
        OD_mm=OD_mm,
        D_mm=float(D_mm),
        ID_mm=float(ID_mm),
        spring_index_C=float(C),

        N_body=N_body,
        N_eff=float(N_eff),

        k_N_per_mm=float(k),
        initial_tension_N=float(Fi),

        body_length_mm=float(L_body),
        hook_length_each_mm=float(L_hook_each),
        free_length_mm=float(L_free),
        extension_at_equilibrium_mm=float(x_eq),
        equilibrium_length_mm=float(L_eq),

        local_natural_frequency_Hz=float(fn_local),

        nominal_force_per_spring_N=float(F_nom),
        proof_force_per_spring_N=float(F_proof),

        max_rated_force_per_spring_N=float(F_rated_max),
        max_supported_mass_kg=float(max_supported_mass_kg),

        utilization_at_proof=float(utilization),
    )


# ============================================================
# 6. OPTIMIZATION
# ============================================================

def generate_stage1_candidates():
    feasible = []

    for d in STAGE1_WIRE_DIAMETERS_mm:
        for OD in STAGE1_OUTSIDE_DIAMETERS_mm:
            for N_body in STAGE1_BODY_COILS:
                s = evaluate_candidate("Stage 1", d, OD, N_body)

                if s is None:
                    continue

                if s.equilibrium_length_mm > STAGE1_MAX_EQUILIBRIUM_LENGTH_mm:
                    continue

                feasible.append(s)

    if not feasible:
        raise RuntimeError("No feasible Stage-1 design.")

    return feasible


def generate_stage2_candidates():
    feasible = []

    for d in STAGE2_WIRE_DIAMETERS_mm:
        for OD in STAGE2_OUTSIDE_DIAMETERS_mm:
            for N_body in STAGE2_BODY_COILS:
                s = evaluate_candidate("Stage 2", d, OD, N_body)

                if s is not None:
                    feasible.append(s)

    if not feasible:
        raise RuntimeError("No feasible Stage-2 design.")

    return feasible


def optimize_two_stage():
    """
    Priority:
    1) Lowest Stage-2 local natural frequency.
    2) Require L2_equilibrium < L1_equilibrium.
    3) Then lowest Stage-1 local natural frequency.
    4) Shorter geometry as tie-breaker.
    """
    stage1_candidates = generate_stage1_candidates()
    stage2_candidates = generate_stage2_candidates()

    max_L1 = max(s.equilibrium_length_mm for s in stage1_candidates)

    compatible_stage2 = [
        s for s in stage2_candidates
        if s.equilibrium_length_mm + STAGE_LENGTH_CLEARANCE_mm < max_L1
    ]

    if not compatible_stage2:
        raise RuntimeError("No compatible Stage-2 design.")

    best_fn2 = min(s.local_natural_frequency_Hz for s in compatible_stage2)
    eps2 = max(1e-12, abs(best_fn2) * 1e-10)

    best_stage2_group = [
        s for s in compatible_stage2
        if abs(s.local_natural_frequency_Hz - best_fn2) <= eps2
    ]

    stage2 = min(
        best_stage2_group,
        key=lambda s: (
            s.equilibrium_length_mm,
            -s.max_supported_mass_kg,
            s.OD_mm,
            s.d_mm,
            s.N_body,
        ),
    )

    compatible_stage1 = [
        s for s in stage1_candidates
        if stage2.equilibrium_length_mm + STAGE_LENGTH_CLEARANCE_mm
        < s.equilibrium_length_mm
    ]

    if not compatible_stage1:
        raise RuntimeError("Selected Stage-2 has no compatible Stage-1.")

    stage1 = min(
        compatible_stage1,
        key=lambda s: (
            s.local_natural_frequency_Hz,
            s.equilibrium_length_mm,
            -s.max_supported_mass_kg,
            s.OD_mm,
            s.d_mm,
            s.N_body,
        ),
    )

    return stage1, stage2


# ============================================================
# 7. COMPACT DESIGN OUTPUT
# ============================================================

def print_compact_design(s):
    print("\n" + "=" * 64)
    print(s.stage)
    print("=" * 64)

    print(f"Parallel springs           : {s.number_parallel}")
    print(f"Wire diameter d            : {s.d_mm:d} mm")
    print(f"Outside diameter OD        : {s.OD_mm:d} mm")
    print(f"Mean diameter D            : {s.D_mm:.3f} mm")
    print(f"Inside diameter ID         : {s.ID_mm:.3f} mm")
    print(f"N_body                     : {s.N_body:d}")
    print(f"N_eff                      : {s.N_eff:.3f}")
    print(f"Hook length / end          : {s.hook_length_each_mm:.3f} mm")
    print(f"Spring rate / spring       : {s.k_N_per_mm:.6f} N/mm")
    print(f"Initial tension / spring   : {s.initial_tension_N:.3f} N")
    print(f"Max rated force / spring   : {s.max_rated_force_per_spring_N:.3f} N")
    print(f"Max supported mass         : {s.max_supported_mass_kg:.3f} kg")
    print(f"Natural frequency          : {s.local_natural_frequency_Hz:.3f} Hz")
    print(f"Free length                : {s.free_length_mm:.3f} mm")
    print(f"Equilibrium length         : {s.equilibrium_length_mm:.3f} mm")


# ============================================================
# 8. FILE PICKER + CSV READER
# ============================================================

def pick_input_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title="Select vibration CSV / TXT file",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    return Path(path)


def decode_text_file_robust(path):
    data = Path(path).read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"

    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16"), "utf-16"

    encodings = [
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
        "cp936",
        "utf-16-le",
        "utf-16-be",
    ]

    for enc in encodings:
        try:
            text = data.decode(enc)
            return text.replace("\x00", ""), enc
        except UnicodeDecodeError:
            pass

    return data.decode("latin-1"), "latin-1"


def detect_delimiter(lines):
    candidates = [",", "\t", ";"]
    best_delimiter = ","
    best_score = -1

    for delimiter in candidates:
        score = 0

        for line in lines[:50]:
            parts = line.strip().split(delimiter)

            if len(parts) >= 2:
                try:
                    float(parts[0].strip().strip('"'))
                    float(parts[1].strip().strip('"'))
                    score += 3
                except Exception:
                    score += 1

        if score > best_score:
            best_score = score
            best_delimiter = delimiter

    return best_delimiter


def convert_time_to_seconds(t_raw):
    t_raw = np.asarray(t_raw, dtype=float)

    if TIME_UNIT == "s":
        return t_raw

    if TIME_UNIT == "ms":
        return t_raw * 1e-3

    if TIME_UNIT == "us":
        return t_raw * 1e-6

    if TIME_UNIT != "auto":
        raise ValueError("TIME_UNIT must be auto, s, ms or us.")

    dt = np.median(np.diff(t_raw))

    # Heuristic for common instrument exports.
    if dt > 100.0:
        scale = 1e-6
        unit_name = "us"
    elif dt > 0.1:
        scale = 1e-3
        unit_name = "ms"
    else:
        scale = 1.0
        unit_name = "s"

    print(f"Auto-detected time unit: {unit_name}")
    return t_raw * scale


def load_time_signal(path):
    text, encoding = decode_text_file_robust(path)
    lines = text.splitlines()

    if len(lines) <= CSV_SKIP_ROWS:
        raise ValueError("Input file has too few rows.")

    data_lines = lines[CSV_SKIP_ROWS:]
    delimiter = detect_delimiter(data_lines)

    parsed = []

    for line in data_lines:
        line = line.strip()

        if not line:
            continue

        try:
            row = next(csv.reader([line], delimiter=delimiter))
        except Exception:
            continue

        required = max(CSV_TIME_COLUMN, CSV_SIGNAL_COLUMN)

        if len(row) <= required:
            continue

        t_field = row[CSV_TIME_COLUMN].strip().strip('"')
        x_field = row[CSV_SIGNAL_COLUMN].strip().strip('"')

        if delimiter == ";":
            t_field = t_field.replace(",", ".")
            x_field = x_field.replace(",", ".")

        try:
            t = float(t_field)
            x = float(x_field)
        except ValueError:
            continue

        if np.isfinite(t) and np.isfinite(x):
            parsed.append((t, x))

    if len(parsed) < 16:
        raise ValueError("Too few valid numeric samples found.")

    arr = np.asarray(parsed, dtype=float)

    t_raw = arr[:, 0]
    x = arr[:, 1]

    order = np.argsort(t_raw)
    t_raw = t_raw[order]
    x = x[order]

    keep = np.concatenate([[True], np.diff(t_raw) > 0])
    t_raw = t_raw[keep]
    x = x[keep]

    t = convert_time_to_seconds(t_raw)

    dt = np.diff(t)
    dt_med = float(np.median(dt))

    if dt_med <= 0:
        raise ValueError("Invalid time column.")

    fs = 1.0 / dt_med
    rel_jitter = float(np.std(dt) / dt_med)

    print(f"Detected encoding           : {encoding}")
    print(f"Detected delimiter          : {repr(delimiter)}")
    print(f"Valid samples               : {len(t)}")
    print(f"Sampling rate               : {fs:.3f} Hz")

    # FFT requires uniform sampling.
    if rel_jitter > 1e-3:
        t_uniform = np.linspace(t[0], t[-1], len(t))
        x = np.interp(t_uniform, t, x)
        t = t_uniform
        dt_med = float(np.median(np.diff(t)))
        fs = 1.0 / dt_med
        print("Time data resampled to uniform grid.")

    return t, x, fs


# ============================================================
# 9. MEASURED SIGNAL PROCESSING
# ============================================================

def process_measured_signal(stage1, stage2, t, x_in):
    """
    Treat the selected measured signal as proportional to base motion.
    Because the system is linear, the same transfer ratio applies to the
    measured signal amplitude.

    DC is retained because H(0)=1.
    """
    n = len(x_in)
    dt = float(np.median(np.diff(t)))

    freq = np.fft.rfftfreq(n, d=dt)
    X = np.fft.rfft(x_in)

    H1, H2 = two_dof_transfer_complex(stage1, stage2, freq)

    X_stage1 = X * H1
    X_stage2 = X * H2

    x_stage1 = np.fft.irfft(X_stage1, n=n)
    x_stage2 = np.fft.irfft(X_stage2, n=n)

    return freq, X, H1, H2, x_stage1, x_stage2


# ============================================================
# 10. PLOTS
# ============================================================

def save_theoretical_transmissibility(stage1, stage2, output_dir):
    f = np.logspace(
        math.log10(ISO_EVAL_MIN_Hz),
        math.log10(ISO_EVAL_MAX_Hz),
        1600,
    )

    H1, H2 = two_dof_transfer_complex(stage1, stage2, f)

    path = output_dir / "01_theoretical_transmissibility.png"

    plt.figure(figsize=(9, 5.5))
    plt.loglog(f, np.abs(H1), label="Stage 1 / Base")
    plt.loglog(f, np.abs(H2), label="Stage 2 / Base")
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Transmissibility |X/Y|")
    plt.title("Two-Stage Isolation Transmissibility")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def save_measured_time_plot(t, x_in, x_stage1, x_stage2, output_dir):
    path = output_dir / "02_measured_time_before_after.png"

    plt.figure(figsize=(10, 5.5))
    plt.plot(t, x_in, linewidth=0.9, label="Input / Base")
    plt.plot(t, x_stage1, linewidth=0.9, label="After Stage 1")
    plt.plot(t, x_stage2, linewidth=0.9, label="After Stage 2")
    plt.xlabel("Time (s)")
    plt.ylabel("Signal amplitude")
    plt.title("Measured Signal Before and After Isolation")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def single_sided_amplitude(X, n):
    amp = np.abs(X) / n

    if n > 1:
        amp[1:-1] *= 2.0

    return amp


def save_measured_spectrum_plot(
    freq,
    X,
    H1,
    H2,
    n,
    output_dir,
):
    Xin = single_sided_amplitude(X.copy(), n)
    X1 = single_sided_amplitude((X * H1).copy(), n)
    X2 = single_sided_amplitude((X * H2).copy(), n)

    mask = (freq > 0.0) & (freq <= ISO_EVAL_MAX_Hz)

    path = output_dir / "03_measured_spectrum_before_after.png"

    plt.figure(figsize=(9, 5.5))
    plt.semilogy(freq[mask], np.maximum(Xin[mask], 1e-15), label="Input / Base")
    plt.semilogy(freq[mask], np.maximum(X1[mask], 1e-15), label="After Stage 1")
    plt.semilogy(freq[mask], np.maximum(X2[mask], 1e-15), label="After Stage 2")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.title("Measured Spectrum Before and After Isolation")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path



def save_measured_psd_plot(
    freq,
    X,
    H1,
    H2,
    n,
    fs,
    output_dir,
):
    """
    Save one-sided periodogram-style PSD comparison for the measured signal.

    The selected CSV signal is treated as the base-input signal. Because the
    system is linear:
        PSD_stage1 = |H1|^2 * PSD_input
        PSD_stage2 = |H2|^2 * PSD_input

    Units are signal_unit^2/Hz. If the input column is voltage, the PSD unit is
    V^2/Hz.
    """
    if n < 2 or fs <= 0:
        raise ValueError("Invalid sample count or sampling rate for PSD.")

    # One-sided PSD from the same FFT used for the time reconstruction.
    psd_in = (np.abs(X) ** 2) / (fs * n)

    # Double positive-frequency power except DC and Nyquist.
    if n % 2 == 0:
        if len(psd_in) > 2:
            psd_in[1:-1] *= 2.0
    else:
        if len(psd_in) > 1:
            psd_in[1:] *= 2.0

    psd_stage1 = psd_in * (np.abs(H1) ** 2)
    psd_stage2 = psd_in * (np.abs(H2) ** 2)

    mask = (freq > 0.0) & (freq <= ISO_EVAL_MAX_Hz)

    path = output_dir / "04_measured_PSD_before_after.png"

    plt.figure(figsize=(9, 5.5))
    plt.semilogy(
        freq[mask],
        np.maximum(psd_in[mask], 1e-30),
        label="Input / Base",
    )
    plt.semilogy(
        freq[mask],
        np.maximum(psd_stage1[mask], 1e-30),
        label="After Stage 1",
    )
    plt.semilogy(
        freq[mask],
        np.maximum(psd_stage2[mask], 1e-30),
        label="After Stage 2",
    )
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("PSD (signal unit$^2$/Hz)")
    plt.title("Measured PSD Before and After Isolation")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    # Also save the PSD flow data so it can be replotted in Origin/MATLAB/Excel.
    csv_path = output_dir / "measured_PSD_before_after.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Input_PSD",
            "After_Stage1_PSD",
            "After_Stage2_PSD",
        ])
        for row in zip(freq, psd_in, psd_stage1, psd_stage2):
            writer.writerow(row)

    return path, csv_path


def save_transfer_csv(stage1, stage2, output_dir):
    f = np.linspace(0.0, ISO_EVAL_MAX_Hz, 2001)
    H1, H2 = two_dof_transfer_complex(stage1, stage2, f)

    path = output_dir / "two_stage_transmissibility.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Stage1_Magnitude",
            "Stage1_dB",
            "Stage1_Phase_deg",
            "Stage2_Magnitude",
            "Stage2_dB",
            "Stage2_Phase_deg",
        ])

        for fi, h1, h2 in zip(f, H1, H2):
            m1 = abs(h1)
            m2 = abs(h2)

            writer.writerow([
                fi,
                m1,
                20.0 * math.log10(max(m1, 1e-300)),
                np.angle(h1, deg=True),
                m2,
                20.0 * math.log10(max(m2, 1e-300)),
                np.angle(h2, deg=True),
            ])

    return path


def save_processed_signal_csv(t, x_in, x_stage1, x_stage2, output_dir):
    path = output_dir / "measured_signal_before_after.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Time_s",
            "Input_Base",
            "After_Stage1",
            "After_Stage2",
        ])

        for row in zip(t, x_in, x_stage1, x_stage2):
            writer.writerow(row)

    return path


# ============================================================
# 11. MAIN
# ============================================================


def main():
    # --------------------------------------------------------
    # 1. SELECT MEASURED FILE FIRST
    # --------------------------------------------------------
    # The dialog appears immediately when the program starts.
    input_path = pick_input_file()

    if input_path is None:
        print("\nNo measured CSV/TXT file selected. Program terminated.")
        return

    print(f"\nSelected measured file: {input_path}")

    # Save everything next to the selected CSV/TXT, as in the previous workflow.
    output_dir = input_path.parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 2. READ MEASURED DATA FIRST
    # --------------------------------------------------------
    # This catches file/encoding/time-column problems before the long optimizer runs.
    try:
        t, x_in, fs = load_time_signal(input_path)
    except Exception as exc:
        try:
            messagebox.showerror("CSV/TXT reading error", str(exc))
        except Exception:
            pass
        raise

    # --------------------------------------------------------
    # 3. RUN TWO-STAGE SPRING OPTIMIZATION
    # --------------------------------------------------------
    print("\nRunning TU0 two-stage spring optimization...")
    stage1, stage2 = optimize_two_stage()

    print_compact_design(stage1)
    print_compact_design(stage2)

    coupled_modes = two_dof_undamped_natural_frequencies_Hz(stage1, stage2)
    print(
        "\nCoupled natural frequencies : "
        + ", ".join(f"{x:.3f} Hz" for x in coupled_modes)
    )

    # --------------------------------------------------------
    # 4. THEORETICAL TRANSFER OUTPUT
    # --------------------------------------------------------
    p1 = save_theoretical_transmissibility(stage1, stage2, output_dir)
    transfer_csv = save_transfer_csv(stage1, stage2, output_dir)

    # --------------------------------------------------------
    # 5. APPLY COMPLEX 2-DOF RESPONSE TO THE MEASURED SIGNAL
    # --------------------------------------------------------
    try:
        freq, X, H1, H2, x_stage1, x_stage2 = process_measured_signal(
            stage1,
            stage2,
            t,
            x_in,
        )

        p2 = save_measured_time_plot(
            t,
            x_in,
            x_stage1,
            x_stage2,
            output_dir,
        )

        p3 = save_measured_spectrum_plot(
            freq,
            X,
            H1,
            H2,
            len(x_in),
            output_dir,
        )

        p4, psd_csv = save_measured_psd_plot(
            freq,
            X,
            H1,
            H2,
            len(x_in),
            fs,
            output_dir,
        )

        processed_csv = save_processed_signal_csv(
            t,
            x_in,
            x_stage1,
            x_stage2,
            output_dir,
        )

        # --------------------------------------------------------
        # 6. PRINT ALL SAVED OUTPUTS
        # --------------------------------------------------------
        print("\n" + "=" * 72)
        print("OUTPUT FILES")
        print("=" * 72)
        print(f"Output directory             : {output_dir}")
        print(f"Theoretical transmissibility : {p1}")
        print(f"Measured time comparison     : {p2}")
        print(f"Measured spectrum comparison : {p3}")
        print(f"Measured PSD comparison      : {p4}")
        print(f"Transfer-function CSV        : {transfer_csv}")
        print(f"Processed time-series CSV    : {processed_csv}")
        print(f"Measured PSD data CSV        : {psd_csv}")

        # --------------------------------------------------------
        # 7. SHOW ALL FOUR SAVED FIGURES
        # --------------------------------------------------------
        # Keep the same save-first, show-after behavior so the files exist even
        # if the user closes the plotting windows.
        figure_paths = [
            (p1, (9, 5.5)),
            (p2, (10, 5.5)),
            (p3, (9, 5.5)),
            (p4, (9, 5.5)),
        ]

        for img_path, fig_size in figure_paths:
            img = plt.imread(img_path)
            plt.figure(figsize=fig_size)
            plt.imshow(img)
            plt.axis("off")
            plt.tight_layout()

    except Exception as exc:
        try:
            messagebox.showerror(
                "Processing error",
                str(exc),
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
