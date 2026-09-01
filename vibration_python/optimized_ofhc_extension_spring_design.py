# -*- coding: utf-8 -*-
"""
C10100 / Cu-OFE oxygen-free copper EXTENSION spring optimization
Two-stage vibration isolation:
    Stage 1: three parallel extension springs carry 90 kg
    Stage 2: one extension spring carries 1 kg

DESIGN PRIORITIES
-----------------
1) Safety constraints first.
2) Minimize Stage-1 loaded/equilibrium spring length.
3) Enforce Stage-2 loaded length < Stage-1 loaded length.
4) Within those constraints, maximize vibration isolation.
5) Check BOTH spring-body stress and integral-hook stresses.

This is a preliminary engineering optimization, NOT a release-to-production
safety certification. Final manufacture should use actual C10100 temper/material
certificate, actual hook/end geometry, proof-load test, fatigue test, and creep test.

REFERENCES / FORMULAS
---------------------
- A. M. Wahl, Mechanical Springs, 2nd ed., McGraw-Hill.
- Shigley's Mechanical Engineering Design, helical/extension spring chapter.
- Machinery's Handbook, Extension Spring Design Example.
- Autodesk Inventor Help, Extension Spring Calculation Formulas.
- Copper Development Association, C10100 alloy data.

Key equations:
    C = D/d
    Kw = (4C-1)/(4C-4) + 0.615/C
    k = G*d^4 / (8*D^3*Na)
    F = Fi + k*x
    tau_body = Kw * 8*F*D / (pi*d^3)

Integral hook, Shigley-style:
    C1 = 2*r1/d
    KA = (4*C1^2 - C1 - 1)/(4*C1*(C1-1))
    sigma_A = F * [ KA*16*D/(pi*d^3) + 4/(pi*d^2) ]

    C2 = 2*r2/d
    KB = (4*C2 - 1)/(4*C2 - 4)
    tau_B = KB * 8*F*D/(pi*d^3)

Length model for close-wound extension spring:
    L_body ~= (Na + 1)*d
For a full-loop / machine-hook preliminary geometry, each end projection is
taken as 0.80*(D-d), following the common 75-85% ID proportion used in
Machinery's Handbook design examples.

IMPORTANT:
For a 90 kg safety-critical suspended mass, a mechanically retained end fitting
or separate eye/end-plug is still preferable to a small-radius integral copper hook.
"""

import math
import csv
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 1. USER-ADJUSTABLE INPUTS
# ============================================================

g = 9.81

# Material: representative C10100 / Cu-OFE hard condition.
# Replace with ACTUAL mill certificate values before production.
G_MPa = 44_000.0              # shear modulus ~44 GPa
UTS_MPa = 380.0               # representative hard C10100 value
YIELD_MPa = 345.0             # representative hard C10100 value

# Conservative preliminary design allowables.
# These are intentionally below material ultimate values.
TAU_ALLOW_MPa = 0.35 * UTS_MPa
SIGMA_HOOK_ALLOW_MPa = 0.60 * UTS_MPa

# Additional utilization cap: selected design must use <= 85% of the
# already-conservative allowable under the overload case.
MAX_ALLOWABLE_UTILIZATION = 0.85

OVERLOAD_FACTOR = 1.50

# Initial tension.
# Extension-spring design references commonly use initial tension;
# 10% of nominal force is deliberately modest here.
INITIAL_TENSION_RATIO = 0.10

# Damping ratios used for isolation prediction.
ZETA_STAGE1 = 0.03
ZETA_STAGE2 = 0.03

# Stage 1
M1_kg = 90.0
N_STAGE1_SPRINGS = 3

# Hard envelope on the equilibrium/loaded length of each Stage-1 spring.
# The optimizer will usually choose substantially shorter than this.
STAGE1_MAX_LOADED_LENGTH_mm = 360.0

# Stage 2
M2_kg = 1.0

# Stage-2 must be shorter than Stage-1 in loaded equilibrium.
STAGE2_LENGTH_RATIO_LIMIT = 0.95

