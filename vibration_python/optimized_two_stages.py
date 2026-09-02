# -*- coding: utf-8 -*-
"""
TU0 high-purity oxygen-free copper EXTENSION spring design + two-stage isolation
===============================================================================

System:
    Base -> Stage 1: three parallel extension springs -> 90 kg platform
         -> Stage 2: one extension spring -> 1 kg payload

This version fixes the main issues found in the previous code:
1) Uses Shigley-style static allowable ratios for NONFERROUS extension springs:
       spring body torsion : 0.35 Sut
       hook torsion        : 0.30 Sut
       hook bending        : 0.55 Sut
2) Stage-1 load includes downstream 1 kg payload.
3) Adds worst-case Stage-1 load-share factor.
4) Uses integer outside diameter (OD) as a direct search variable.
5) Separates body coils N_body and effective coils N_eff.
   For two full hooks, default hook flexibility is approximated as +1 equivalent coil.
6) Initial tension is NOT assumed to be a universal percentage of load.
   It is a user input / manufacturing requirement. Default is 0 N for conservative
   extension/length prediction.
7) Adds optional fatigue screening using a modified-Goodman style relation.
   Because real vibration force amplitude must come from measurement / specification,
   fatigue force amplitude is user-adjustable.
8) Retains 2-DOF base-excitation isolation model.
9) Adds CSV file picker:
       first 4 rows skipped
       column 1 = time
       column 2 = voltage
   The measured voltage is processed by FFT -> complex two-stage FRF -> IFFT.
10) Exports design, time-series, FRF and plots.

IMPORTANT ENGINEERING LIMITATION
--------------------------------
TU0 is a copper grade, not a unique spring temper. Final manufacture MUST replace
the preliminary material values below with the actual mill certificate / supplier
data for the exact wire/rod diameter and cold-work condition.

For a 90 kg suspended mass, use an independent anti-drop safety cable or mechanical
catch. Integral copper hooks should NOT be the only life-safety load path.

Primary formula references:
- Shigley's Mechanical Engineering Design, helical compression/extension spring chapter.
- A. M. Wahl, Mechanical Springs.
- Machinery's Handbook, extension spring design / hook geometry and stress discussion.
- Copper Development Association (C10100/Cu-OFE elastic-property data, used only as
  a modulus cross-check; TU0 strength must come from actual material certification).

All chart labels are English.
"""

import math
import csv
import io
from dataclasses import dataclass, asdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 1. USER-ADJUSTABLE INPUTS
# ============================================================

g = 9.80665

# ------------------------------------------------------------
# MATERIAL: TU0 HIGH-PURITY OXYGEN-FREE COPPER
# ------------------------------------------------------------
MATERIAL_NAME = "TU0 high-purity oxygen-free copper"

# Elastic constants:
# G ~= 44 GPa is a reasonable preliminary value for high-purity oxygen-free copper.
G_MPa = 44_000.0

# !!! MUST BE REPLACED BY ACTUAL MILL CERTIFICATE FOR PRODUCTION !!!
# These values are deliberately exposed as user inputs instead of pretending that
# TU0 has one universal strength.
UTS_MPa = 345.0
YIELD_MPa = 300.0

# Shigley-style static allowable ratios for nonferrous extension springs.
BODY_TORSION_ALLOW_RATIO = 0.35
HOOK_TORSION_ALLOW_RATIO = 0.30
HOOK_BENDING_ALLOW_RATIO = 0.55

BODY_TORSION_ALLOW_MPa = BODY_TORSION_ALLOW_RATIO * UTS_MPa
HOOK_TORSION_ALLOW_MPa = HOOK_TORSION_ALLOW_RATIO * UTS_MPa
HOOK_BENDING_ALLOW_MPa = HOOK_BENDING_ALLOW_RATIO * UTS_MPa

# Additional utilization cap under proof-load case.
# If 0.85, the design must remain below 85% of the handbook-style allowable.
MAX_ALLOWABLE_UTILIZATION = 0.85

# Proof-load factor applied to static gravity load.
PROOF_LOAD_FACTOR = 1.50

# ------------------------------------------------------------
# INITIAL TENSION -- HANDBOOK-BASED
# ------------------------------------------------------------
# For close-wound extension springs, initial tension is generated during coiling.
# A common handbook/design recommendation is to express the UNCORRECTED initial
# torsional stress as:
#
#       tau_i = A * Sut / C
#
# with the recommended band:
#
#       0.4*Sut/C <= tau_i <= 0.8*Sut/C
#
# Then:
#
#       Fi = pi*d^3*tau_i / (8*D)
#
# IMPORTANT FOR TU0:
# Machinery's Handbook gives explicit reduction factors for stainless steel,
# copper-nickel and phosphor bronze relative to its steel chart, but it does NOT
# publish a dedicated TU0 pure oxygen-free-copper factor. Therefore this code
# keeps a visible user parameter instead of silently pretending that TU0 has a
# handbook-certified factor.
#
# Use 1.0 only as a preliminary generic-equation calculation. Replace with a
# spring-manufacturer-qualified factor when actual TU0 initial-tension capability
# is known.
INITIAL_TENSION_MODE = "handbook"     # "handbook" or "manual"

INITIAL_TENSION_COEFF_LOW = 0.40
INITIAL_TENSION_COEFF_HIGH = 0.80

# 0.0 -> lower edge of recommended band
# 0.5 -> middle
# 1.0 -> upper edge
# Lower edge is selected to avoid overstating reliably retained initial tension.
INITIAL_TENSION_BAND_POSITION = 0.0

# TU0-specific manufacturing correction.
# No dedicated TU0 value was found in Machinery's Handbook.
# Keep explicit and replace after spring-maker qualification.
TU0_INITIAL_TENSION_MATERIAL_FACTOR = 1.0

# Manual values are used only if INITIAL_TENSION_MODE == "manual".
STAGE1_MANUAL_INITIAL_TENSION_N_PER_SPRING = 0.0
STAGE2_MANUAL_INITIAL_TENSION_N = 0.0

# Operational linearity constraint:
# nominal load must exceed initial tension by a useful margin so the spring does
# not repeatedly close/open under ordinary dynamic unloading.
#
# This 0.80 is an engineering system constraint, NOT a handbook chart value.
# Replace it using the measured/required minimum dynamic force if known.
MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL = 0.80

# ------------------------------------------------------------
# LOADS
# ------------------------------------------------------------
M1_kg = 90.0
M2_kg = 0.8
N_STAGE1_SPRINGS = 3

# Worst-case Stage-1 load-share factor.
# Perfect sharing would be 1.0. Example 1.10 means the most heavily loaded spring
# is designed for 10% more than one-third of the total Stage-1 gravity load.
# Replace with a value derived from real geometry/tolerance/load-distribution analysis.
STAGE1_LOAD_SHARE_FACTOR = 1.10

# ------------------------------------------------------------
# DAMPING / ISOLATION BAND
# ------------------------------------------------------------
ZETA_STAGE1 = 0.03
ZETA_STAGE2 = 0.03

ISO_BAND_MIN_Hz = 10.0
ISO_BAND_MAX_Hz = 100.0

# ------------------------------------------------------------
# LENGTH CONSTRAINTS
# ------------------------------------------------------------
STAGE1_MAX_LOADED_LENGTH_mm = 300.0
STAGE2_LENGTH_RATIO_LIMIT = 0.95

# ------------------------------------------------------------
# LEXICOGRAPHIC DESIGN PRIORITIES
# ------------------------------------------------------------
# Strict priority order requested by user:
#   1) Make Stage-2 natural frequency as LOW as possible.
#   2) HARD constraint: Stage-2 loaded length < Stage-1 loaded length.
#   3) Only after (1) and (2), make Stage-1 loaded length as SHORT as possible.
#
# This is NOT a weighted compromise. Lower-priority objectives are never allowed
# to degrade a higher-priority objective beyond the explicit tolerance below.
ENFORCE_STAGE2_SHORTER_THAN_STAGE1 = True

# Minimum required loaded-length clearance:
#     L1_loaded - L2_loaded >= STAGE_LENGTH_CLEARANCE_mm
#
# 0.0 means enforce only the mathematical condition L2 < L1.
# For real manufacture, set this from spring/load/tolerance analysis (for example,
# several millimetres or more as justified by the actual assembly).
STAGE_LENGTH_CLEARANCE_mm = 0.0

