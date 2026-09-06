# -*- coding: utf-8 -*-
"""
TU0 two-stage extension-spring optimizer + measured-vibration isolation simulation

Features
--------
1) Wire diameter d and outside diameter OD may be decimal values (printed to 0.1 mm).
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
   - measured PSD before/after isolation
   - user-defined phosphor-bronze single-spring comparison

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
import re
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
ISO_EVAL_MIN_Hz = 0.1
ISO_EVAL_MAX_Hz = 1000.0

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

# Decimal-capable design spaces.
# d and OD are floating-point values and are printed to one decimal place.
# Default step = 0.5 mm to keep the exhaustive search reasonably fast.
# Set GEOMETRY_SEARCH_STEP_MM = 0.1 for a full 0.1-mm search
# (substantially slower).
GEOMETRY_SEARCH_STEP_MM = 0.1

STAGE1_WIRE_DIAMETERS_mm = np.round(
    np.arange(
        5.0,
        12.0 + 0.5 * GEOMETRY_SEARCH_STEP_MM,
        GEOMETRY_SEARCH_STEP_MM,
    ),
    1,
)
STAGE1_OUTSIDE_DIAMETERS_mm = np.round(
    np.arange(
        30.0,
        120.0 + 0.5 * GEOMETRY_SEARCH_STEP_MM,
        GEOMETRY_SEARCH_STEP_MM,
    ),
    1,
)
STAGE1_BODY_COILS = range(4, 181)

STAGE2_WIRE_DIAMETERS_mm = np.round(
    np.arange(
        1.0,
        5.0 + 0.5 * GEOMETRY_SEARCH_STEP_MM,
        GEOMETRY_SEARCH_STEP_MM,
    ),
    1,
)
STAGE2_OUTSIDE_DIAMETERS_mm = np.round(
    np.arange(
        6.0,
        60.0 + 0.5 * GEOMETRY_SEARCH_STEP_MM,
        GEOMETRY_SEARCH_STEP_MM,
    ),
    1,
)
STAGE2_BODY_COILS = range(10, 321)

# ============================================================
# USER-DEFINED SINGLE SPRING FOR DIRECT COMPARISON
# ============================================================
# Change these values directly to the phosphor-bronze spring you want to test.
# Default material is C51000 phosphor bronze.
# Copper Development Association lists modulus of rigidity ~6000 ksi
# which is approximately 41.37 GPa.
CUSTOM_SPRING_ENABLED = True
CUSTOM_SPRING_MATERIAL = "Phosphor Bronze C51000"
CUSTOM_SPRING_G_MPa = 41_370.0

# Geometry: decimal input is allowed; keep one decimal place if desired.
CUSTOM_SPRING_WIRE_DIAMETER_mm = 1.0
CUSTOM_SPRING_OUTSIDE_DIAMETER_mm = 11.0
CUSTOM_SPRING_BODY_COILS = 100

# Hook flexibility model for the custom extension spring.
CUSTOM_SPRING_HOOK_EQUIVALENT_COILS_TOTAL = 1.0

# The mass carried by the SINGLE comparison spring.
# Default: same payload as Stage 2, for a direct comparison.
CUSTOM_SPRING_SUPPORTED_MASS_kg = M2_kg

# Small-amplitude viscous damping ratio for the custom 1-DOF system.
CUSTOM_SPRING_ZETA = 0.03

# PSD logarithmic X-axis begins explicitly at 10^-1 Hz.
PSD_X_MIN_Hz = 1.0e-1

# ============================================================
# PCB 393B04 SENSOR MEASUREMENT FLOOR FOR PSD COMPARISON
# ============================================================
# Datasheet spectral-noise density (typical):
#     1 Hz    : 0.30 ug/sqrt(Hz)
#     10 Hz   : 0.10 ug/sqrt(Hz)
#     100 Hz  : 0.04 ug/sqrt(Hz)
#     1000 Hz : 0.04 ug/sqrt(Hz)
#
# The measured PSD in this program is plotted in g^2/Hz.
# Therefore:
#     noise_PSD [g^2/Hz] = (noise_ASD [g/sqrt(Hz)])^2
#
# IMPORTANT:
# - This is the intrinsic sensor spectral-noise floor from the PCB 393B04
#   datasheet. It does NOT include DAQ/input-amplifier/cable/ADC noise.
# - The datasheet points used here span 1 to 1000 Hz. The code deliberately
#   does NOT extrapolate the noise-floor curve below 1 Hz or above 1000 Hz.
PCB393B04_SHOW_NOISE_FLOOR = True
PCB393B04_NOISE_FREQ_Hz = np.array(
    [1.0, 10.0, 100.0, 1000.0],
    dtype=float,
)
PCB393B04_NOISE_ASD_ug_per_sqrtHz = np.array(
    [0.30, 0.10, 0.04, 0.04],
    dtype=float,
)

# ============================================================
# INPUT VOLTAGE -> ACCELERATION CALIBRATION
# ============================================================
# Sensor sensitivity supplied by user:
#     0.957 V/g
SENSOR_SENSITIVITY_V_PER_G = 0.957

# The code assumes the number written as "gain" is a LINEAR voltage gain.
# Example:
#     filename "..._100gain.csv" -> gain = 100
#     acceleration_g = measured_voltage / (100 * 0.957)
#
# Automatic detection searches:
#   1) the input filename
#   2) the first CSV_SKIP_ROWS header lines
#
# Supported examples include:
#   100gain
#   gain100
#   gain=100
#   gain:100
#   x100
#   100x
#   增益100
#
# If a header explicitly contains "gain = 40 dB", it is converted using
# voltage gain = 10^(dB/20).
AUTO_DETECT_INPUT_GAIN = True

# Set to a number (e.g. 100.0) to override automatic gain detection.
# Leave as None for automatic detection.
MANUAL_INPUT_GAIN_OVERRIDE = None

# Used only if no gain can be detected and no manual override is given.
DEFAULT_INPUT_GAIN = 1.0

# CSV input format
CSV_SKIP_ROWS = 4
CSV_TIME_COLUMN = 0
CSV_SIGNAL_COLUMN = 1

# "auto", "s", "ms", "us"
TIME_UNIT = "auto"

OUTPUT_DIR_NAME = "TU0_isolation_results"

# Time-domain detail plot window, starting from the first valid sample.
# Example: 0.2 = first 0.2 s; 1.0 = first 1 s; 5.0 = first 5 s.
TIME_DETAIL_SECONDS = 1.0


# ============================================================
# 2. DATA STRUCTURE
# ============================================================

@dataclass
class SpringDesign:
    stage: str
    number_parallel: int

    d_mm: float
    OD_mm: float
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


def spring_rate_N_per_mm(d_mm, D_mm, N_eff, G_value_MPa=G_MPa):
    return G_value_MPa * d_mm**4 / (8.0 * D_mm**3 * N_eff)


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



@dataclass
class ReferenceSpringDesign:
    material: str
    d_mm: float
    OD_mm: float
    D_mm: float
    ID_mm: float
    spring_index_C: float
    N_body: int
    N_eff: float
    G_MPa: float
    k_N_per_mm: float
    supported_mass_kg: float
    zeta: float
    natural_frequency_Hz: float


def build_custom_reference_spring():
    """
    Build the user-defined SINGLE phosphor-bronze extension spring.

    Small-amplitude stiffness:
        k = G*d^4 / (8*D^3*N_eff)

    D = OD - d
    N_eff = N_body + hook-equivalent coils

    Initial tension is not required for this linear small-amplitude
    transmissibility calculation. It shifts the static equilibrium as long
    as the spring remains in its linear, opened working region.
    """
    d = round(float(CUSTOM_SPRING_WIRE_DIAMETER_mm), 1)
    OD = round(float(CUSTOM_SPRING_OUTSIDE_DIAMETER_mm), 1)
    N_body = int(CUSTOM_SPRING_BODY_COILS)
    mass = float(CUSTOM_SPRING_SUPPORTED_MASS_kg)
    zeta = float(CUSTOM_SPRING_ZETA)
    G_ref = float(CUSTOM_SPRING_G_MPa)

    if d <= 0.0:
        raise ValueError("CUSTOM_SPRING_WIRE_DIAMETER_mm must be > 0.")
    if OD <= 0.0:
        raise ValueError("CUSTOM_SPRING_OUTSIDE_DIAMETER_mm must be > 0.")
    if N_body <= 0:
        raise ValueError("CUSTOM_SPRING_BODY_COILS must be > 0.")
    if mass <= 0.0:
        raise ValueError("CUSTOM_SPRING_SUPPORTED_MASS_kg must be > 0.")
    if not (0.0 <= zeta < 1.0):
        raise ValueError("CUSTOM_SPRING_ZETA must satisfy 0 <= zeta < 1.")
    if G_ref <= 0.0:
        raise ValueError("CUSTOM_SPRING_G_MPa must be > 0.")

    D = OD - d
    ID = OD - 2.0 * d

    if D <= 0.0 or ID <= 0.0:
        raise ValueError(
            "Invalid custom spring geometry: require OD > 2*d."
        )

    C = D / d
    N_eff = (
        N_body
        + float(CUSTOM_SPRING_HOOK_EQUIVALENT_COILS_TOTAL)
    )

    if N_eff <= 0.0:
        raise ValueError(
            "Custom spring effective coil count must be > 0."
        )

    k = spring_rate_N_per_mm(
        d,
        D,
        N_eff,
        G_value_MPa=G_ref,
    )

    k_N_per_m = k * 1000.0
    fn = (
        1.0
        / (2.0 * math.pi)
        * math.sqrt(k_N_per_m / mass)
    )

    return ReferenceSpringDesign(
        material=CUSTOM_SPRING_MATERIAL,
        d_mm=d,
        OD_mm=OD,
        D_mm=float(D),
        ID_mm=float(ID),
        spring_index_C=float(C),
        N_body=N_body,
        N_eff=float(N_eff),
        G_MPa=G_ref,
        k_N_per_mm=float(k),
        supported_mass_kg=mass,
        zeta=zeta,
        natural_frequency_Hz=float(fn),
    )


def print_reference_spring(s):
    print("\n" + "=" * 64)
    print("USER-DEFINED SINGLE SPRING")
    print("=" * 64)
    print(f"Material                    : {s.material}")
    print(f"Wire diameter d             : {s.d_mm:.1f} mm")
    print(f"Outside diameter OD         : {s.OD_mm:.1f} mm")
    print(f"Mean diameter D             : {s.D_mm:.3f} mm")
    print(f"Inside diameter ID          : {s.ID_mm:.3f} mm")
    print(f"Spring index C              : {s.spring_index_C:.3f}")
    print(f"N_body                      : {s.N_body:d}")
    print(f"N_eff                       : {s.N_eff:.3f}")
    print(f"Shear modulus G             : {s.G_MPa / 1000.0:.3f} GPa")
    print(f"Spring rate                 : {s.k_N_per_mm:.6f} N/mm")
    print(f"Supported mass              : {s.supported_mass_kg:.3f} kg")
    print(f"Damping ratio               : {s.zeta:.4f}")
    print(f"Natural frequency           : {s.natural_frequency_Hz:.6f} Hz")


def single_dof_transfer_complex(reference_spring, frequencies_Hz):
    """
    Absolute base-to-mass transmissibility for the custom 1-DOF spring:

        H = X/Y = (k + j*w*c) / (k - m*w^2 + j*w*c)
    """
    f = np.asarray(frequencies_Hz, dtype=float)

    m = reference_spring.supported_mass_kg
    k = reference_spring.k_N_per_mm * 1000.0
    zeta = reference_spring.zeta
    c = 2.0 * zeta * math.sqrt(k * m)

    w = 2.0 * math.pi * f
    numerator = k + 1j * w * c
    denominator = k - m * w**2 + 1j * w * c

    H = numerator / denominator

    zero_mask = np.abs(w) < 1e-15
    if np.any(zero_mask):
        H = np.asarray(H, dtype=complex)
        H[zero_mask] = 1.0 + 0j

    return H


def save_reference_spring_csv(reference_spring, output_dir):
    path = output_dir / "custom_phosphor_bronze_spring.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow(["Parameter", "Value", "Unit"])
        writer.writerow(["Material", reference_spring.material, ""])
        writer.writerow(["Wire_diameter_d", reference_spring.d_mm, "mm"])
        writer.writerow(["Outside_diameter_OD", reference_spring.OD_mm, "mm"])
        writer.writerow(["Mean_diameter_D", reference_spring.D_mm, "mm"])
        writer.writerow(["Inside_diameter_ID", reference_spring.ID_mm, "mm"])
        writer.writerow(["Spring_index_C", reference_spring.spring_index_C, ""])
        writer.writerow(["N_body", reference_spring.N_body, "turns"])
        writer.writerow(["N_eff", reference_spring.N_eff, "turns"])
        writer.writerow(["Shear_modulus_G", reference_spring.G_MPa, "MPa"])
        writer.writerow(["Spring_rate", reference_spring.k_N_per_mm, "N/mm"])
        writer.writerow(["Supported_mass", reference_spring.supported_mass_kg, "kg"])
        writer.writerow(["Damping_ratio", reference_spring.zeta, ""])
        writer.writerow([
            "Natural_frequency",
            reference_spring.natural_frequency_Hz,
            "Hz",
        ])

    return path


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
    # Preserve decimal geometry and normalize to 0.1 mm.
    d_mm = round(float(d_mm), 1)
    OD_mm = round(float(OD_mm), 1)
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

def _stage_nominal_force_N(stage):
    if stage == "Stage 1":
        total_static_force = (M1_kg + M2_kg) * g
        return (
            total_static_force
            / N_STAGE1_SPRINGS
            * STAGE1_LOAD_SHARE_FACTOR
        )

    if stage == "Stage 2":
        return M2_kg * g

    raise ValueError("Unknown stage.")


def _largest_feasible_N_for_length(
    stage,
    d_mm,
    OD_mm,
    N_min,
    N_max,
    length_limit_mm,
    strict_less=False,
):
    """
    For fixed d and OD, equilibrium length is linear in N_body:

        k = A / (N + hook_eq)
        x = (F-Fi) * (N + hook_eq) / A
        L = N*d + 2*hook_length + x

    Therefore the maximum body-coil count allowed by a length limit
    can be found analytically instead of iterating every N.
    """
    d_mm = round(float(d_mm), 1)
    OD_mm = round(float(OD_mm), 1)

    D_mm = OD_mm - d_mm
    ID_mm = OD_mm - 2.0 * d_mm

    if D_mm <= 0.0 or ID_mm <= 0.0:
        return None

    C = D_mm / d_mm

    if not (C_MIN <= C <= C_MAX):
        return None

    F_nom = _stage_nominal_force_N(stage)
    Fi = initial_tension_N(d_mm, D_mm, C)

    if Fi >= F_nom:
        return None

    if (
        Fi / F_nom
        > MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL
    ):
        return None

    F_proof = PROOF_LOAD_FACTOR * F_nom

    if (
        stress_utilization(F_proof, d_mm, D_mm)
        > MAX_ALLOWABLE_UTILIZATION
    ):
        return None

    # k = A / N_eff
    A = (
        G_MPa
        * d_mm**4
        / (8.0 * D_mm**3)
    )

    if A <= 0.0:
        return None

    q = (F_nom - Fi) / A
    hook_eq = float(HOOK_EQUIVALENT_COILS_TOTAL)
    hook_each = HOOK_LENGTH_TO_OD_RATIO * OD_mm

    # L(N) = a*N + b
    a = d_mm + q
    b = 2.0 * hook_each + q * hook_eq

    if a <= 0.0:
        return None

    effective_limit = float(length_limit_mm)

    if strict_less:
        effective_limit -= 1.0e-9

    N_length_max = math.floor(
        (effective_limit - b) / a
        + 1.0e-12
    )

    N_candidate = min(int(N_max), int(N_length_max))

    if N_candidate < int(N_min):
        return None

    design = evaluate_candidate(
        stage,
        d_mm,
        OD_mm,
        N_candidate,
    )

    if design is None:
        return None

    if strict_less:
        if not (
            design.equilibrium_length_mm
            < length_limit_mm
        ):
            return None
    else:
        if (
            design.equilibrium_length_mm
            > length_limit_mm
        ):
            return None

    return design


def _smallest_feasible_stage1_above_length(
    d_mm,
    OD_mm,
    N_min,
    N_max,
    minimum_length_mm,
):
    """
    For one Stage-1 geometry, find the SHORTEST feasible N_body
    satisfying:
        L1 > minimum_length_mm
        L1 <= STAGE1_MAX_EQUILIBRIUM_LENGTH_mm
    """
    d_mm = round(float(d_mm), 1)
    OD_mm = round(float(OD_mm), 1)

    D_mm = OD_mm - d_mm
    ID_mm = OD_mm - 2.0 * d_mm

    if D_mm <= 0.0 or ID_mm <= 0.0:
        return None

    C = D_mm / d_mm

    if not (C_MIN <= C <= C_MAX):
        return None

    F_nom = _stage_nominal_force_N("Stage 1")
    Fi = initial_tension_N(d_mm, D_mm, C)

    if Fi >= F_nom:
        return None

    if (
        Fi / F_nom
        > MAX_INITIAL_TENSION_FRACTION_OF_NOMINAL
    ):
        return None

    F_proof = PROOF_LOAD_FACTOR * F_nom

    if (
        stress_utilization(F_proof, d_mm, D_mm)
        > MAX_ALLOWABLE_UTILIZATION
    ):
        return None

    A = (
        G_MPa
        * d_mm**4
        / (8.0 * D_mm**3)
    )

    if A <= 0.0:
        return None

    q = (F_nom - Fi) / A
    hook_eq = float(HOOK_EQUIVALENT_COILS_TOTAL)
    hook_each = HOOK_LENGTH_TO_OD_RATIO * OD_mm

    a = d_mm + q
    b = 2.0 * hook_each + q * hook_eq

    if a <= 0.0:
        return None

    # Strictly greater than minimum_length_mm.
    N_required = math.floor(
        (float(minimum_length_mm) - b) / a
        + 1.0e-12
    ) + 1

    N_candidate = max(int(N_min), int(N_required))

    if N_candidate > int(N_max):
        return None

    design = evaluate_candidate(
        "Stage 1",
        d_mm,
        OD_mm,
        N_candidate,
    )

    if design is None:
        return None

    if not (
        design.equilibrium_length_mm
        > minimum_length_mm
    ):
        return None

    if (
        design.equilibrium_length_mm
        > STAGE1_MAX_EQUILIBRIUM_LENGTH_mm
    ):
        return None

    return design


def generate_stage1_candidates():
    """
    Return one maximum-N feasible Stage-1 design for each d/OD pair.
    This is enough to determine the largest Stage-1 length available
    under the 300-mm hard envelope.
    """
    feasible = []

    N_min = min(STAGE1_BODY_COILS)
    N_max = max(STAGE1_BODY_COILS)

    for d in STAGE1_WIRE_DIAMETERS_mm:
        for OD in STAGE1_OUTSIDE_DIAMETERS_mm:
            s = _largest_feasible_N_for_length(
                "Stage 1",
                d,
                OD,
                N_min,
                N_max,
                STAGE1_MAX_EQUILIBRIUM_LENGTH_mm,
                strict_less=False,
            )

            if s is not None:
                feasible.append(s)

    if not feasible:
        raise RuntimeError("No feasible Stage-1 design.")

    return feasible


def generate_stage2_candidates(length_limit_mm):
    """
    Return one maximum-N feasible Stage-2 design for each d/OD pair.
    For fixed geometry, maximum feasible N gives minimum k and minimum fn2.
    """
    feasible = []

    N_min = min(STAGE2_BODY_COILS)
    N_max = max(STAGE2_BODY_COILS)

    for d in STAGE2_WIRE_DIAMETERS_mm:
        for OD in STAGE2_OUTSIDE_DIAMETERS_mm:
            s = _largest_feasible_N_for_length(
                "Stage 2",
                d,
                OD,
                N_min,
                N_max,
                length_limit_mm,
                strict_less=True,
            )

            if s is not None:
                feasible.append(s)

    if not feasible:
        raise RuntimeError("No feasible Stage-2 design.")

    return feasible


def optimize_two_stage():
    """
    Strict priority retained from the user's design intent:

    1) Minimize Stage-2 local natural frequency.
    2) Require L2 + clearance < L1 <= 300 mm.
    3) After fn2 is minimized, choose the SHORTEST compatible Stage-1.
    4) Use lower Stage-1 natural frequency only as a tie-breaker.

    Geometry d and OD are searched at 0.1-mm resolution.
    """
    stage1_max_candidates = generate_stage1_candidates()

    max_L1 = max(
        s.equilibrium_length_mm
        for s in stage1_max_candidates
    )

    stage2_candidates = generate_stage2_candidates(
        max_L1 - STAGE_LENGTH_CLEARANCE_mm
    )

    # First priority: absolutely lowest Stage-2 local fn.
    stage2 = min(
        stage2_candidates,
        key=lambda s: (
            s.local_natural_frequency_Hz,
            s.equilibrium_length_mm,
            -s.max_supported_mass_kg,
            s.OD_mm,
            s.d_mm,
            s.N_body,
        ),
    )

    required_stage1_min = (
        stage2.equilibrium_length_mm
        + STAGE_LENGTH_CLEARANCE_mm
    )

    # Re-search Stage 1 and choose the shortest design that is
    # strictly longer than the selected Stage 2.
    stage1_options = []

    N1_min = min(STAGE1_BODY_COILS)
    N1_max = max(STAGE1_BODY_COILS)

    for d in STAGE1_WIRE_DIAMETERS_mm:
        for OD in STAGE1_OUTSIDE_DIAMETERS_mm:
            s1 = _smallest_feasible_stage1_above_length(
                d,
                OD,
                N1_min,
                N1_max,
                required_stage1_min,
            )

            if s1 is not None:
                stage1_options.append(s1)

    if not stage1_options:
        raise RuntimeError(
            "Selected Stage-2 has no compatible Stage-1."
        )

    stage1 = min(
        stage1_options,
        key=lambda s: (
            s.equilibrium_length_mm,
            s.local_natural_frequency_Hz,
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
    print(f"Wire diameter d            : {s.d_mm:.1f} mm")
    print(f"Outside diameter OD        : {s.OD_mm:.1f} mm")
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



def _valid_gain_value(value):
    try:
        value = float(value)
    except Exception:
        return False
    return np.isfinite(value) and value > 0.0


def detect_input_gain(path, header_lines):
    """
    Detect the acquisition/amplifier voltage gain from:
      1) filename
      2) the first CSV_SKIP_ROWS header lines

    Returns
    -------
    gain_linear : float
        Linear voltage gain.
    source_text : str
        Human-readable description of where the value came from.

    Notes
    -----
    A filename such as:
        stud_FDU_z-direction_startPT_100gain.csv
    is detected as gain = 100.

    If a header explicitly states a dB gain, e.g. "Gain = 40 dB",
    the code converts it to a voltage ratio using 10^(dB/20).
    """
    if MANUAL_INPUT_GAIN_OVERRIDE is not None:
        gain = float(MANUAL_INPUT_GAIN_OVERRIDE)
        if not _valid_gain_value(gain):
            raise ValueError("MANUAL_INPUT_GAIN_OVERRIDE must be > 0.")
        return gain, "manual override"

    if not AUTO_DETECT_INPUT_GAIN:
        return float(DEFAULT_INPUT_GAIN), "default (auto detection disabled)"

    filename_text = Path(path).stem
    header_text = "\n".join(header_lines[:CSV_SKIP_ROWS])

    sources = [
        ("filename", filename_text),
        ("header", header_text),
    ]

    # Higher-priority patterns are checked first.
    linear_patterns = [
        # 100gain, 100_gain
        re.compile(
            r"(?i)(?<![\d.])(\d+(?:\.\d+)?)\s*[_\-\s]*gain\b"
        ),
        # gain100, gain=100, gain:100
        re.compile(
            r"(?i)(?:^|[^A-Za-z0-9])gain\s*[:=_\-\s]*"
            r"(\d+(?:\.\d+)?)(?!\s*dB)"
        ),
        # Chinese header such as 增益100 / 增益:100
        re.compile(
            r"增益\s*[:：=_\-\s]*"
            r"(\d+(?:\.\d+)?)"
        ),
        # x100
        re.compile(
            r"(?i)(?:^|[_\-\s(])x\s*"
            r"(\d+(?:\.\d+)?)"
            r"(?:$|[_\-\s)])"
        ),
        # 100x
        re.compile(
            r"(?i)(?:^|[_\-\s(])"
            r"(\d+(?:\.\d+)?)\s*x"
            r"(?:$|[_\-\s)])"
        ),
    ]

    db_patterns = [
        re.compile(
            r"(?i)(?:^|[^A-Za-z0-9])gain\s*[:=_\-\s]*"
            r"(\d+(?:\.\d+)?)\s*dB\b"
        ),
        re.compile(
            r"增益\s*[:：=_\-\s]*"
            r"(\d+(?:\.\d+)?)\s*dB\b",
            re.IGNORECASE,
        ),
    ]

    # Prefer an explicit filename gain because the user's instrument
    # filenames commonly include forms such as "..._100gain.csv".
    for source_name, source_text in sources:
        for pattern in db_patterns:
            match = pattern.search(source_text)
            if match:
                gain_db = float(match.group(1))
                gain_linear = 10.0 ** (gain_db / 20.0)
                if _valid_gain_value(gain_linear):
                    return (
                        gain_linear,
                        f"{source_name}: {gain_db:g} dB",
                    )

        for pattern in linear_patterns:
            match = pattern.search(source_text)
            if match:
                gain_linear = float(match.group(1))
                if _valid_gain_value(gain_linear):
                    return (
                        gain_linear,
                        f"{source_name}: {match.group(0)}",
                    )

    return float(DEFAULT_INPUT_GAIN), "default: gain not found"


def voltage_to_acceleration_g(voltage_V, gain_linear):
    """
    Convert measured amplified voltage to acceleration in g.

        sensor_voltage = measured_voltage / gain
        acceleration_g = sensor_voltage / sensitivity

    Therefore:
        acceleration_g
        = measured_voltage / (gain * SENSOR_SENSITIVITY_V_PER_G)
    """
    gain_linear = float(gain_linear)

    if not _valid_gain_value(gain_linear):
        raise ValueError("Input gain must be > 0.")

    sensitivity = float(SENSOR_SENSITIVITY_V_PER_G)

    if not _valid_gain_value(sensitivity):
        raise ValueError("SENSOR_SENSITIVITY_V_PER_G must be > 0.")

    return (
        np.asarray(voltage_V, dtype=float)
        / (gain_linear * sensitivity)
    )


def save_input_calibration_csv(
    input_path,
    detected_gain,
    gain_source,
    output_dir,
):
    path = output_dir / "input_calibration.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow(["Parameter", "Value", "Unit"])
        writer.writerow(["Input_file", str(input_path), ""])
        writer.writerow(["Detected_voltage_gain", detected_gain, "x"])
        writer.writerow(["Gain_detection_source", gain_source, ""])
        writer.writerow([
            "Sensor_sensitivity",
            SENSOR_SENSITIVITY_V_PER_G,
            "V/g",
        ])
        writer.writerow([
            "Conversion_formula",
            "acceleration_g = measured_voltage_V / "
            "(gain * sensitivity_V_per_g)",
            "",
        ])

    return path


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

    header_lines = lines[:CSV_SKIP_ROWS]
    detected_gain, gain_source = detect_input_gain(
        path,
        header_lines,
    )

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
        voltage_field = row[CSV_SIGNAL_COLUMN].strip().strip('"')

        if delimiter == ";":
            t_field = t_field.replace(",", ".")
            voltage_field = voltage_field.replace(",", ".")

        try:
            t_value = float(t_field)
            voltage_value = float(voltage_field)
        except ValueError:
            continue

        if np.isfinite(t_value) and np.isfinite(voltage_value):
            parsed.append((t_value, voltage_value))

    if len(parsed) < 16:
        raise ValueError("Too few valid numeric samples found.")

    arr = np.asarray(parsed, dtype=float)

    t_raw = arr[:, 0]
    voltage_raw = arr[:, 1]

    order = np.argsort(t_raw)
    t_raw = t_raw[order]
    voltage_raw = voltage_raw[order]

    keep = np.concatenate([[True], np.diff(t_raw) > 0])
    t_raw = t_raw[keep]
    voltage_raw = voltage_raw[keep]

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
    print(f"Detected input gain         : {detected_gain:.6g} x")
    print(f"Gain detection source       : {gain_source}")
    print(
        f"Sensor sensitivity          : "
        f"{SENSOR_SENSITIVITY_V_PER_G:.6g} V/g"
    )
    print(
        "Voltage -> acceleration     : "
        "a[g] = Vmeasured / (gain * sensitivity)"
    )

    # FFT requires uniform sampling.
    if rel_jitter > 1e-3:
        t_uniform = np.linspace(t[0], t[-1], len(t))
        voltage_raw = np.interp(
            t_uniform,
            t,
            voltage_raw,
        )
        t = t_uniform
        dt_med = float(np.median(np.diff(t)))
        fs = 1.0 / dt_med
        print("Time data resampled to uniform grid.")

    acceleration_g = voltage_to_acceleration_g(
        voltage_raw,
        detected_gain,
    )

    return (
        t,
        acceleration_g,
        fs,
        voltage_raw,
        detected_gain,
        gain_source,
    )


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

def save_theoretical_transmissibility(
    stage1,
    stage2,
    reference_spring,
    output_dir,
):
    f = np.logspace(
        math.log10(ISO_EVAL_MIN_Hz),
        math.log10(ISO_EVAL_MAX_Hz),
        1600,
    )

    H1, H2 = two_dof_transfer_complex(stage1, stage2, f)
    H_ref = single_dof_transfer_complex(reference_spring, f)

    path = output_dir / "01_theoretical_transmissibility.png"

    plt.figure(figsize=(9, 5.5))
    plt.loglog(f, np.abs(H1), label="TU0 Stage 1")
    plt.loglog(f, np.abs(H2), label="TU0 Stage 2")
    plt.loglog(
        f,
        np.abs(H_ref),
        label=f"{reference_spring.material} single spring",
    )
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Transmissibility |X/Y|")
    plt.title("Isolation Transmissibility Comparison")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.xlim(ISO_EVAL_MIN_Hz, ISO_EVAL_MAX_Hz)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def save_measured_time_plot(
    t,
    x_in,
    x_stage1,
    x_stage2,
    x_reference,
    reference_spring,
    output_dir,
):
    path = output_dir / "02_measured_time_before_after.png"

    plt.figure(figsize=(10, 5.5))
    plt.plot(t, x_in, linewidth=0.9, label="Input")
    plt.plot(t, x_stage1, linewidth=0.9, label="After TU0 Stage 1")
    plt.plot(t, x_stage2, linewidth=0.9, label="After TU0 Stage 2")
    plt.plot(
        t,
        x_reference,
        linewidth=0.9,
        label=f"After {reference_spring.material} single spring",
    )
    plt.xlabel("Time (s)")
    plt.ylabel("Acceleration (g)")
    plt.title("Signal Before and After Isolation")
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


def save_measured_time_detail_plot(
    t,
    x_in,
    x_stage1,
    x_stage2,
    x_reference,
    reference_spring,
    output_dir,
    detail_seconds=TIME_DETAIL_SECONDS,
):
    """Detailed time-domain comparison."""
    if len(t) < 2:
        raise ValueError("Too few time samples for detail plot.")

    t = np.asarray(t, dtype=float)
    x_in = np.asarray(x_in, dtype=float)
    x_stage1 = np.asarray(x_stage1, dtype=float)
    x_stage2 = np.asarray(x_stage2, dtype=float)
    x_reference = np.asarray(x_reference, dtype=float)

    t0 = float(t[0])
    t1_requested = t0 + float(detail_seconds)
    t1 = min(t1_requested, float(t[-1]))
    mask = (t >= t0) & (t <= t1)

    if np.count_nonzero(mask) < 10:
        n_detail = min(len(t), max(10, len(t) // 20))
        mask = np.zeros(len(t), dtype=bool)
        mask[:n_detail] = True

    path = output_dir / "02b_measured_time_before_after_detail.png"

    plt.figure(figsize=(10, 5.5))
    plt.plot(t[mask], x_in[mask], linewidth=0.9, label="Input")
    plt.plot(
        t[mask],
        x_stage1[mask],
        linewidth=0.9,
        label="After TU0 Stage 1",
    )
    plt.plot(
        t[mask],
        x_stage2[mask],
        linewidth=0.9,
        label="After TU0 Stage 2",
    )
    plt.plot(
        t[mask],
        x_reference[mask],
        linewidth=0.9,
        label=f"After {reference_spring.material} single spring",
    )
    plt.xlabel("Time (s)")
    plt.ylabel("Acceleration (g)")
    plt.title(
        f"Measured Signal Detail: First "
        f"{t[mask][-1] - t[mask][0]:.3f} s"
    )
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def pcb393b04_noise_lpsd_g_per_sqrtHz(frequency_Hz):
    """
    PCB 393B04 intrinsic sensor spectral-noise floor in g/sqrt(Hz).

    IMPORTANT DEFINITION USED IN THIS PROGRAM
    -----------------------------------------
    Here "LPSD" means the square root of the one-sided PSD:

        LPSD(f) = sqrt(PSD(f))

    Therefore:
        PSD  unit  = g^2/Hz
        LPSD unit  = g/sqrt(Hz)

    This quantity is also commonly called ASD
    (Amplitude Spectral Density).

    PCB 393B04 datasheet spectral-noise points:
        1 Hz    : 0.30 ug/sqrt(Hz)
        10 Hz   : 0.10 ug/sqrt(Hz)
        100 Hz  : 0.04 ug/sqrt(Hz)
        1000 Hz : 0.04 ug/sqrt(Hz)

    The datasheet points are interpolated in log(f)-log(amplitude)
    space. Frequencies outside 1...1000 Hz return NaN; the code does
    not extrapolate the specified sensor noise floor.
    """
    f = np.asarray(frequency_Hz, dtype=float)

    result = np.full(f.shape, np.nan, dtype=float)

    f_spec = np.asarray(
        PCB393B04_NOISE_FREQ_Hz,
        dtype=float,
    )
    lpsd_spec_ug = np.asarray(
        PCB393B04_NOISE_ASD_ug_per_sqrtHz,
        dtype=float,
    )

    valid = (
        np.isfinite(f)
        & (f >= f_spec[0])
        & (f <= f_spec[-1])
        & (f > 0.0)
    )

    if not np.any(valid):
        return result

    # Log-log interpolation for the datasheet spectral-noise density.
    log_lpsd_ug = np.interp(
        np.log10(f[valid]),
        np.log10(f_spec),
        np.log10(lpsd_spec_ug),
    )
    lpsd_ug = 10.0**log_lpsd_ug

    # ug/sqrt(Hz) -> g/sqrt(Hz)
    result[valid] = lpsd_ug * 1.0e-6

    return result


def pcb393b04_noise_psd_g2_per_Hz(frequency_Hz):
    """
    PCB 393B04 intrinsic sensor noise floor in g^2/Hz.

    Since:
        LPSD = sqrt(PSD)

    then:
        PSD = LPSD^2
    """
    lpsd = pcb393b04_noise_lpsd_g_per_sqrtHz(frequency_Hz)
    return lpsd**2

def one_sided_psd(signal, fs):
    """
    One-sided PSD using a Hann window.

    Returns
    -------
    freq : ndarray
        One-sided frequency vector in Hz.
    psd : ndarray
        One-sided PSD in signal_unit^2/Hz.
    """
    x = np.asarray(signal, dtype=float)

    if len(x) < 8:
        raise ValueError("Too few samples for PSD calculation.")

    x = x - np.mean(x)

    n = len(x)
    window = np.hanning(n)
    window_power = float(np.sum(window**2))

    if window_power <= 0.0:
        raise ValueError("Invalid Hann window power.")

    Xw = np.fft.rfft(x * window)
    freq = np.fft.rfftfreq(n, d=1.0 / fs)

    psd = (np.abs(Xw) ** 2) / (fs * window_power)

    if n % 2 == 0:
        if len(psd) > 2:
            psd[1:-1] *= 2.0
    else:
        if len(psd) > 1:
            psd[1:] *= 2.0

    return freq, psd


def save_measured_psd_plot(
    x_in,
    x_stage1,
    x_stage2,
    x_reference,
    reference_spring,
    fs,
    output_dir,
):
    """
    Measured PSD comparison with logarithmic X and Y axes.
    X-axis starts explicitly at 10^-1 Hz.
    """
    freq, psd_in = one_sided_psd(x_in, fs)
    freq1, psd_stage1 = one_sided_psd(x_stage1, fs)
    freq2, psd_stage2 = one_sided_psd(x_stage2, fs)
    freq_ref, psd_reference = one_sided_psd(x_reference, fs)

    pcb_noise_psd = pcb393b04_noise_psd_g2_per_Hz(freq)

    if not (
        np.allclose(freq, freq1)
        and np.allclose(freq, freq2)
        and np.allclose(freq, freq_ref)
    ):
        raise RuntimeError("PSD frequency vectors do not match.")

    upper_limit = min(
        float(ISO_EVAL_MAX_Hz),
        float(fs) / 2.0,
    )

    mask = (
        (freq >= PSD_X_MIN_Hz)
        & (freq <= upper_limit)
        & np.isfinite(psd_in)
        & np.isfinite(psd_stage1)
        & np.isfinite(psd_stage2)
        & np.isfinite(psd_reference)
    )

    if np.count_nonzero(mask) < 2:
        raise ValueError(
            "Not enough PSD points at or above 0.1 Hz. "
            "A longer record may be required."
        )

    path = output_dir / "04_measured_PSD_before_after.png"

    plt.figure(figsize=(9, 5.5))
    plt.loglog(
        freq[mask],
        np.maximum(psd_in[mask], 1e-300),
        linewidth=1.2,
        linestyle="--",
        color="gray",
        label="Input",
    )
    plt.loglog(
        freq[mask],
        np.maximum(psd_stage1[mask], 1e-300),
        linewidth=1.0,
        label="After TU0 Stage 1",
    )
    plt.loglog(
        freq[mask],
        np.maximum(psd_stage2[mask], 1e-300),
        linewidth=1.0,
        label="After TU0 Stage 2",
    )
    plt.loglog(
        freq[mask],
        np.maximum(psd_reference[mask], 1e-300),
        linewidth=1.0,
        label=f"After {reference_spring.material} single spring",
    )

    if PCB393B04_SHOW_NOISE_FLOOR:
        pcb_mask = (
            mask
            & np.isfinite(pcb_noise_psd)
            & (pcb_noise_psd > 0.0)
        )

        if np.count_nonzero(pcb_mask) >= 2:
            plt.loglog(
                freq[pcb_mask],
                pcb_noise_psd[pcb_mask],
                linewidth=1.5,
                linestyle=":",
                label="PCB 393B04 sensor noise floor",
            )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Acceleration PSD (g$^2$/Hz)")
    plt.title("PSD Before and After Isolation")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.xlim(PSD_X_MIN_Hz, upper_limit)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    csv_path = output_dir / "measured_PSD_before_after.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Input_PSD",
            "After_TU0_Stage1_PSD",
            "After_TU0_Stage2_PSD",
            "After_PhosphorBronze_SingleSpring_PSD",
            "PCB_393B04_Sensor_NoiseFloor_PSD_g2_per_Hz",
        ])

        for row in zip(
            freq[mask],
            psd_in[mask],
            psd_stage1[mask],
            psd_stage2[mask],
            psd_reference[mask],
            pcb_noise_psd[mask],
        ):
            writer.writerow(row)

    return path, csv_path



def save_measured_lpsd_plot(
    x_in,
    x_stage1,
    x_stage2,
    x_reference,
    reference_spring,
    fs,
    output_dir,
):
    """
    Measured LPSD comparison.

    Definition used here:
        LPSD(f) = sqrt(PSD(f))

    where PSD is the one-sided acceleration PSD produced by
    one_sided_psd().

    Units:
        PSD  : g^2/Hz
        LPSD : g/sqrt(Hz)

    In vibration/noise work this same quantity is also commonly called
    ASD (Amplitude Spectral Density).

    Both X and Y axes are logarithmic because LPSD is a linear spectral
    density, NOT a dB quantity.
    """
    freq, psd_in = one_sided_psd(x_in, fs)
    freq1, psd_stage1 = one_sided_psd(x_stage1, fs)
    freq2, psd_stage2 = one_sided_psd(x_stage2, fs)
    freq_ref, psd_reference = one_sided_psd(x_reference, fs)

    if not (
        np.allclose(freq, freq1)
        and np.allclose(freq, freq2)
        and np.allclose(freq, freq_ref)
    ):
        raise RuntimeError("LPSD/PSD frequency vectors do not match.")

    # Correct LPSD conversion:
    #     LPSD = sqrt(PSD)
    # PSD is non-negative theoretically; clip tiny numerical negatives.
    lpsd_in = np.sqrt(np.maximum(psd_in, 0.0))
    lpsd_stage1 = np.sqrt(np.maximum(psd_stage1, 0.0))
    lpsd_stage2 = np.sqrt(np.maximum(psd_stage2, 0.0))
    lpsd_reference = np.sqrt(np.maximum(psd_reference, 0.0))

    # PCB datasheet spectral noise is already an amplitude density.
    pcb_noise_lpsd = pcb393b04_noise_lpsd_g_per_sqrtHz(freq)

    upper_limit = min(
        float(ISO_EVAL_MAX_Hz),
        float(fs) / 2.0,
    )

    mask = (
        (freq >= PSD_X_MIN_Hz)
        & (freq <= upper_limit)
        & np.isfinite(lpsd_in)
        & np.isfinite(lpsd_stage1)
        & np.isfinite(lpsd_stage2)
        & np.isfinite(lpsd_reference)
    )

    if np.count_nonzero(mask) < 2:
        raise ValueError(
            "Not enough LPSD points at or above 0.1 Hz. "
            "A longer record may be required."
        )

    path = output_dir / "05_measured_LPSD_before_after.png"

    # Avoid zeros on a logarithmic Y-axis only for plotting.
    plot_floor = np.finfo(float).tiny

    plt.figure(figsize=(9, 5.5))
    plt.loglog(
        freq[mask],
        np.maximum(lpsd_in[mask], plot_floor),
        linewidth=1.2,
        linestyle="--",
        color="gray",
        label="Input",
    )
    plt.loglog(
        freq[mask],
        np.maximum(lpsd_stage1[mask], plot_floor),
        linewidth=1.0,
        label="After TU0 Stage 1",
    )
    plt.loglog(
        freq[mask],
        np.maximum(lpsd_stage2[mask], plot_floor),
        linewidth=1.0,
        label="After TU0 Stage 2",
    )
    plt.loglog(
        freq[mask],
        np.maximum(lpsd_reference[mask], plot_floor),
        linewidth=1.0,
        label=f"After {reference_spring.material} single spring",
    )

    if PCB393B04_SHOW_NOISE_FLOOR:
        pcb_mask = (
            mask
            & np.isfinite(pcb_noise_lpsd)
            & (pcb_noise_lpsd > 0.0)
        )

        if np.count_nonzero(pcb_mask) >= 2:
            plt.loglog(
                freq[pcb_mask],
                pcb_noise_lpsd[pcb_mask],
                linewidth=1.5,
                linestyle=":",
                label="PCB 393B04 sensor noise floor",
            )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel(r"Acceleration LPSD (g/$\sqrt{\mathrm{Hz}}$)")
    plt.title("LPSD Before and After Isolation")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.xlim(PSD_X_MIN_Hz, upper_limit)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    csv_path = output_dir / "measured_LPSD_before_after.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Input_LPSD_g_per_sqrtHz",
            "After_TU0_Stage1_LPSD_g_per_sqrtHz",
            "After_TU0_Stage2_LPSD_g_per_sqrtHz",
            "After_PhosphorBronze_SingleSpring_LPSD_g_per_sqrtHz",
            "PCB_393B04_Sensor_NoiseFloor_LPSD_g_per_sqrtHz",
        ])

        for row in zip(
            freq[mask],
            lpsd_in[mask],
            lpsd_stage1[mask],
            lpsd_stage2[mask],
            lpsd_reference[mask],
            pcb_noise_lpsd[mask],
        ):
            writer.writerow(row)

    return path, csv_path

def save_transfer_csv(
    stage1,
    stage2,
    reference_spring,
    output_dir,
):
    f = np.linspace(0.0, ISO_EVAL_MAX_Hz, 2001)
    H1, H2 = two_dof_transfer_complex(stage1, stage2, f)
    H_ref = single_dof_transfer_complex(reference_spring, f)

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
            "PhosphorBronze_Single_Magnitude",
            "PhosphorBronze_Single_dB",
            "PhosphorBronze_Single_Phase_deg",
        ])

        for fi, h1, h2, href in zip(f, H1, H2, H_ref):
            m1 = abs(h1)
            m2 = abs(h2)
            mr = abs(href)

            writer.writerow([
                fi,
                m1,
                20.0 * math.log10(max(m1, 1e-300)),
                np.angle(h1, deg=True),
                m2,
                20.0 * math.log10(max(m2, 1e-300)),
                np.angle(h2, deg=True),
                mr,
                20.0 * math.log10(max(mr, 1e-300)),
                np.angle(href, deg=True),
            ])

    return path


def save_processed_signal_csv(
    t,
    raw_voltage_V,
    detected_gain,
    x_in,
    x_stage1,
    x_stage2,
    x_reference,
    output_dir,
):
    path = output_dir / "measured_signal_before_after.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Time_s",
            "Raw_Input_Voltage_V",
            "Detected_Gain_x",
            "Input_Acceleration_g",
            "After_TU0_Stage1_g",
            "After_TU0_Stage2_g",
            "After_PhosphorBronze_SingleSpring_g",
        ])

        for row in zip(
            t,
            raw_voltage_V,
            np.full(len(t), detected_gain),
            x_in,
            x_stage1,
            x_stage2,
            x_reference,
        ):
            writer.writerow(row)

    return path


# ============================================================
# 11. MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # FILE PICKER FIRST
    # --------------------------------------------------------
    input_path = pick_input_file()

    if input_path is None:
        print("\nNo measured file selected. Program stopped.")
        return

    print(f"\nSelected measured file      : {input_path}")

    (
        t,
        x_in,
        fs,
        raw_voltage_V,
        detected_gain,
        gain_source,
    ) = load_time_signal(input_path)

    # --------------------------------------------------------
    # USER-DEFINED PHOSPHOR-BRONZE SINGLE SPRING
    # --------------------------------------------------------
    reference_spring = build_custom_reference_spring()
    print_reference_spring(reference_spring)

    if not (4.0 <= reference_spring.spring_index_C <= 12.0):
        print(
            "\nWARNING: custom phosphor-bronze spring index C is outside "
            "the usual 4-12 preliminary design range."
        )

    # --------------------------------------------------------
    # TU0 TWO-STAGE SPRING OPTIMIZATION
    # --------------------------------------------------------
    stage1, stage2 = optimize_two_stage()

    print_compact_design(stage1)
    print_compact_design(stage2)

    coupled_modes = two_dof_undamped_natural_frequencies_Hz(
        stage1,
        stage2,
    )

    print(
        "\nCoupled TU0 natural frequencies : "
        + ", ".join(f"{x:.3f} Hz" for x in coupled_modes)
    )

    print(
        f"Stage-2 local natural frequency: "
        f"{stage2.local_natural_frequency_Hz:.6f} Hz"
    )

    output_dir = input_path.parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    calibration_csv = save_input_calibration_csv(
        input_path,
        detected_gain,
        gain_source,
        output_dir,
    )

    # --------------------------------------------------------
    # THEORETICAL TRANSMISSIBILITY
    # --------------------------------------------------------
    p1 = save_theoretical_transmissibility(
        stage1,
        stage2,
        reference_spring,
        output_dir,
    )

    transfer_csv = save_transfer_csv(
        stage1,
        stage2,
        reference_spring,
        output_dir,
    )

    reference_csv = save_reference_spring_csv(
        reference_spring,
        output_dir,
    )

    # --------------------------------------------------------
    # MEASURED-SIGNAL ISOLATION SIMULATION
    # --------------------------------------------------------
    freq, X, H1, H2, x_stage1, x_stage2 = process_measured_signal(
        stage1,
        stage2,
        t,
        x_in,
    )

    H_reference = single_dof_transfer_complex(
        reference_spring,
        freq,
    )
    X_reference = X * H_reference
    x_reference = np.fft.irfft(
        X_reference,
        n=len(x_in),
    )

    p2_full = save_measured_time_plot(
        t,
        x_in,
        x_stage1,
        x_stage2,
        x_reference,
        reference_spring,
        output_dir,
    )

    p2_detail = save_measured_time_detail_plot(
        t,
        x_in,
        x_stage1,
        x_stage2,
        x_reference,
        reference_spring,
        output_dir,
        detail_seconds=TIME_DETAIL_SECONDS,
    )

    p4, psd_csv = save_measured_psd_plot(
        x_in,
        x_stage1,
        x_stage2,
        x_reference,
        reference_spring,
        fs,
        output_dir,
    )

    p5, lpsd_csv = save_measured_lpsd_plot(
        x_in,
        x_stage1,
        x_stage2,
        x_reference,
        reference_spring,
        fs,
        output_dir,
    )

    processed_csv = save_processed_signal_csv(
        t,
        raw_voltage_V,
        detected_gain,
        x_in,
        x_stage1,
        x_stage2,
        x_reference,
        output_dir,
    )

    print("\n" + "=" * 72)
    print("OUTPUT FILES")
    print("=" * 72)
    print(f"Theoretical transmissibility : {p1}")
    print(f"Time-domain full plot         : {p2_full}")
    print(f"Time-domain detail plot       : {p2_detail}")
    print(f"Measured PSD log-log plot     : {p4}")
    print(f"Measured LPSD log-log plot    : {p5}")
    print(f"Transfer CSV                  : {transfer_csv}")
    print(f"Processed time CSV            : {processed_csv}")
    print(f"Measured PSD CSV              : {psd_csv}")
    print(f"Measured LPSD CSV             : {lpsd_csv}")
    print(f"Reference spring CSV          : {reference_csv}")
    print(f"Input calibration CSV         : {calibration_csv}")
    print(f"Output directory              : {output_dir}")

    # All figures are saved only. No interactive plot display.


if __name__ == "__main__":
    main()