# Optimization weights.
# Increasing W_LENGTH_STAGE1 gives a shorter Stage-1 spring but worsens isolation.
# Increasing W_ISOLATION gives a lower natural frequency but a longer spring.
W_LENGTH_STAGE1 = 0.45
W_ISOLATION_STAGE1 = 0.55

# For Stage 2 final isolation is weighted more strongly.
W_LENGTH_STAGE2 = 0.35
W_ISOLATION_STAGE2 = 0.65

# Isolation performance band used by the optimizer.
# Change 10 Hz if your equipment's lowest disturbance frequency is different.
ISO_BAND_MIN_Hz = 10.0
ISO_BAND_MAX_Hz = 100.0

# Search ranges
STAGE1_WIRE_DIAMETERS_mm = np.arange(8.0, 14.01, 0.5)
STAGE1_SPRING_INDEX = np.arange(4.5, 8.01, 0.25)
STAGE1_ACTIVE_COILS = range(8, 35)

STAGE2_WIRE_DIAMETERS_mm = np.arange(1.4, 3.01, 0.1)
STAGE2_SPRING_INDEX = np.arange(4.5, 8.01, 0.25)
STAGE2_ACTIVE_COILS = range(20, 121)

# Hook geometry:
# r1 = D/2 -> C1 = D/d = C
# r2 = 2d  -> C2 = 4
HOOK_R2_OVER_d = 2.0

OUTPUT_DIR = Path("spring_optimization_output")


# ============================================================
# 2. SPRING DESIGN FUNCTIONS
# ============================================================

@dataclass
class SpringDesign:
    stage: str
    d_mm: float
    D_mm: float
    C: float
    Na: int
    OD_mm: float
    ID_mm: float
    k_N_per_mm: float
    initial_tension_N: float
    nominal_force_N: float
    overload_force_N: float
    extension_nominal_mm: float
    body_length_mm: float
    hook_projection_each_mm: float
    free_length_mm: float
    loaded_length_mm: float
    fn_Hz: float
    tau_body_overload_MPa: float
    sigma_hook_A_overload_MPa: float
    tau_hook_B_overload_MPa: float
    utilization: float
    isolation_metric_dB: float


def wahl_factor(C):
    """Wahl stress correction factor."""
    return (4.0*C - 1.0)/(4.0*C - 4.0) + 0.615/C


def spring_rate_N_per_mm(d_mm, D_mm, Na, G_MPa=G_MPa):
    """Helical spring body rate, N/mm."""
    return G_MPa * d_mm**4 / (8.0 * D_mm**3 * Na)


def body_shear_MPa(F_N, d_mm, D_mm):
    """Wahl-corrected torsional shear stress in spring body."""
    C = D_mm / d_mm
    return wahl_factor(C) * 8.0 * F_N * D_mm / (math.pi * d_mm**3)


def hook_stress_A_MPa(F_N, d_mm, D_mm, r1_mm=None):
    """
    Hook root A: bending + direct tensile stress.
    Default r1=D/2 -> C1=D/d.
    """
    if r1_mm is None:
        r1_mm = D_mm / 2.0

    C1 = 2.0 * r1_mm / d_mm
    if C1 <= 1.0:
        return float("inf")

    KA = (4.0*C1**2 - C1 - 1.0) / (4.0*C1*(C1 - 1.0))

    return F_N * (
        KA * 16.0 * D_mm / (math.pi * d_mm**3)
        + 4.0 / (math.pi * d_mm**2)
    )


def hook_stress_B_MPa(F_N, d_mm, D_mm, r2_mm=None):
    """
    Hook side B: torsional stress.
    Default r2=2d, giving C2=4.
    """
    if r2_mm is None:
        r2_mm = HOOK_R2_OVER_d * d_mm

    C2 = 2.0 * r2_mm / d_mm
    if C2 <= 1.0:
        return float("inf")

    KB = (4.0*C2 - 1.0) / (4.0*C2 - 4.0)

    return KB * 8.0 * F_N * D_mm / (math.pi * d_mm**3)