# Optional hard upper limit for Stage-2 natural frequency.
# None means "make fn2 as low as the search space and length constraint permit".
STAGE2_HARD_MAX_FN_Hz = None

# ------------------------------------------------------------
# SEARCH RANGES
# ------------------------------------------------------------
# Integer OD requirement is implemented directly.
STAGE1_WIRE_DIAMETERS_mm = np.arange(5.0, 10.01, 0.25)
STAGE1_INTEGER_OD_mm = range(45, 121)
STAGE1_BODY_COILS = range(6, 181)

STAGE2_WIRE_DIAMETERS_mm = np.arange(1.0, 3.51, 0.05)
STAGE2_INTEGER_OD_mm = range(10, 61)
STAGE2_BODY_COILS = range(20, 321)

# Spring index range. Common practical helical-spring range.
C_MIN = 4.0
C_MAX = 12.0

# Full-hook flexibility approximation:
# Machinery's Handbook discusses hook deformation; a pair of full hooks is often
# approximated as adding about one equivalent active coil in rate calculations.
HOOK_EQUIVALENT_COILS_TOTAL = 1.0

# Hook geometry for Shigley-style stress model:
# r1 = D/2 -> C1 = D/d = C
# r2 = 2d  -> C2 = 4
HOOK_R2_OVER_d = 2.0

# Preliminary full-hook projection used only for overall-length estimate.
# Common handbook examples place a regular hook projection around 75-85% of ID.
HOOK_PROJECTION_ID_RATIO = 0.80

# Optimization weights.
W_LENGTH_STAGE1 = 0.45
W_ISOLATION_STAGE1 = 0.55
W_LENGTH_STAGE2 = 0.35
W_ISOLATION_STAGE2 = 0.65

# ------------------------------------------------------------
# OPTIONAL FATIGUE SCREEN
# ------------------------------------------------------------
# Real fatigue calculation requires actual minimum/maximum spring force.
# Set ENABLE_FATIGUE_SCREEN = True only after entering a defensible cyclic-force model.
ENABLE_FATIGUE_SCREEN = False

# Fractional alternating force relative to nominal static force.
# Example: 0.10 means +/-10% of nominal force.
STAGE1_FORCE_AMPLITUDE_RATIO = 0.10
STAGE2_FORCE_AMPLITUDE_RATIO = 0.10

# Preliminary modified-Goodman fatigue strength fractions of Sut.
# These are NOT universal TU0 constants. Replace with qualified spring-wire fatigue data.
BODY_TORSION_ENDURANCE_RATIO = 0.18
HOOK_BENDING_ENDURANCE_RATIO = 0.22
HOOK_TORSION_ENDURANCE_RATIO = 0.16
FATIGUE_SAFETY_FACTOR_REQUIRED = 1.50

# ------------------------------------------------------------
# CSV INPUT
# ------------------------------------------------------------
CSV_SKIP_ROWS = 4
CSV_TIME_COLUMN = 0
CSV_VOLTAGE_COLUMN = 1

# "auto", "s", "ms", "us"
TIME_UNIT = "auto"

OUTPUT_DIR_NAME = "TU0_isolation_results"


# ============================================================
# 2. DATA STRUCTURE
# ============================================================

@dataclass
class SpringDesign:
    stage: str
    material: str
    d_mm: float
    OD_mm: int
    D_mm: float
    ID_mm: float
    C: float
    N_body: int
    N_effective: float
    k_N_per_mm: float
    initial_tension_N: float
    initial_tension_shear_MPa: float
    initial_tension_fraction_nominal: float
    initial_tension_tau_low_MPa: float
    initial_tension_tau_high_MPa: float
    nominal_force_N: float
    proof_force_N: float
    extension_nominal_mm: float
    body_length_mm: float
    hook_projection_each_mm: float
    free_length_mm: float
    loaded_length_mm: float
    fn_Hz: float
    tau_body_proof_MPa: float
    sigma_hook_A_proof_MPa: float
    tau_hook_B_proof_MPa: float
    utilization_body: float
    utilization_hook_A: float
    utilization_hook_B: float
    utilization_max: float
    fatigue_safety_factor: float
    isolation_metric_dB: float


# ============================================================
# 3. SPRING FORMULAS
# ============================================================

def wahl_factor(C):
    """Wahl stress correction factor for round-wire helical spring body."""
    if C <= 1.0:
        return float("inf")
    return (4.0 * C - 1.0) / (4.0 * C - 4.0) + 0.615 / C


def spring_rate_N_per_mm(d_mm, D_mm, N_effective, G=G_MPa):
    """
    Helical extension-spring rate:
        k = G d^4 / (8 D^3 N_eff)
    G in N/mm^2 gives k in N/mm.
    """
    if d_mm <= 0 or D_mm <= 0 or N_effective <= 0:
        return float("nan")
    return G * d_mm**4 / (8.0 * D_mm**3 * N_effective)


def body_shear_MPa(F_N, d_mm, D_mm):
    """Wahl-corrected spring-body shear stress."""
    C = D_mm / d_mm
    return wahl_factor(C) * 8.0 * F_N * D_mm / (math.pi * d_mm**3)


def hook_stress_A_MPa(F_N, d_mm, D_mm, r1_mm=None):
    """
    Shigley-style hook root A:
        bending + direct tensile stress
    Default r1 = D/2.
    """
    if r1_mm is None:
        r1_mm = D_mm / 2.0

    C1 = 2.0 * r1_mm / d_mm
    if C1 <= 1.0:
        return float("inf")

    K_A = (4.0 * C1**2 - C1 - 1.0) / (4.0 * C1 * (C1 - 1.0))

    return F_N * (
        K_A * 16.0 * D_mm / (math.pi * d_mm**3)
        + 4.0 / (math.pi * d_mm**2)
    )


def hook_stress_B_MPa(F_N, d_mm, D_mm, r2_mm=None):
    """
    Shigley-style hook side B torsional stress.
    Default r2 = 2d -> C2 = 4.
    """
    if r2_mm is None:
        r2_mm = HOOK_R2_OVER_d * d_mm

    C2 = 2.0 * r2_mm / d_mm
    if C2 <= 1.0:
        return float("inf")

    K_B = (4.0 * C2 - 1.0) / (4.0 * C2 - 4.0)

    return K_B * 8.0 * F_N * D_mm / (math.pi * d_mm**3)


def preliminary_hook_projection_mm(d_mm, D_mm):
    """
    Preliminary regular full-hook projection from spring body to inside of hook.
    Used ONLY for length estimation.
    """
    ID_mm = D_mm - d_mm
    return HOOK_PROJECTION_ID_RATIO * ID_mm



def handbook_initial_tension_tau_range_MPa(C, Sut_MPa=UTS_MPa):
    """
    Generic extension-spring recommended initial-tension stress band:

        tau_i,low  = 0.4*Sut/C
        tau_i,high = 0.8*Sut/C

    A visible TU0 manufacturing factor is applied because Machinery's Handbook
    does not provide a dedicated TU0 correction factor.

    Returns:
        (tau_low_MPa, tau_high_MPa)
    """
    if C <= 0:
        return float("nan"), float("nan")

    low = (
        INITIAL_TENSION_COEFF_LOW
        * Sut_MPa / C
        * TU0_INITIAL_TENSION_MATERIAL_FACTOR
    )
    high = (
        INITIAL_TENSION_COEFF_HIGH
        * Sut_MPa / C
        * TU0_INITIAL_TENSION_MATERIAL_FACTOR
    )
    return float(low), float(high)


def initial_tension_from_handbook_N(d_mm, D_mm, C):
    """
    Select initial torsional stress inside the recommended band and convert it
    to initial tension force using the UNCORRECTED torsional-stress relation:

        tau_i = 8*Fi*D / (pi*d^3)

        Fi = pi*d^3*tau_i / (8*D)

    Returns:
        Fi_N, tau_i_MPa, tau_low_MPa, tau_high_MPa
    """
    tau_low, tau_high = handbook_initial_tension_tau_range_MPa(C)

    p = float(np.clip(INITIAL_TENSION_BAND_POSITION, 0.0, 1.0))
    tau_i = tau_low + p * (tau_high - tau_low)

    Fi = math.pi * d_mm**3 * tau_i / (8.0 * D_mm)

    return float(Fi), float(tau_i), float(tau_low), float(tau_high)