def absolute_transmissibility_1dof(f_Hz, fn_Hz, zeta):
    """Absolute displacement/acceleration transmissibility under base excitation."""
    r = np.asarray(f_Hz, dtype=float) / fn_Hz
    numerator = 1.0 + (2.0*zeta*r)**2
    denominator = (1.0-r**2)**2 + (2.0*zeta*r)**2
    return np.sqrt(numerator / denominator)


def isolation_metric_dB(fn_Hz, zeta):
    """
    Mean 20log10(T) over the specified disturbance band.
    More negative = better isolation.
    """
    freq = np.logspace(
        math.log10(ISO_BAND_MIN_Hz),
        math.log10(ISO_BAND_MAX_Hz),
        250
    )
    T = absolute_transmissibility_1dof(freq, fn_Hz, zeta)
    return float(np.mean(20.0*np.log10(T)))


def preliminary_hook_projection_mm(d_mm, D_mm):
    """
    Preliminary projection from spring body to inside of hook.

    Machinery's Handbook extension-spring example uses a hook projection
    around 75-85% of inside diameter; 80% is used here.
    """
    ID = D_mm - d_mm
    return 0.80 * ID


def evaluate_candidate(stage, d_mm, C, Na, mass_kg, number_parallel, zeta):
    D_mm = C * d_mm
    OD_mm = D_mm + d_mm
    ID_mm = D_mm - d_mm

    # Static load:
    # Stage 1 supports BOTH the 90 kg first-stage body and the 1 kg second-stage payload.
    if stage == "Stage 1":
        F_total_nom = (M1_kg + M2_kg) * g
    else:
        F_total_nom = mass_kg * g

    F_nom = F_total_nom / number_parallel
    F_over = OVERLOAD_FACTOR * F_nom
    Fi = INITIAL_TENSION_RATIO * F_nom

    k = spring_rate_N_per_mm(d_mm, D_mm, Na)

    if k <= 0 or F_nom <= Fi:
        return None

    # Extension after overcoming initial tension.
    x_nom = (F_nom - Fi) / k

    # Close-wound extension-spring body length.
    # Machinery's Handbook example: body length ~= (total coils + 1)*d.
    L_body = (Na + 1.0) * d_mm

    h_hook = preliminary_hook_projection_mm(d_mm, D_mm)
    L_free = L_body + 2.0*h_hook
    L_loaded = L_free + x_nom

    tau_body = body_shear_MPa(F_over, d_mm, D_mm)
    sigma_A = hook_stress_A_MPa(F_over, d_mm, D_mm)
    tau_B = hook_stress_B_MPa(F_over, d_mm, D_mm)

    utilization = max(
        tau_body / TAU_ALLOW_MPa,
        sigma_A / SIGMA_HOOK_ALLOW_MPa,
        tau_B / TAU_ALLOW_MPa,
    )

    k_total_N_per_m = number_parallel * k * 1000.0

    # For Stage 1, use total suspended static mass for the first-mode
    # preliminary frequency estimate.
    modal_mass = (M1_kg + M2_kg) if stage == "Stage 1" else mass_kg
    fn = (1.0/(2.0*math.pi)) * math.sqrt(k_total_N_per_m / modal_mass)
    metric = isolation_metric_dB(fn, zeta)

    return SpringDesign(
        stage=stage,
        d_mm=float(d_mm),
        D_mm=float(D_mm),
        C=float(C),
        Na=int(Na),
        OD_mm=float(OD_mm),
        ID_mm=float(ID_mm),
        k_N_per_mm=float(k),
        initial_tension_N=float(Fi),
        nominal_force_N=float(F_nom),
        overload_force_N=float(F_over),
        extension_nominal_mm=float(x_nom),
        body_length_mm=float(L_body),
        hook_projection_each_mm=float(h_hook),
        free_length_mm=float(L_free),
        loaded_length_mm=float(L_loaded),
        fn_Hz=float(fn),
        tau_body_overload_MPa=float(tau_body),
        sigma_hook_A_overload_MPa=float(sigma_A),
        tau_hook_B_overload_MPa=float(tau_B),
        utilization=float(utilization),
        isolation_metric_dB=float(metric),
    )


# ============================================================
# 3. MULTI-OBJECTIVE OPTIMIZATION
# ============================================================

def normalize(values):
    values = np.asarray(values, dtype=float)
    span = values.max() - values.min()
    if span <= 1e-12:
        return np.zeros_like(values)
    return (values - values.min()) / span


def choose_weighted_knee(candidates, w_length, w_isolation):
    """
    Pick a practical knee point:
      - shorter loaded length is better
      - more-negative isolation_metric_dB is better
    """
    lengths = np.array([c.loaded_length_mm for c in candidates])
    metrics = np.array([c.isolation_metric_dB for c in candidates])

    Lnorm = normalize(lengths)

    # More-negative metric is better. Normalization puts the minimum at zero.
    Inorm = normalize(metrics)

    score = w_length*Lnorm + w_isolation*Inorm
    return candidates[int(np.argmin(score))]


def search_stage1():
    feasible = []

    for d in STAGE1_WIRE_DIAMETERS_mm:
        for C in STAGE1_SPRING_INDEX:
            # Recommended spring index search kept in a practical range.
            if not (4.0 <= C <= 12.0):
                continue

            for Na in STAGE1_ACTIVE_COILS:
                design = evaluate_candidate(
                    stage="Stage 1",
                    d_mm=d,
                    C=C,
                    Na=Na,
                    mass_kg=M1_kg,
                    number_parallel=N_STAGE1_SPRINGS,
                    zeta=ZETA_STAGE1,
                )

                if design is None:
                    continue

                if design.utilization > MAX_ALLOWABLE_UTILIZATION:
                    continue

                if design.loaded_length_mm > STAGE1_MAX_LOADED_LENGTH_mm:
                    continue

                feasible.append(design)

    if not feasible:
        raise RuntimeError("No feasible Stage-1 design. Relax size constraints or enlarge search ranges.")

    return choose_weighted_knee(
        feasible,
        W_LENGTH_STAGE1,
        W_ISOLATION_STAGE1
    ), feasible


def exact_two_stage_isolation_metric_dB(stage1_design, stage2_design):
    """
    Mean final payload transmissibility, 20log10(|X2/Y|),
    over the specified isolation band.
    More negative = better.
    """
    f = np.logspace(
        math.log10(ISO_BAND_MIN_Hz),
        math.log10(ISO_BAND_MAX_Hz),
        250
    )

    H1, H2 = two_dof_transfer(stage1_design, stage2_design, f)
    return float(np.mean(20.0*np.log10(H2)))


def search_stage2(stage1_design):
    feasible = []

    L2_limit = STAGE2_LENGTH_RATIO_LIMIT * stage1_design.loaded_length_mm

    for d in STAGE2_WIRE_DIAMETERS_mm:
        for C in STAGE2_SPRING_INDEX:
            if not (4.0 <= C <= 12.0):
                continue

            for Na in STAGE2_ACTIVE_COILS:
                design = evaluate_candidate(
                    stage="Stage 2",
                    d_mm=d,
                    C=C,
                    Na=Na,
                    mass_kg=M2_kg,
                    number_parallel=1,
                    zeta=ZETA_STAGE2,
                )

                if design is None:
                    continue

                if design.utilization > MAX_ALLOWABLE_UTILIZATION:
                    continue

                # User requirement: Stage-2 loaded length must be less than Stage-1.
                if design.loaded_length_mm >= L2_limit:
                    continue

                # Overwrite the independent 1-DOF metric with the exact
                # two-stage final-payload isolation metric.
                design.isolation_metric_dB = exact_two_stage_isolation_metric_dB(
                    stage1_design, design
                )

                feasible.append(design)

    if not feasible:
        raise RuntimeError("No feasible Stage-2 design under the Stage-1 length constraint.")

    return choose_weighted_knee(
        feasible,
        W_LENGTH_STAGE2,
        W_ISOLATION_STAGE2
    ), feasible