def get_initial_tension(stage, d_mm, D_mm, C):
    """
    Return the design initial tension.

    Handbook mode:
        calculated from spring index and tensile strength.

    Manual mode:
        uses a manufacturer-specified value, then back-calculates the
        uncorrected initial torsional stress for reporting.
    """
    tau_low, tau_high = handbook_initial_tension_tau_range_MPa(C)

    if INITIAL_TENSION_MODE.lower() == "handbook":
        return initial_tension_from_handbook_N(d_mm, D_mm, C)

    if INITIAL_TENSION_MODE.lower() == "manual":
        if stage == "Stage 1":
            Fi = STAGE1_MANUAL_INITIAL_TENSION_N_PER_SPRING
        elif stage == "Stage 2":
            Fi = STAGE2_MANUAL_INITIAL_TENSION_N
        else:
            raise ValueError("Unknown spring stage.")

        tau_i = 8.0 * Fi * D_mm / (math.pi * d_mm**3)
        return float(Fi), float(tau_i), float(tau_low), float(tau_high)

    raise ValueError(
        "INITIAL_TENSION_MODE must be 'handbook' or 'manual'."
    )

def extension_from_force_mm(F_N, Fi_N, k_N_per_mm):
    """
    Extension-spring force relation:
        F = Fi + k x
        x = (F-Fi)/k
    If load is below initial tension, body coils remain closed and x=0.
    """
    if k_N_per_mm <= 0:
        return float("inf")
    return max(0.0, (F_N - Fi_N) / k_N_per_mm)


# ============================================================
# 4. OPTIONAL FATIGUE SCREEN
# ============================================================

def modified_goodman_sf(stress_mean, stress_alt, endurance_limit, ultimate_limit):
    """
    Modified-Goodman safety factor:
        1/n = sigma_a/Se + sigma_m/Su
    Returns inf if both stresses are zero.
    """
    if stress_alt <= 0 and stress_mean <= 0:
        return float("inf")
    denom = 0.0
    if endurance_limit > 0:
        denom += stress_alt / endurance_limit
    else:
        return 0.0
    if ultimate_limit > 0:
        denom += stress_mean / ultimate_limit
    else:
        return 0.0
    if denom <= 0:
        return float("inf")
    return 1.0 / denom


def fatigue_safety_factor(
    F_nom,
    amplitude_ratio,
    d_mm,
    D_mm
):
    """
    Preliminary fatigue screen using force range:
        Fmax = Fnom * (1 + amplitude_ratio)
        Fmin = max(0, Fnom * (1 - amplitude_ratio))

    IMPORTANT:
    This is only a framework. TU0 fatigue allowables must come from qualified
    material/spring test data before production.
    """
    if not ENABLE_FATIGUE_SCREEN:
        return float("inf")

    Fmax = F_nom * (1.0 + amplitude_ratio)
    Fmin = max(0.0, F_nom * (1.0 - amplitude_ratio))

    # Body torsion
    tau_max = body_shear_MPa(Fmax, d_mm, D_mm)
    tau_min = body_shear_MPa(Fmin, d_mm, D_mm)
    tau_m = 0.5 * (tau_max + tau_min)
    tau_a = 0.5 * (tau_max - tau_min)

    Se_body = BODY_TORSION_ENDURANCE_RATIO * UTS_MPa
    Su_shear = 0.67 * UTS_MPa
    n_body = modified_goodman_sf(tau_m, tau_a, Se_body, Su_shear)

    # Hook A bending
    sig_max = hook_stress_A_MPa(Fmax, d_mm, D_mm)
    sig_min = hook_stress_A_MPa(Fmin, d_mm, D_mm)
    sig_m = 0.5 * (sig_max + sig_min)
    sig_a = 0.5 * (sig_max - sig_min)

    Se_hook_b = HOOK_BENDING_ENDURANCE_RATIO * UTS_MPa
    n_hook_A = modified_goodman_sf(sig_m, sig_a, Se_hook_b, UTS_MPa)

    # Hook B torsion
    tb_max = hook_stress_B_MPa(Fmax, d_mm, D_mm)
    tb_min = hook_stress_B_MPa(Fmin, d_mm, D_mm)
    tb_m = 0.5 * (tb_max + tb_min)
    tb_a = 0.5 * (tb_max - tb_min)

    Se_hook_t = HOOK_TORSION_ENDURANCE_RATIO * UTS_MPa
    n_hook_B = modified_goodman_sf(tb_m, tb_a, Se_hook_t, Su_shear)

    return min(n_body, n_hook_A, n_hook_B)


# ============================================================
# 5. ISOLATION FORMULAS
# ============================================================

def absolute_transmissibility_1dof(f_Hz, fn_Hz, zeta):
    """Absolute transmissibility under base excitation."""
    f = np.asarray(f_Hz, dtype=float)
    r = f / fn_Hz
    numerator = 1.0 + (2.0 * zeta * r)**2
    denominator = (1.0 - r**2)**2 + (2.0 * zeta * r)**2
    return np.sqrt(numerator / denominator)


def isolation_metric_1dof_dB(fn_Hz, zeta):
    """Mean 20log10(T) over the optimization band. More negative is better."""
    f = np.logspace(
        math.log10(ISO_BAND_MIN_Hz),
        math.log10(ISO_BAND_MAX_Hz),
        250
    )
    T = absolute_transmissibility_1dof(f, fn_Hz, zeta)
    T = np.maximum(T, 1e-300)
    return float(np.mean(20.0 * np.log10(T)))


def two_dof_transfer_complex(stage1, stage2, frequencies_Hz):
    """
    Complex base-to-absolute-motion FRFs:
        H1 = X1 / Y
        H2 = X2 / Y

    Base y -> Stage-1 mass x1 -> Stage-2 mass x2
    """
    f = np.asarray(frequencies_Hz, dtype=float)

    m1 = M1_kg
    m2 = M2_kg

    k1 = N_STAGE1_SPRINGS * stage1.k_N_per_mm * 1000.0  # N/m
    k2 = stage2.k_N_per_mm * 1000.0                     # N/m

    # Equivalent viscous damping approximation.
    c1 = 2.0 * ZETA_STAGE1 * math.sqrt(k1 * m1)
    c2 = 2.0 * ZETA_STAGE2 * math.sqrt(k2 * m2)

    M = np.array([[m1, 0.0],
                  [0.0, m2]], dtype=float)

    K = np.array([[k1 + k2, -k2],
                  [-k2,       k2]], dtype=float)

    Cmat = np.array([[c1 + c2, -c2],
                     [-c2,      c2]], dtype=float)

    H1 = np.zeros(len(f), dtype=complex)
    H2 = np.zeros(len(f), dtype=complex)

    for i, fi in enumerate(f):
        w = 2.0 * math.pi * fi

        if abs(w) < 1e-16:
            # Static base motion: both suspended masses follow the base.
            H1[i] = 1.0 + 0j
            H2[i] = 1.0 + 0j
            continue

        A = -w*w*M + 1j*w*Cmat + K

        # Base excitation enters Stage 1 through k1/c1.
        B = np.array([k1 + 1j*w*c1, 0.0], dtype=complex)

        X = np.linalg.solve(A, B)
        H1[i] = X[0]
        H2[i] = X[1]

    return H1, H2


def two_dof_transfer_abs(stage1, stage2, frequencies_Hz):
    H1, H2 = two_dof_transfer_complex(stage1, stage2, frequencies_Hz)
    return np.abs(H1), np.abs(H2)



def two_dof_undamped_natural_frequencies_Hz(stage1, stage2):
    """
    Exact undamped coupled natural frequencies of the 2-DOF vertical system.

    Solves:
        det(K - w^2 M) = 0

    Returns:
        sorted numpy array [f_mode1, f_mode2] in Hz.
    """
    m1 = M1_kg
    m2 = M2_kg

    k1 = N_STAGE1_SPRINGS * stage1.k_N_per_mm * 1000.0
    k2 = stage2.k_N_per_mm * 1000.0

    M = np.array([
        [m1, 0.0],
        [0.0, m2]
    ], dtype=float)

    K = np.array([
        [k1 + k2, -k2],
        [-k2,       k2]
    ], dtype=float)

    # eig(M^-1 K) = w^2
    eigvals = np.linalg.eigvals(np.linalg.solve(M, K))
    eigvals = np.real(eigvals)
    eigvals = np.maximum(eigvals, 0.0)

    omega = np.sqrt(eigvals)
    f = np.sort(omega / (2.0 * math.pi))
    return f

def exact_two_stage_isolation_metric_dB(stage1, stage2):
    f = np.logspace(
        math.log10(ISO_BAND_MIN_Hz),
        math.log10(ISO_BAND_MAX_Hz),
        250
    )
    _, H2 = two_dof_transfer_abs(stage1, stage2, f)
    H2 = np.maximum(H2, 1e-300)
    return float(np.mean(20.0 * np.log10(H2)))


# ============================================================
# 6. CANDIDATE EVALUATION
# ============================================================

def evaluate_candidate(stage, d_mm, OD_mm, N_body, number_parallel, zeta):
    D_mm = float(OD_mm) - float(d_mm)
    if D_mm <= 0:
        return None

    ID_mm = D_mm - d_mm
    if ID_mm <= 0:
        return None

    C = D_mm / d_mm
    if not (C_MIN <= C <= C_MAX):
        return None

    # Two full hooks are approximated as adding one equivalent active coil.
    N_effective = float(N_body) + HOOK_EQUIVALENT_COILS_TOTAL

    k = spring_rate_N_per_mm(d_mm, D_mm, N_effective)
    if not np.isfinite(k) or k <= 0:
        return None

    if stage == "Stage 1":
        total_static = (M1_kg + M2_kg) * g

        # Most heavily loaded spring:
        F_nom = (total_static / number_parallel) * STAGE1_LOAD_SHARE_FACTOR
        amp_ratio = STAGE1_FORCE_AMPLITUDE_RATIO

        # Natural-frequency estimate uses complete suspended mass and all springs.
        modal_mass = M1_kg + M2_kg

    elif stage == "Stage 2":
        total_static = M2_kg * g
        F_nom = total_static
        amp_ratio = STAGE2_FORCE_AMPLITUDE_RATIO
        modal_mass = M2_kg

    else:
        raise ValueError("Unknown stage")

    Fi, tau_i, tau_i_low, tau_i_high = get_initial_tension(
        stage=stage,
        d_mm=d_mm,
        D_mm=D_mm,
        C=C
    )

    if not np.isfinite(Fi) or Fi < 0:
        return None

    # The extension spring must be open at nominal operating load.
    if Fi >= F_nom:
        return None

    # Additional operational margin to reduce coil open/close nonlinearity.
    if Fi / F_nom > MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL:
        return None

    F_proof = PROOF_LOAD_FACTOR * F_nom

    x_nom = extension_from_force_mm(F_nom, Fi, k)

    # Close-wound body length:
    # N_body is physical body-coil count; +1d approximates end transition allowance.
    L_body = (N_body + 1.0) * d_mm

    h_hook = preliminary_hook_projection_mm(d_mm, D_mm)
    L_free = L_body + 2.0 * h_hook
    L_loaded = L_free + x_nom

    # Proof-load stresses.
    tau_body = body_shear_MPa(F_proof, d_mm, D_mm)
    sigma_A = hook_stress_A_MPa(F_proof, d_mm, D_mm)
    tau_B = hook_stress_B_MPa(F_proof, d_mm, D_mm)

    u_body = tau_body / BODY_TORSION_ALLOW_MPa
    u_hook_A = sigma_A / HOOK_BENDING_ALLOW_MPa
    u_hook_B = tau_B / HOOK_TORSION_ALLOW_MPa
    u_max = max(u_body, u_hook_A, u_hook_B)

    fatigue_n = fatigue_safety_factor(
        F_nom=F_nom,
        amplitude_ratio=amp_ratio,
        d_mm=d_mm,
        D_mm=D_mm
    )

    # Preliminary stage natural frequency.
    k_total_N_per_m = number_parallel * k * 1000.0
    fn = (1.0 / (2.0 * math.pi)) * math.sqrt(k_total_N_per_m / modal_mass)

    metric = isolation_metric_1dof_dB(fn, zeta)

    return SpringDesign(
        stage=stage,
        material=MATERIAL_NAME,
        d_mm=float(d_mm),
        OD_mm=int(OD_mm),
        D_mm=float(D_mm),
        ID_mm=float(ID_mm),
        C=float(C),
        N_body=int(N_body),
        N_effective=float(N_effective),
        k_N_per_mm=float(k),
        initial_tension_N=float(Fi),
        initial_tension_shear_MPa=float(tau_i),
        initial_tension_fraction_nominal=float(Fi / F_nom),
        initial_tension_tau_low_MPa=float(tau_i_low),
        initial_tension_tau_high_MPa=float(tau_i_high),
        nominal_force_N=float(F_nom),
        proof_force_N=float(F_proof),
        extension_nominal_mm=float(x_nom),
        body_length_mm=float(L_body),
        hook_projection_each_mm=float(h_hook),
        free_length_mm=float(L_free),
        loaded_length_mm=float(L_loaded),
        fn_Hz=float(fn),
        tau_body_proof_MPa=float(tau_body),
        sigma_hook_A_proof_MPa=float(sigma_A),
        tau_hook_B_proof_MPa=float(tau_B),
        utilization_body=float(u_body),
        utilization_hook_A=float(u_hook_A),
        utilization_hook_B=float(u_hook_B),
        utilization_max=float(u_max),
        fatigue_safety_factor=float(fatigue_n),
        isolation_metric_dB=float(metric)
    )


# ============================================================
# 7. OPTIMIZATION
# ============================================================

def normalize(values):
    v = np.asarray(values, dtype=float)
    span = float(v.max() - v.min())
    if span <= 1e-15:
        return np.zeros_like(v)
    return (v - v.min()) / span


def choose_weighted_knee(candidates, w_length, w_isolation):
    if not candidates:
        raise RuntimeError("No candidate supplied.")

    lengths = np.array([c.loaded_length_mm for c in candidates], dtype=float)
    metrics = np.array([c.isolation_metric_dB for c in candidates], dtype=float)

    Lnorm = normalize(lengths)
    # More-negative isolation metric is better; min maps to zero.
    Inorm = normalize(metrics)

    score = w_length * Lnorm + w_isolation * Inorm
    return candidates[int(np.argmin(score))]


def static_and_fatigue_pass(design):
    if design.utilization_max > MAX_ALLOWABLE_UTILIZATION:
        return False

    if ENABLE_FATIGUE_SCREEN:
        if design.fatigue_safety_factor < FATIGUE_SAFETY_FACTOR_REQUIRED:
            return False

    return True


def generate_stage1_feasible():
    """
    Generate statically safe Stage-1 candidates.

    Stage 1 is NOT selected independently anymore because doing so can prevent
    the globally best Stage-2 low-frequency solution. It is only filtered by
    hard engineering constraints here.
    """
    feasible = []

    for d in STAGE1_WIRE_DIAMETERS_mm:
        for OD in STAGE1_INTEGER_OD_mm:
            for N_body in STAGE1_BODY_COILS:
                design = evaluate_candidate(
                    stage="Stage 1",
                    d_mm=float(d),
                    OD_mm=int(OD),
                    N_body=int(N_body),
                    number_parallel=N_STAGE1_SPRINGS,
                    zeta=ZETA_STAGE1
                )

                if design is None:
                    continue

                if not static_and_fatigue_pass(design):
                    continue

                if design.loaded_length_mm > STAGE1_MAX_LOADED_LENGTH_mm:
                    continue

                feasible.append(design)

    if not feasible:
        raise RuntimeError(
            "No feasible Stage-1 design in the current search envelope."
        )

    return feasible


def generate_stage2_feasible():
    """
    Generate statically safe Stage-2 candidates independent of Stage 1.
    The L2 < L1 hard constraint is applied during pair matching.
    """
    feasible = []

    for d in STAGE2_WIRE_DIAMETERS_mm:
        for OD in STAGE2_INTEGER_OD_mm:
            for N_body in STAGE2_BODY_COILS:
                design = evaluate_candidate(
                    stage="Stage 2",
                    d_mm=float(d),
                    OD_mm=int(OD),
                    N_body=int(N_body),
                    number_parallel=1,
                    zeta=ZETA_STAGE2
                )

                if design is None:
                    continue

                if not static_and_fatigue_pass(design):
                    continue

                if STAGE2_HARD_MAX_FN_Hz is not None:
                    if design.fn_Hz > STAGE2_HARD_MAX_FN_Hz:
                        continue

                feasible.append(design)

    if not feasible:
        raise RuntimeError(
            "No feasible Stage-2 design in the current search envelope."
        )

    return feasible