# ============================================================
# 4. EXACT 2-DOF ISOLATION MODEL
# ============================================================

def two_dof_transfer(stage1, stage2, frequencies_Hz):
    """
    Base y -> Stage-1 mass x1 -> Stage-2 mass x2.

    The first stage uses 3 springs in parallel.
    Stage 2 uses one spring suspended from Stage 1.

    Returns |X1/Y| and |X2/Y|.
    """
    m1 = M1_kg
    m2 = M2_kg

    k1 = N_STAGE1_SPRINGS * stage1.k_N_per_mm * 1000.0
    k2 = stage2.k_N_per_mm * 1000.0

    c1 = 2.0*ZETA_STAGE1*math.sqrt(k1*m1)
    c2 = 2.0*ZETA_STAGE2*math.sqrt(k2*m2)

    M = np.array([
        [m1, 0.0],
        [0.0, m2]
    ], dtype=float)

    K = np.array([
        [k1+k2, -k2],
        [-k2,    k2]
    ], dtype=float)

    Cmat = np.array([
        [c1+c2, -c2],
        [-c2,    c2]
    ], dtype=float)

    H1 = np.zeros(len(frequencies_Hz), dtype=complex)
    H2 = np.zeros(len(frequencies_Hz), dtype=complex)

    for i, f in enumerate(frequencies_Hz):
        w = 2.0*math.pi*f

        A = -w*w*M + 1j*w*Cmat + K

        # Base excitation enters Stage-1 through first-stage spring/damper.
        B = np.array([
            k1 + 1j*w*c1,
            0.0
        ], dtype=complex)

        X = np.linalg.solve(A, B)

        H1[i] = X[0]
        H2[i] = X[1]

    return np.abs(H1), np.abs(H2)


# ============================================================
# 5. PSD EXAMPLE + EXPORT
# ============================================================

def example_base_psd(f):
    """
    Illustrative base acceleration PSD only.
    REPLACE with measured PSD for final prediction.
    """
    def log_peak(f0, amplitude, width):
        return amplitude * np.exp(
            -0.5 * (np.log(f/f0)/width)**2
        )

    return (
        2.0e-8
        + log_peak(10.0, 3.0e-6, 0.055)
        + log_peak(25.0, 1.0e-6, 0.050)
        + log_peak(50.0, 4.0e-7, 0.050)
        + log_peak(100.0, 1.5e-7, 0.050)
    )


def print_design(d):
    print("\n" + "="*72)
    print(d.stage)
    print("="*72)
    print(f"Wire diameter d                = {d.d_mm:.3f} mm")
    print(f"Mean coil diameter D           = {d.D_mm:.3f} mm")
    print(f"Spring index C                 = {d.C:.3f}")
    print(f"OD / ID                        = {d.OD_mm:.3f} / {d.ID_mm:.3f} mm")
    print(f"Active coils Na                = {d.Na:d}")
    print(f"Spring rate                    = {d.k_N_per_mm:.6f} N/mm")
    print(f"Initial tension                = {d.initial_tension_N:.3f} N")
    print(f"Nominal force / spring         = {d.nominal_force_N:.3f} N")
    print(f"1.5x overload force / spring   = {d.overload_force_N:.3f} N")
    print(f"Nominal extension              = {d.extension_nominal_mm:.3f} mm")
    print(f"Body length                    = {d.body_length_mm:.3f} mm")
    print(f"Free overall length            = {d.free_length_mm:.3f} mm")
    print(f"Loaded/equilibrium length      = {d.loaded_length_mm:.3f} mm")
    print(f"Natural frequency              = {d.fn_Hz:.3f} Hz")
    print(f"Body shear @ overload          = {d.tau_body_overload_MPa:.3f} MPa")
    print(f"Hook-A stress @ overload       = {d.sigma_hook_A_overload_MPa:.3f} MPa")
    print(f"Hook-B shear @ overload        = {d.tau_hook_B_overload_MPa:.3f} MPa")
    print(f"Allowable utilization          = {100*d.utilization:.1f} %")
    print(f"Mean isolation metric          = {d.isolation_metric_dB:.2f} dB"
          f" over {ISO_BAND_MIN_Hz:g}-{ISO_BAND_MAX_Hz:g} Hz")