def lexicographic_joint_optimization():
    """
    STRICT joint lexicographic optimization.

    Priority 1:
        Make Stage-2 local natural frequency fn2 as LOW as possible.

    Hard constraint:
        L2_loaded + STAGE_LENGTH_CLEARANCE_mm < L1_loaded
        (with zero clearance this reduces to L2 < L1).

    Priority 2:
        After the globally minimum feasible fn2 is fixed, select the SHORTEST
        safe Stage-1 spring that can contain that Stage-2 loaded length.

    Priority 3:
        If multiple Stage-2 geometries have exactly the same minimum fn2 within
        numerical precision, select the shorter Stage-2 geometry, then lower
        utilization.

    No weighted objective is used.
    A shorter Stage 1 is NEVER allowed to worsen the best achievable fn2.
    """
    stage1_candidates = generate_stage1_feasible()
    stage2_candidates = generate_stage2_feasible()

    stage1_sorted = sorted(
        stage1_candidates,
        key=lambda d: (
            d.loaded_length_mm,
            d.utilization_max,
            d.OD_mm,
            d.d_mm
        )
    )

    max_stage1_length = max(d.loaded_length_mm for d in stage1_sorted)

    # Stage-2 candidates that can fit below at least one safe Stage-1 design.
    compatible_stage2 = [
        s2 for s2 in stage2_candidates
        if (
            s2.loaded_length_mm + STAGE_LENGTH_CLEARANCE_mm
            < max_stage1_length
        )
    ]

    if not compatible_stage2:
        raise RuntimeError(
            "No Stage-2 candidate can satisfy the loaded-length constraint.\n"
            f"Required: L2 + {STAGE_LENGTH_CLEARANCE_mm:.3f} mm < L1.\n"
            f"Longest available safe Stage-1 loaded length = "
            f"{max_stage1_length:.3f} mm.\n"
            "Increase STAGE1_MAX_LOADED_LENGTH_mm / STAGE1_BODY_COILS or "
            "broaden the safe Stage-1 geometry search."
        )

    # Priority 1: absolute minimum feasible Stage-2 natural frequency.
    global_best_fn = min(s2.fn_Hz for s2 in compatible_stage2)

    # Numerical equality only; this is NOT an engineering trade-off tolerance.
    fn_eps = max(1e-12, abs(global_best_fn) * 1e-10)

    best_fn_stage2 = [
        s2 for s2 in compatible_stage2
        if abs(s2.fn_Hz - global_best_fn) <= fn_eps
    ]

    # Priority 3 for exact-frequency ties.
    best_s2 = min(
        best_fn_stage2,
        key=lambda d: (
            d.loaded_length_mm,
            d.utilization_max,
            d.OD_mm,
            d.d_mm,
            d.N_body
        )
    )

    # Priority 2: after fn2 is fixed, find the shortest safe Stage 1 that is
    # strictly longer than Stage 2 by the requested clearance.
    compatible_stage1 = [
        s1 for s1 in stage1_sorted
        if (
            best_s2.loaded_length_mm + STAGE_LENGTH_CLEARANCE_mm
            < s1.loaded_length_mm
        )
    ]

    if not compatible_stage1:
        raise RuntimeError(
            "Internal optimization error: globally selected Stage-2 design "
            "has no compatible Stage-1 design."
        )

    best_s1 = compatible_stage1[0]

    # Exact two-stage metric is reporting only; it does not override the stated
    # priority order.
    best_s2.isolation_metric_dB = exact_two_stage_isolation_metric_dB(
        best_s1, best_s2
    )

    diagnostics = {
        "global_min_stage2_fn_Hz": float(global_best_fn),
        "stage_length_clearance_mm": float(STAGE_LENGTH_CLEARANCE_mm),
        "stage1_candidate_count": len(stage1_candidates),
        "stage2_candidate_count": len(stage2_candidates),
        "min_fn_stage2_tie_count": len(best_fn_stage2),
        "length_margin_mm": float(
            best_s1.loaded_length_mm - best_s2.loaded_length_mm
        ),
    }

    return best_s1, best_s2, diagnostics, stage1_candidates, stage2_candidates


# ============================================================
# 8. DESIGN REPORT / EXPORT
# ============================================================

def print_design(d):
    print("\n" + "=" * 82)
    print(d.stage)
    print("=" * 82)
    print(f"Material                         = {d.material}")
    print(f"Wire diameter d                  = {d.d_mm:.3f} mm")
    print(f"Outside diameter OD              = {d.OD_mm:d} mm  (integer)")
    print(f"Mean coil diameter D             = {d.D_mm:.3f} mm")
    print(f"Inside diameter ID               = {d.ID_mm:.3f} mm")
    print(f"Spring index C                   = {d.C:.3f}")
    print(f"Physical body coils N_body       = {d.N_body:d}")
    print(f"Effective coils N_eff            = {d.N_effective:.3f}")
    print(f"Spring rate                      = {d.k_N_per_mm:.6f} N/mm")
    print(f"Initial tension Fi               = {d.initial_tension_N:.3f} N")
    print(f"Initial tension shear tau_i      = {d.initial_tension_shear_MPa:.3f} MPa")
    print(
        f"Handbook tau_i band              = "
        f"{d.initial_tension_tau_low_MPa:.3f} to "
        f"{d.initial_tension_tau_high_MPa:.3f} MPa"
    )
    print(
        f"Fi / nominal force               = "
        f"{100*d.initial_tension_fraction_nominal:.2f} %"
    )
    print(f"Nominal design force             = {d.nominal_force_N:.3f} N")
    print(f"{PROOF_LOAD_FACTOR:.2f}x proof force                 = {d.proof_force_N:.3f} N")
    print(f"Nominal extension                = {d.extension_nominal_mm:.3f} mm")
    print(f"Body length estimate             = {d.body_length_mm:.3f} mm")
    print(f"Hook projection / end            = {d.hook_projection_each_mm:.3f} mm")
    print(f"Free overall length estimate     = {d.free_length_mm:.3f} mm")
    print(f"Loaded/equilibrium length        = {d.loaded_length_mm:.3f} mm")
    print(f"Preliminary natural frequency    = {d.fn_Hz:.3f} Hz")
    print(f"Body shear @ proof               = {d.tau_body_proof_MPa:.3f} MPa")
    print(f"Hook-A stress @ proof            = {d.sigma_hook_A_proof_MPa:.3f} MPa")
    print(f"Hook-B shear @ proof             = {d.tau_hook_B_proof_MPa:.3f} MPa")
    print(f"Body utilization                 = {100*d.utilization_body:.1f} %")
    print(f"Hook-A utilization               = {100*d.utilization_hook_A:.1f} %")
    print(f"Hook-B utilization               = {100*d.utilization_hook_B:.1f} %")
    print(f"Maximum utilization              = {100*d.utilization_max:.1f} %")

    if ENABLE_FATIGUE_SCREEN:
        print(f"Preliminary fatigue safety factor= {d.fatigue_safety_factor:.3f}")
    else:
        print("Fatigue screen                    = DISABLED (requires real cyclic force data)")

    print(
        f"Isolation metric                 = {d.isolation_metric_dB:.2f} dB "
        f"over {ISO_BAND_MIN_Hz:g}-{ISO_BAND_MAX_Hz:g} Hz"
    )


def save_design_csv(stage1, stage2, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "optimized_TU0_spring_design.csv"

    rows = [asdict(stage1), asdict(stage2)]

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return path


def save_summary(stage1, stage2, output_dir, measured_summary=None):
    path = output_dir / "summary.txt"

    lines = []
    lines.append("TU0 EXTENSION SPRING + TWO-STAGE ISOLATION SUMMARY")
    lines.append("=" * 72)
    lines.append("")
    lines.append("IMPORTANT:")
    lines.append("UTS/Yield are preliminary inputs and must be replaced by the actual TU0")
    lines.append("material certificate for the selected diameter and cold-work condition.")
    lines.append("")
    lines.append(
        f"Static allowables: body torsion={BODY_TORSION_ALLOW_RATIO:.2f} Sut, "
        f"hook torsion={HOOK_TORSION_ALLOW_RATIO:.2f} Sut, "
        f"hook bending={HOOK_BENDING_ALLOW_RATIO:.2f} Sut."
    )
    lines.append(
        f"Proof-load factor={PROOF_LOAD_FACTOR:.2f}; "
        f"maximum allowable utilization={MAX_ALLOWABLE_UTILIZATION:.2f}."
    )
    lines.append(
        f"Stage-1 worst-case load-share factor={STAGE1_LOAD_SHARE_FACTOR:.3f}."
    )
    lines.append(
        f"Initial-tension mode={INITIAL_TENSION_MODE}; "
        f"recommended generic band={INITIAL_TENSION_COEFF_LOW:.2f} to "
        f"{INITIAL_TENSION_COEFF_HIGH:.2f} times Sut/C."
    )
    lines.append(
        f"TU0 initial-tension material factor="
        f"{TU0_INITIAL_TENSION_MATERIAL_FACTOR:.3f} "
        "(must be qualified by spring manufacturer; no dedicated TU0 factor "
        "is supplied by the cited Machinery's Handbook chart)."
    )
    lines.append(
        f"Maximum Fi/Fnom operational ratio="
        f"{MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL:.3f}."
    )
    lines.append("")

    for d in [stage1, stage2]:
        lines.append(d.stage)
        lines.append("-" * 40)
        lines.append(f"d = {d.d_mm:.3f} mm")
        lines.append(f"OD = {d.OD_mm:d} mm")
        lines.append(f"D = {d.D_mm:.3f} mm")
        lines.append(f"ID = {d.ID_mm:.3f} mm")
        lines.append(f"C = {d.C:.3f}")
        lines.append(f"N_body = {d.N_body:d}")
        lines.append(f"N_eff = {d.N_effective:.3f}")
        lines.append(f"k = {d.k_N_per_mm:.6f} N/mm")
        lines.append(f"Initial tension Fi = {d.initial_tension_N:.6f} N")
        lines.append(
            f"Initial tension tau_i = {d.initial_tension_shear_MPa:.6f} MPa"
        )
        lines.append(
            f"Recommended tau_i band = "
            f"{d.initial_tension_tau_low_MPa:.6f} to "
            f"{d.initial_tension_tau_high_MPa:.6f} MPa"
        )
        lines.append(
            f"Fi/Fnom = {d.initial_tension_fraction_nominal:.6f}"
        )
        lines.append(f"Loaded length = {d.loaded_length_mm:.3f} mm")
        lines.append(f"Max utilization = {100*d.utilization_max:.2f}%")
        lines.append(f"Isolation metric = {d.isolation_metric_dB:.3f} dB")
        lines.append("")

    if measured_summary:
        lines.append("MEASURED CSV PROCESSING")
        lines.append("-" * 40)
        for k, v in measured_summary.items():
            lines.append(f"{k}: {v}")

    lines.append("")
    lines.append("SAFETY NOTE:")
    lines.append("Use an independent anti-drop cable/mechanical catch for the 90 kg mass.")
    lines.append("Final end geometry requires proof-load, fatigue, creep/stress-relaxation")
    lines.append("and manufacturing validation. Integral copper hooks should not be the")
    lines.append("sole safety-critical load path.")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ============================================================
# 9. THEORETICAL PLOTS / FRF EXPORT
# ============================================================

def save_theoretical_results(stage1, stage2, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    f = np.logspace(math.log10(0.2), math.log10(200.0), 2200)
    H1c, H2c = two_dof_transfer_complex(stage1, stage2, f)
    H1 = np.abs(H1c)
    H2 = np.abs(H2c)

    # FRF CSV
    frf_path = output_dir / "two_stage_frequency_response.csv"
    with open(frf_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Stage1_Magnitude",
            "Stage1_Phase_deg",
            "Stage2_Magnitude",
            "Stage2_Phase_deg"
        ])
        for row in zip(
            f,
            H1,
            np.angle(H1c, deg=True),
            H2,
            np.angle(H2c, deg=True)
        ):
            writer.writerow(row)

    # Transmissibility plot
    p = output_dir / "01_theoretical_two_stage_transmissibility.png"
    plt.figure(figsize=(9, 5.5))
    plt.loglog(f, H1, label="Stage 1 platform")
    plt.loglog(f, H2, label="Stage 2 payload")
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Absolute transmissibility |X/Y|")
    plt.title("TU0 Two-Stage Extension-Spring Isolation")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=180)
    plt.close()

    return frf_path, p


# ============================================================
# 10. CSV FILE PICKER / SIGNAL PROCESSING
# ============================================================

def pick_csv_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title="Select vibration CSV file",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
    )

    root.destroy()

    if not path:
        return None

    return Path(path)


def _decode_text_file_robust(path):
    """
    Robustly decode a text/CSV file.

    Tries BOM-aware Unicode encodings first, then common Chinese Windows encodings.
    Returns:
        decoded_text, encoding_name
    """
    path = Path(path)
    data = path.read_bytes()

    # BOM checks first.
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16"), "utf-16"

    # Common encodings for instrument-exported CSV files.
    candidates = [
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
        "cp936",
        "utf-16-le",
        "utf-16-be",
    ]

    errors = []
    for enc in candidates:
        try:
            decoded = data.decode(enc)

            # Reject obviously wrong UTF-16 guesses with excessive NULs.
            if "\x00" in decoded:
                nul_ratio = decoded.count("\x00") / max(len(decoded), 1)
                if nul_ratio > 0.05 and "utf-16" not in enc:
                    continue

            return decoded, enc
        except UnicodeDecodeError as exc:
            errors.append(f"{enc}: {exc}")

    # Last-resort byte-preserving decode. This prevents the program from dying
    # because of metadata characters; numeric rows can still be parsed below.
    decoded = data.decode("latin-1")
    return decoded, "latin-1-fallback"


def _detect_delimiter_from_numeric_lines(lines):
    """
    Detect delimiter from data lines.
    Supported delimiters: comma, tab, semicolon.
    """
    candidates = [",", "\t", ";"]

    best_delim = ","
    best_score = -1

    sample_lines = lines[:min(len(lines), 50)]

    for delim in candidates:
        score = 0
        for line in sample_lines:
            parts = line.strip().split(delim)
            if len(parts) >= 2:
                # Reward lines whose first two columns look numeric.
                try:
                    float(parts[0].strip().replace('"', ''))
                    float(parts[1].strip().replace('"', ''))
                    score += 3
                except Exception:
                    score += 1

        if score > best_score:
            best_score = score
            best_delim = delim

    return best_delim


def load_time_voltage_csv(path):
    """
    Robust CSV/text loader.

    User format:
        - skip the first CSV_SKIP_ROWS rows
        - first column = time
        - second column = voltage

    Improvements:
        - automatic encoding detection:
          UTF-8 / UTF-8 BOM / UTF-16 / GB18030 / GBK / CP936
        - automatic delimiter detection:
          comma / tab / semicolon
        - ignores non-numeric rows after the first 4 rows
        - tolerates quoted numeric fields
        - resamples slightly nonuniform time data before FFT
    """
    path = Path(path)

    decoded_text, detected_encoding = _decode_text_file_robust(path)

    # Normalize line endings and remove Unicode NUL characters that sometimes
    # occur when instrument software exports UTF-16-like text.
    decoded_text = decoded_text.replace("\x00", "")
    all_lines = decoded_text.splitlines()

    if len(all_lines) <= CSV_SKIP_ROWS:
        raise ValueError(
            f"File contains only {len(all_lines)} lines; "
            f"cannot skip the first {CSV_SKIP_ROWS} rows."
        )

    data_lines = all_lines[CSV_SKIP_ROWS:]
    delimiter = _detect_delimiter_from_numeric_lines(data_lines)

    print(
        f"Detected text encoding: {detected_encoding}; "
        f"delimiter: {repr(delimiter)}"
    )

    # Parse numeric rows ourselves instead of letting NumPy decode the file.
    # This avoids Windows locale/GBK decoding failures inside genfromtxt().
    parsed = []

    for line_no, line in enumerate(data_lines, start=CSV_SKIP_ROWS + 1):
        line = line.strip()
        if not line:
            continue

        # Parse using Python csv reader so quoted fields are handled correctly.
        try:
            row = next(csv.reader([line], delimiter=delimiter))
        except Exception:
            continue

        max_required_col = max(CSV_TIME_COLUMN, CSV_VOLTAGE_COLUMN)
        if len(row) <= max_required_col:
            continue

        t_field = row[CSV_TIME_COLUMN].strip().strip('"').strip()
        v_field = row[CSV_VOLTAGE_COLUMN].strip().strip('"').strip()

        # Some instruments use decimal comma only when delimiter is semicolon.
        if delimiter == ";":
            t_field = t_field.replace(",", ".")
            v_field = v_field.replace(",", ".")

        try:
            t_val = float(t_field)
            v_val = float(v_field)
        except ValueError:
            # Header/unit/comment line after the four skipped rows -> ignore.
            continue

        if np.isfinite(t_val) and np.isfinite(v_val):
            parsed.append((t_val, v_val))

    if len(parsed) < 16:
        preview = "\n".join(data_lines[:8])
        raise ValueError(
            "Too few valid numeric samples were found after skipping the first "
            f"{CSV_SKIP_ROWS} rows.\n"
            f"Detected encoding: {detected_encoding}\n"
            f"Detected delimiter: {repr(delimiter)}\n\n"
            "First data-area lines:\n"
            f"{preview}"
        )

    raw = np.asarray(parsed, dtype=float)

    t_raw = raw[:, 0]
    v = raw[:, 1]

    # Sort by time to protect against an occasional out-of-order row.
    order = np.argsort(t_raw)
    t_raw = t_raw[order]
    v = v[order]

    # Remove duplicate / non-increasing time samples.
    if len(t_raw) >= 2:
        keep = np.concatenate([
            [True],
            np.diff(t_raw) > 0
        ])
        t_raw = t_raw[keep]
        v = v[keep]

    if len(t_raw) < 16:
        raise ValueError(
            "Too few strictly increasing time samples remain after cleaning."
        )

    t = convert_time_to_seconds(t_raw)

    # Basic sample interval checks.
    dt = np.diff(t)
    dt_med = float(np.median(dt))

    if not np.isfinite(dt_med) or dt_med <= 0:
        raise ValueError(
            "Invalid time column: median sample interval is non-positive."
        )

    # Relative sampling jitter.
    rel_jitter = float(np.std(dt) / dt_med)

    print(
        f"Valid samples: {len(t)}; "
        f"median dt = {dt_med:.9g} s; "
        f"sampling rate ≈ {1.0/dt_med:.6g} Hz; "
        f"relative time-step jitter = {rel_jitter:.3e}"
    )

    # FFT requires uniform sampling. If the measured timestamp jitter is larger
    # than 0.1%, interpolate onto an equally spaced grid.
    if rel_jitter > 1e-3:
        print(
            "Time samples are not sufficiently uniform for direct FFT; "
            "linearly resampling to a uniform time grid."
        )

        t_uniform = np.linspace(t[0], t[-1], len(t))
        v_uniform = np.interp(t_uniform, t, v)

        t = t_uniform
        v = v_uniform

    return t, v