def export_design_csv(stage1, stage2):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / "optimized_spring_design.csv"
    rows = []

    for d in [stage1, stage2]:
        row = asdict(d)
        rows.append(row)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return path


def export_frequency_csv(f, H1, H2, psd_in, psd1, psd2):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / "isolation_frequency_psd_data.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "Frequency_Hz",
            "Stage1_2DOF_Transmissibility",
            "Stage2_2DOF_Transmissibility",
            "Base_PSD",
            "After_Stage1_PSD",
            "After_Stage2_PSD",
        ])

        for row in zip(f, H1, H2, psd_in, psd1, psd2):
            writer.writerow(row)

    return path


def make_plots(stage1, stage2):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    f = np.logspace(math.log10(0.2), math.log10(200.0), 1800)

    H1, H2 = two_dof_transfer(stage1, stage2, f)

    psd_in = example_base_psd(f)
    psd_stage1 = psd_in * H1**2
    psd_stage2 = psd_in * H2**2

    # Figure 1: final two-stage transmissibility
    plt.figure(figsize=(9, 5.5))
    plt.loglog(f, H1, label="Stage 1 platform")
    plt.loglog(f, H2, label="Stage 2 payload")
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Absolute transmissibility |X/Y|")
    plt.title("Optimized Two-Stage Extension-Spring Isolation")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    p1 = OUTPUT_DIR / "optimized_two_stage_transmissibility.png"
    plt.savefig(p1, dpi=180)
    plt.close()

    # Figure 2: PSD comparison
    plt.figure(figsize=(9, 5.5))
    plt.loglog(f, psd_in, label="Base input PSD")
    plt.loglog(f, psd_stage1, label="After Stage 1")
    plt.loglog(f, psd_stage2, label="After Stage 2")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Acceleration PSD ((m/s^2)^2/Hz)")
    plt.title("PSD Comparison")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    p2 = OUTPUT_DIR / "optimized_psd_comparison.png"
    plt.savefig(p2, dpi=180)
    plt.close()

    export_frequency_csv(
        f, H1, H2,
        psd_in,
        psd_stage1,
        psd_stage2
    )

    return p1, p2


# ============================================================
# 6. MAIN
# ============================================================

if __name__ == "__main__":

    stage1, feasible1 = search_stage1()
    stage2, feasible2 = search_stage2(stage1)

    print_design(stage1)
    print_design(stage2)

    print("\n" + "="*72)
    print("GEOMETRIC CHECK")
    print("="*72)

    print(
        f"Stage-1 loaded length = {stage1.loaded_length_mm:.2f} mm"
    )
    print(
        f"Stage-2 loaded length = {stage2.loaded_length_mm:.2f} mm"
    )
    print(
        "Stage-2 / Stage-1 loaded-length ratio = "
        f"{stage2.loaded_length_mm/stage1.loaded_length_mm:.3f}"
    )

    assert stage2.loaded_length_mm < stage1.loaded_length_mm
    assert stage1.utilization <= MAX_ALLOWABLE_UTILIZATION
    assert stage2.utilization <= MAX_ALLOWABLE_UTILIZATION

    design_csv = export_design_csv(stage1, stage2)
    plot1, plot2 = make_plots(stage1, stage2)

    print("\nOutput files:")
    print(design_csv)
    print(plot1)
    print(plot2)

    print("\nSAFETY NOTE:")
    print(
        "For a 90 kg suspended mass, use an independent anti-drop safety cable. "
        "Final copper spring/end design requires proof-load, fatigue and creep testing. "
        "If integral hook stresses are undesirable, use mechanically retained end fittings "
        "and separately qualify the end connection."
    )