def convert_time_to_seconds(t):
    t = np.asarray(t, dtype=float)

    if TIME_UNIT == "s":
        return t
    if TIME_UNIT == "ms":
        return t * 1e-3
    if TIME_UNIT == "us":
        return t * 1e-6
    if TIME_UNIT != "auto":
        raise ValueError("TIME_UNIT must be 'auto', 's', 'ms', or 'us'.")

    dt = float(np.median(np.diff(t)))

    # Conservative heuristic:
    # Large numeric dt commonly indicates microseconds or milliseconds.
    # Explicit TIME_UNIT is strongly preferred when known.
    if dt >= 100.0:
        return t * 1e-6
    if dt >= 0.1:
        return t * 1e-3
    return t


def apply_isolation_to_voltage(stage1, stage2, t, voltage):
    """
    Remove DC -> rFFT -> multiply complex FRF -> irFFT.
    DC is then added back for convenience.

    This assumes sensor voltage is linearly proportional to one absolute vibration
    quantity (displacement/velocity/acceleration) over the frequency range of interest.
    """
    n = len(voltage)
    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt

    dc = float(np.mean(voltage))
    vin_ac = voltage - dc

    freq = np.fft.rfftfreq(n, d=dt)
    V = np.fft.rfft(vin_ac)

    H1, H2 = two_dof_transfer_complex(stage1, stage2, freq)

    # Preserve zero-frequency DC handling separately.
    if len(H1):
        H1[0] = 0.0 + 0j
        H2[0] = 0.0 + 0j

    V1 = V * H1
    V2 = V * H2

    v1_ac = np.fft.irfft(V1, n=n)
    v2_ac = np.fft.irfft(V2, n=n)

    v1 = v1_ac + dc
    v2 = v2_ac + dc

    return {
        "fs_Hz": fs,
        "dc_V": dc,
        "freq_Hz": freq,
        "input_ac": vin_ac,
        "stage1_ac": v1_ac,
        "stage2_ac": v2_ac,
        "stage1_full": v1,
        "stage2_full": v2,
        "H1": H1,
        "H2": H2,
        "FFT_input": V,
        "FFT_stage1": V1,
        "FFT_stage2": V2,
    }


def one_sided_amplitude_spectrum(x, fs):
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0/fs)
    amp = np.abs(X) / n
    if n > 2:
        amp[1:-1] *= 2.0
    return f, amp


def periodogram_psd(x, fs):
    """
    One-sided periodogram PSD in V^2/Hz.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)

    # Hann window to reduce leakage.
    w = np.hanning(n)
    U = np.sum(w**2)

    X = np.fft.rfft(x * w)
    psd = (np.abs(X)**2) / (fs * U)

    if n > 2:
        psd[1:-1] *= 2.0

    f = np.fft.rfftfreq(n, 1.0/fs)
    return f, psd


def rms_ac(x):
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x**2)))


def attenuation_dB(out_rms, in_rms):
    if in_rms <= 0:
        return float("nan")
    ratio = max(out_rms / in_rms, 1e-300)
    return 20.0 * math.log10(ratio)


def export_measured_csv(t, voltage, result, output_dir):
    path = output_dir / "measured_isolation_processed.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Time_s",
            "Original_V",
            "Original_AC_V",
            "After_Stage1_AC_V",
            "After_Stage2_AC_V",
            "After_Stage1_Full_V",
            "After_Stage2_Full_V"
        ])

        for row in zip(
            t,
            voltage,
            result["input_ac"],
            result["stage1_ac"],
            result["stage2_ac"],
            result["stage1_full"],
            result["stage2_full"]
        ):
            writer.writerow(row)

    return path


def make_measured_plots(t, voltage, result, output_dir):
    fs = result["fs_Hz"]
    x0 = result["input_ac"]
    x1 = result["stage1_ac"]
    x2 = result["stage2_ac"]

    paths = []

    # 1) Full time-domain AC comparison
    p = output_dir / "02_measured_time_domain_full.png"
    plt.figure(figsize=(10, 5.5))
    plt.plot(t, x0, label="Input AC voltage", linewidth=0.8)
    plt.plot(t, x1, label="After Stage 1", linewidth=0.8)
    plt.plot(t, x2, label="After Stage 2", linewidth=0.8)
    plt.xlabel("Time (s)")
    plt.ylabel("AC voltage (V)")
    plt.title("Measured Signal: Time-Domain Isolation")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    # 2) Zoomed time-domain comparison
    duration = t[-1] - t[0]
    zoom_duration = min(5.0, max(duration * 0.10, duration / 100.0))
    mask = t <= (t[0] + zoom_duration)

    p = output_dir / "03_measured_time_domain_zoom.png"
    plt.figure(figsize=(10, 5.5))
    plt.plot(t[mask], x0[mask], label="Input AC voltage", linewidth=0.9)
    plt.plot(t[mask], x1[mask], label="After Stage 1", linewidth=0.9)
    plt.plot(t[mask], x2[mask], label="After Stage 2", linewidth=0.9)
    plt.xlabel("Time (s)")
    plt.ylabel("AC voltage (V)")
    plt.title("Measured Signal: Time-Domain Isolation (Zoom)")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    # 3) Amplitude spectrum
    f0, a0 = one_sided_amplitude_spectrum(x0, fs)
    f1, a1 = one_sided_amplitude_spectrum(x1, fs)
    f2, a2 = one_sided_amplitude_spectrum(x2, fs)

    positive = f0 > 0

    p = output_dir / "04_measured_amplitude_spectrum.png"
    plt.figure(figsize=(10, 5.5))
    plt.loglog(f0[positive], np.maximum(a0[positive], 1e-300), label="Input")
    plt.loglog(f1[positive], np.maximum(a1[positive], 1e-300), label="After Stage 1")
    plt.loglog(f2[positive], np.maximum(a2[positive], 1e-300), label="After Stage 2")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude (V)")
    plt.title("Measured Signal: Amplitude Spectrum")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    # 4) PSD comparison
    fp0, p0 = periodogram_psd(x0, fs)
    fp1, p1 = periodogram_psd(x1, fs)
    fp2, p2 = periodogram_psd(x2, fs)

    positive = fp0 > 0

    p = output_dir / "05_measured_PSD_comparison.png"
    plt.figure(figsize=(10, 5.5))
    plt.loglog(fp0[positive], np.maximum(p0[positive], 1e-300), label="Input PSD")
    plt.loglog(fp1[positive], np.maximum(p1[positive], 1e-300), label="After Stage 1")
    plt.loglog(fp2[positive], np.maximum(p2[positive], 1e-300), label="After Stage 2")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Voltage PSD (V²/Hz)")
    plt.title("Measured Signal: PSD Comparison")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    return paths


# ============================================================
# 11. MAIN
# ============================================================

def main():
    print("\n" + "=" * 82)
    print("TU0 TWO-STAGE EXTENSION-SPRING OPTIMIZATION")
    print("=" * 82)
    print("Strict priority order:")
    print("  1) Minimize Stage-2 natural frequency")
    print("  2) Enforce Stage-2 loaded length < Stage-1 loaded length")
    print("  3) Then minimize Stage-1 loaded length")
    print("")

    print("Running joint lexicographic optimization...")
    print(
        "Initial tension: handbook-based tau_i range "
        f"{INITIAL_TENSION_COEFF_LOW:.2f}*Sut/C to "
        f"{INITIAL_TENSION_COEFF_HIGH:.2f}*Sut/C"
    )
    print(
        "TU0 initial-tension material factor = "
        f"{TU0_INITIAL_TENSION_MATERIAL_FACTOR:.3f} "
        "(manufacturer qualification required)"
    )

    stage1, stage2, opt_diag, feasible1, feasible2 = (
        lexicographic_joint_optimization()
    )

    # --------------------------------------------------------
    # HARD CHECKS
    # --------------------------------------------------------
    assert stage1.OD_mm == int(stage1.OD_mm)
    assert stage2.OD_mm == int(stage2.OD_mm)

    assert stage1.utilization_max <= MAX_ALLOWABLE_UTILIZATION
    assert stage2.utilization_max <= MAX_ALLOWABLE_UTILIZATION

    assert (
        stage2.loaded_length_mm + STAGE_LENGTH_CLEARANCE_mm
        < stage1.loaded_length_mm
    )

    if STAGE2_HARD_MAX_FN_Hz is not None:
        assert stage2.fn_Hz <= STAGE2_HARD_MAX_FN_Hz

    if ENABLE_FATIGUE_SCREEN:
        assert stage1.fatigue_safety_factor >= FATIGUE_SAFETY_FACTOR_REQUIRED
        assert stage2.fatigue_safety_factor >= FATIGUE_SAFETY_FACTOR_REQUIRED

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------
    print_design(stage1)
    print_design(stage2)

    coupled_fn = two_dof_undamped_natural_frequencies_Hz(stage1, stage2)

    print("\n" + "=" * 82)
    print("STRICT OPTIMIZATION / GEOMETRIC CHECK")
    print("=" * 82)

    print(f"Stage-1 loaded length            = {stage1.loaded_length_mm:.6f} mm")
    print(f"Stage-2 loaded length            = {stage2.loaded_length_mm:.6f} mm")
    print(
        f"Actual L1-L2 loaded margin       = "
        f"{stage1.loaded_length_mm-stage2.loaded_length_mm:.6f} mm"
    )
    print(
        f"Required L1-L2 clearance         = "
        f"{STAGE_LENGTH_CLEARANCE_mm:.6f} mm"
    )
    print(
        f"Stage-2 / Stage-1 length ratio   = "
        f"{stage2.loaded_length_mm/stage1.loaded_length_mm:.9f}"
    )

    print(f"Stage-2 local natural frequency  = {stage2.fn_Hz:.9f} Hz")
    print(
        f"Global minimum feasible fn2      = "
        f"{opt_diag['global_min_stage2_fn_Hz']:.9f} Hz"
    )

    print(
        "Exact coupled 2-DOF modes        = "
        + ", ".join(f"{x:.9f} Hz" for x in coupled_fn)
    )

    print(f"Stage-1 feasible candidates      = {len(feasible1)}")
    print(f"Stage-2 feasible candidates      = {len(feasible2)}")
    print(
        f"Exact-minimum-fn2 geometry ties  = "
        f"{opt_diag['min_fn_stage2_tie_count']}"
    )

    # --------------------------------------------------------
    # CSV FILE PICKER
    # --------------------------------------------------------
    csv_path = pick_csv_file()

    if csv_path is not None:
        output_dir = csv_path.parent / OUTPUT_DIR_NAME
    else:
        output_dir = Path.cwd() / OUTPUT_DIR_NAME

    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # DESIGN / THEORETICAL OUTPUT
    # --------------------------------------------------------
    design_csv = save_design_csv(stage1, stage2, output_dir)
    frf_csv, theoretical_plot = save_theoretical_results(
        stage1, stage2, output_dir
    )

    measured_summary = None
    measured_files = []

    # --------------------------------------------------------
    # MEASURED CSV PROCESSING
    # --------------------------------------------------------
    if csv_path is not None:
        print(f"\nReading measured CSV: {csv_path}")

        t, voltage = load_time_voltage_csv(csv_path)

        result = apply_isolation_to_voltage(
            stage1,
            stage2,
            t,
            voltage
        )

        processed_csv = export_measured_csv(
            t,
            voltage,
            result,
            output_dir
        )

        plots = make_measured_plots(
            t,
            voltage,
            result,
            output_dir
        )

        rms0 = rms_ac(result["input_ac"])
        rms1 = rms_ac(result["stage1_ac"])
        rms2 = rms_ac(result["stage2_ac"])

        measured_summary = {
            "Input file": str(csv_path),
            "Samples": len(t),
            "Sampling rate Hz": f"{result['fs_Hz']:.9f}",
            "Input AC RMS V": f"{rms0:.12g}",
            "Stage-1 AC RMS V": f"{rms1:.12g}",
            "Stage-2 AC RMS V": f"{rms2:.12g}",
            "Stage-1 attenuation dB": f"{attenuation_dB(rms1, rms0):.6f}",
            "Stage-2 attenuation dB": f"{attenuation_dB(rms2, rms0):.6f}",
            "Stage-2 local natural frequency Hz": f"{stage2.fn_Hz:.9f}",
            "Coupled first mode Hz": f"{coupled_fn[0]:.9f}",
            "Coupled second mode Hz": f"{coupled_fn[1]:.9f}",
            "Stage-1 loaded length mm": f"{stage1.loaded_length_mm:.9f}",
            "Stage-2 loaded length mm": f"{stage2.loaded_length_mm:.9f}",
            "L1-L2 margin mm": f"{stage1.loaded_length_mm-stage2.loaded_length_mm:.9f}",
        }

        measured_files = [processed_csv] + plots

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    summary_path = save_summary(
        stage1,
        stage2,
        output_dir,
        measured_summary=measured_summary
    )

    print("\n" + "=" * 82)
    print("OUTPUT FILES")
    print("=" * 82)
    print(design_csv)
    print(frf_csv)
    print(theoretical_plot)

    for p in measured_files:
        print(p)

    print(summary_path)

    print("\n" + "=" * 82)
    print("SAFETY / VALIDATION NOTE")
    print("=" * 82)
    print(
        "This program is an engineering screening/optimization tool, not a "
        "release-to-production certification. Replace preliminary TU0 strength "
        "and fatigue values with certified properties for the actual wire/rod "
        "diameter and cold-work condition. Validate final hooks/end fittings by "
        "proof-load, fatigue, creep/stress-relaxation and manufacturing tests. "
        "Use an independent anti-drop device for the 90 kg suspended mass."
    )

    # --------------------------------------------------------
    # OPTIONAL COMPLETION POPUP
    # --------------------------------------------------------
    try:
        root = tk.Tk()
        root.withdraw()

        messagebox.showinfo(
            "TU0 spring optimization complete",
            "Strict optimization completed.\n\n"
            f"Stage 2 fn = {stage2.fn_Hz:.6f} Hz\n"
            f"Stage 1 loaded length = {stage1.loaded_length_mm:.3f} mm\n"
            f"Stage 2 loaded length = {stage2.loaded_length_mm:.3f} mm\n"
            f"L1-L2 margin = "
            f"{stage1.loaded_length_mm-stage2.loaded_length_mm:.3f} mm\n\n"
            f"Results folder:\n{output_dir}"
        )

        root.destroy()

    except Exception:
        pass


if __name__ == "__main__":
    main()
