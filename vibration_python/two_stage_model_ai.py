#!/usr/bin/env python3
"""
Cryogenic two-stage helical extension-spring design tool.

Baseline problem
----------------
Stage-1 moving mass m1 = 90.0 kg
Stage-2 detector mass m2 = 0.8 kg
Three identical primary springs
One secondary spring

IMPORTANT
---------
This is a preliminary engineering-design calculator, not a substitute for
material certification, detailed FEA, end-hook/termination analysis, proof
testing, or cryogenic qualification.

The script deliberately includes effects often omitted in a first-pass model:
  * primary springs support m1 + m2;
  * spring self-weight in static extension and top-coil stress;
  * spring distributed mass in the two-DOF modal model (consistent-mass approx.);
  * three-point load imbalance factor;
  * proof-load factor;
  * cold-vs-room-temperature shear-modulus sensitivity;
  * Wahl curvature correction for coil-body shear stress;
  * automatic geometry scans under OD/length constraints;
  * base-to-detector transfer function.

For an extension spring, the end hooks / eyes / terminations can be the
critical locations.  The Wahl-stress calculation below applies to the helical
coil body and DOES NOT qualify the end geometry.

Material-property basis
-----------------------
- CDA C10100 room-temperature modulus of rigidity: about 6400 ksi (~44.1 GPa).
- NIST Monograph 177 fit for annealed oxygen-free copper, 4-300 K:
      G(T) [GPa] = 51.2 - 4.63e-5 T^2
  The NIST fit is NOT valid below 4 K.  For a mK apparatus, 51.2 GPa is used
  only as a 4 K proxy / design sensitivity point.  The assembled cold spring
  rate should be measured.

Author: generated for the two-stage cryogenic suspension design study.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

G0 = 9.80665
RHO_CU = 8940.0  # kg/m^3, nominal C10100 density from specific gravity 8.94


@dataclass
class SystemConfig:
    # Moving payload masses; spring masses are added separately.
    m1_kg: float = 90.0
    m2_kg: float = 0.8

    n_primary: int = 3
    n_secondary: int = 1

    # Desired coupled-mode region.  These are design targets, not guaranteed
    # optimum values until the measured cryostat vibration spectrum is known.
    target_mode1_hz: float = 2.0
    target_mode2_hz: float = 3.5

    # Damping is uncertain at mK.  It is used only for transfer-function plots.
    zeta1: float = 0.02
    zeta2: float = 0.02

    # Equal-load assumption is never perfect.  1.15 means the most-loaded
    # primary spring is allowed to carry 15% above the nominal payload share.
    primary_load_imbalance_factor: float = 1.15

    # Example proof-load factor applied on top of the imbalanced design load.
    # Replace with your collaboration / lab requirement.
    proof_factor: float = 1.50

    # Geometry limits used by the scanner.  EDIT to match your cryostat.
    primary_max_od_mm: float = 140.0
    primary_max_working_body_mm: float = 320.0
    secondary_max_od_mm: float = 35.0
    secondary_max_working_body_mm: float = 100.0

    # Cold design modulus.  NIST's annealed-Cu fit tends to ~51.2 GPa at 4 K.
    # This is a 4 K proxy, not a validated 70 mK value.
    G_cold_proxy_pa: float = 51.2e9

    # CDA room-temperature reference.
    G_room_pa: float = 44.1e9

    # Candidate frequency windows for geometry filtering.
    primary_local_f_window_hz: tuple[float, float] = (1.75, 2.25)
    secondary_local_f_window_hz: tuple[float, float] = (2.8, 4.2)

    # Optional measured excitation lines. Leave empty until you have a PSD.
    # Example ONLY, do not use blindly:
    # excitation_lines_hz: tuple[float, ...] = (1.4, 2.8, 4.2, 5.6, 7.0)
    excitation_lines_hz: tuple[float, ...] = ()


@dataclass
class SpringGeometry:
    d_mm: float
    D_mm: float
    active_turns: int

    @property
    def d_m(self) -> float:
        return self.d_mm * 1e-3

    @property
    def D_m(self) -> float:
        return self.D_mm * 1e-3

    @property
    def spring_index(self) -> float:
        return self.D_mm / self.d_mm

    @property
    def od_mm(self) -> float:
        return self.D_mm + self.d_mm


# ---------------------------------------------------------------------------
# Material and basic spring equations
# ---------------------------------------------------------------------------

def nist_annealed_ofe_shear_modulus_pa(T_K: float) -> float:
    """
    NIST Monograph 177 regression for annealed oxygen-free copper.
    Valid only for 4 K <= T <= 300 K.
    """
    if not 4.0 <= T_K <= 300.0:
        raise ValueError("NIST annealed-Cu G(T) fit is valid only from 4 K to 300 K.")
    return (51.2 - 4.63e-5 * T_K**2) * 1e9


def wahl_factor(C: float) -> float:
    if C <= 1.0:
        raise ValueError("Spring index C must be > 1.")
    return (4.0*C - 1.0)/(4.0*C - 4.0) + 0.615/C


def spring_rate_N_per_m(G_pa: float, geom: SpringGeometry) -> float:
    """Close-coiled round-wire helical spring rate."""
    d, D, N = geom.d_m, geom.D_m, geom.active_turns
    return G_pa * d**4 / (8.0 * D**3 * N)


def coil_wire_length_m(geom: SpringGeometry) -> float:
    """
    Active-coil wire length only.  End loops/hooks are NOT included.
    """
    return math.pi * geom.D_m * geom.active_turns


def spring_body_mass_kg(geom: SpringGeometry, rho=RHO_CU) -> float:
    A = math.pi * geom.d_m**2 / 4.0
    return rho * A * coil_wire_length_m(geom)


def coil_body_shear_stress_pa(force_N: float, geom: SpringGeometry) -> float:
    """
    Wahl-corrected maximum coil-body shear stress under axial force.

    This DOES NOT calculate extension-spring hook / eye stresses.
    """
    C = geom.spring_index
    return wahl_factor(C) * 8.0 * force_N * geom.D_m / (math.pi * geom.d_m**3)


def extension_due_payload_and_self_weight_m(
    payload_force_N: float,
    spring_mass_kg: float,
    rate_N_per_m: float,
) -> float:
    """
    Approximate static extension of a vertical uniform spring:
       x = F_payload/k + (m_s g)/(2k)
    The self-weight term is one-half because the axial force from the spring's
    own weight varies approximately linearly from bottom to top.
    """
    return (payload_force_N + 0.5 * spring_mass_kg * G0) / rate_N_per_m


def local_primary_frequency_hz(k_each, spring_mass_each, cfg: SystemConfig, secondary_mass=0.0):
    """
    Approximate primary local frequency including m_s/3 effective mass.
    For three identical springs, total spring effective mass is
       3*m_s/3 = m_s
    """
    moving = cfg.m1_kg + cfg.m2_kg + secondary_mass
    effective_mass = moving + cfg.n_primary * spring_mass_each / 3.0
    return math.sqrt(cfg.n_primary * k_each / effective_mass)/(2.0*math.pi)


def local_secondary_frequency_hz(k, spring_mass, cfg: SystemConfig):
    effective_mass = cfg.m2_kg + spring_mass/3.0
    return math.sqrt(k/effective_mass)/(2.0*math.pi)


# ---------------------------------------------------------------------------
# Two-DOF model with consistent spring-mass approximation
# ---------------------------------------------------------------------------

def system_matrices(
    primary_geom: SpringGeometry,
    secondary_geom: SpringGeometry,
    cfg: SystemConfig,
    G_pa: float,
):
    k1_each = spring_rate_N_per_m(G_pa, primary_geom)
    K1 = cfg.n_primary * k1_each
    K2 = spring_rate_N_per_m(G_pa, secondary_geom)

    ms1_each = spring_body_mass_kg(primary_geom)
    Ms1 = cfg.n_primary * ms1_each
    ms2 = spring_body_mass_kg(secondary_geom)

    # Consistent mass approximation for a uniform spring with linearly
    # varying axial velocity.  Secondary spring contributes an off-diagonal
    # m_s/6 term between x1 and x2.
    M = np.array([
        [cfg.m1_kg + Ms1/3.0 + ms2/3.0, ms2/6.0],
        [ms2/6.0, cfg.m2_kg + ms2/3.0],
    ], dtype=float)

    K = np.array([
        [K1 + K2, -K2],
        [-K2, K2],
    ], dtype=float)

    return M, K, K1, K2, Ms1, ms2


def coupled_modes_hz(primary_geom, secondary_geom, cfg, G_pa):
    M, K, *_ = system_matrices(primary_geom, secondary_geom, cfg, G_pa)
    eigvals = np.linalg.eigvals(np.linalg.solve(M, K))
    eigvals = np.sort(np.real(eigvals))
    return np.sqrt(eigvals)/(2.0*math.pi)


def damping_coefficients(primary_geom, secondary_geom, cfg, G_pa):
    M, K, K1, K2, Ms1, ms2 = system_matrices(
        primary_geom, secondary_geom, cfg, G_pa
    )
    # Approximate link damping coefficients.  Actual damping must be fitted.
    m1eff = cfg.m1_kg + Ms1/3.0
    m2eff = cfg.m2_kg + ms2/3.0
    C1 = 2.0 * cfg.zeta1 * math.sqrt(K1 * m1eff)
    C2 = 2.0 * cfg.zeta2 * math.sqrt(K2 * m2eff)
    return C1, C2


def transfer_detector_over_base(
    f_hz: np.ndarray,
    primary_geom: SpringGeometry,
    secondary_geom: SpringGeometry,
    cfg: SystemConfig,
    G_pa: float,
):
    """
    X2/Y transfer function with:
      * point masses m1, m2,
      * consistent-mass approximation for distributed spring mass,
      * viscous link damping.

    The primary-spring consistent mass contributes an inertial base-excitation
    forcing term Ms1/6 * omega^2 Y.
    """
    M, K, K1, K2, Ms1, ms2 = system_matrices(
        primary_geom, secondary_geom, cfg, G_pa
    )
    C1, C2 = damping_coefficients(
        primary_geom, secondary_geom, cfg, G_pa
    )
    C = np.array([
        [C1 + C2, -C2],
        [-C2, C2],
    ], dtype=float)

    f_hz = np.asarray(f_hz, dtype=float)
    H2 = np.zeros_like(f_hz, dtype=complex)

    # Coupling from prescribed base y into x1.
    Mxy = np.array([Ms1/6.0, 0.0], dtype=float)
    Cxy = np.array([-C1, 0.0], dtype=float)
    Kxy = np.array([-K1, 0.0], dtype=float)

    for i, f in enumerate(f_hz):
        w = 2.0*math.pi*f
        Z = -w*w*M + 1j*w*C + K
        rhs = (w*w*Mxy - 1j*w*Cxy - Kxy)  # unit base displacement Y=1
        x = np.linalg.solve(Z, rhs)
        H2[i] = x[1]
    return H2


# ---------------------------------------------------------------------------
# Candidate evaluation and scanning
# ---------------------------------------------------------------------------

def evaluate_pair(primary_geom, secondary_geom, cfg, G_pa):
    k2 = spring_rate_N_per_m(G_pa, secondary_geom)
    ms2 = spring_body_mass_kg(secondary_geom)

    # Secondary statics
    F2_payload = cfg.m2_kg * G0
    F2_top_static = F2_payload + ms2*G0
    x2 = extension_due_payload_and_self_weight_m(F2_payload, ms2, k2)
    tau2_static = coil_body_shear_stress_pa(F2_top_static, secondary_geom)
    tau2_proof = coil_body_shear_stress_pa(
        cfg.proof_factor * F2_top_static, secondary_geom
    )

    # Primary statics: the primary supports m1 + m2 + entire secondary spring.
    k1_each = spring_rate_N_per_m(G_pa, primary_geom)
    ms1_each = spring_body_mass_kg(primary_geom)
    primary_payload_mass = cfg.m1_kg + cfg.m2_kg + ms2
    F1_payload_each = primary_payload_mass * G0 / cfg.n_primary

    # Top of each primary spring additionally carries its own spring body weight.
    F1_top_static = F1_payload_each + ms1_each*G0
    F1_top_design = (
        cfg.primary_load_imbalance_factor * F1_payload_each
        + ms1_each*G0
    )
    F1_top_proof = cfg.proof_factor * F1_top_design

    x1 = extension_due_payload_and_self_weight_m(
        F1_payload_each, ms1_each, k1_each
    )
    tau1_static = coil_body_shear_stress_pa(F1_top_static, primary_geom)
    tau1_design = coil_body_shear_stress_pa(F1_top_design, primary_geom)
    tau1_proof = coil_body_shear_stress_pa(F1_top_proof, primary_geom)

    modes = coupled_modes_hz(primary_geom, secondary_geom, cfg, G_pa)

    # Von Mises conversion: for pure shear, sigma_eq = sqrt(3)*tau.
    # This is a minimum material-yield requirement for the COIL BODY only.
    sigma_y_req_primary = math.sqrt(3.0)*tau1_proof
    sigma_y_req_secondary = math.sqrt(3.0)*tau2_proof

    return {
        "mode1_Hz": modes[0],
        "mode2_Hz": modes[1],
        "primary_k_each_N_m": k1_each,
        "primary_K_total_N_m": cfg.n_primary*k1_each,
        "secondary_K_N_m": k2,
        "primary_payload_force_each_N": F1_payload_each,
        "primary_top_static_force_N": F1_top_static,
        "primary_top_design_force_N": F1_top_design,
        "primary_top_proof_force_N": F1_top_proof,
        "primary_static_extension_mm": x1*1e3,
        "secondary_static_extension_mm": x2*1e3,
        "primary_spring_body_mass_each_kg": ms1_each,
        "primary_spring_body_mass_total_kg": cfg.n_primary*ms1_each,
        "secondary_spring_body_mass_kg": ms2,
        "primary_tau_static_MPa": tau1_static/1e6,
        "primary_tau_design_MPa": tau1_design/1e6,
        "primary_tau_proof_MPa": tau1_proof/1e6,
        "secondary_tau_static_MPa": tau2_static/1e6,
        "secondary_tau_proof_MPa": tau2_proof/1e6,
        "primary_min_tensile_yield_for_body_proof_MPa": sigma_y_req_primary/1e6,
        "secondary_min_tensile_yield_for_body_proof_MPa": sigma_y_req_secondary/1e6,
        "primary_working_coil_body_mm": primary_geom.active_turns*primary_geom.d_mm + x1*1e3,
        "secondary_working_coil_body_mm": secondary_geom.active_turns*secondary_geom.d_mm + x2*1e3,
    }


def scan_primary(cfg, secondary_geom, G_pa):
    sec_mass = spring_body_mass_kg(secondary_geom)
    rows = []
    for d_mm in np.arange(9.0, 13.51, 0.25):
        for C in np.arange(7.0, 11.51, 0.25):
            D_mm = d_mm*C
            for N in range(8, 27):
                geom = SpringGeometry(float(d_mm), float(D_mm), int(N))
                if geom.od_mm > cfg.primary_max_od_mm:
                    continue

                k = spring_rate_N_per_m(G_pa, geom)
                ms = spring_body_mass_kg(geom)
                f_local = local_primary_frequency_hz(k, ms, cfg, sec_mass)
                if not (cfg.primary_local_f_window_hz[0] <= f_local <= cfg.primary_local_f_window_hz[1]):
                    continue

                payload_mass = cfg.m1_kg + cfg.m2_kg + sec_mass
                Fpayload = payload_mass*G0/cfg.n_primary
                Ftop = Fpayload + ms*G0
                Fdesign = cfg.primary_load_imbalance_factor*Fpayload + ms*G0
                Fproof = cfg.proof_factor*Fdesign
                x = extension_due_payload_and_self_weight_m(Fpayload, ms, k)
                body = N*d_mm + x*1e3
                if body > cfg.primary_max_working_body_mm:
                    continue

                rows.append({
                    "d_mm": d_mm,
                    "D_mean_mm": D_mm,
                    "OD_mm": geom.od_mm,
                    "active_turns": N,
                    "spring_index": C,
                    "k_each_N_m": k,
                    "spring_mass_each_kg": ms,
                    "local_f_Hz_with_spring_mass": f_local,
                    "static_extension_mm": x*1e3,
                    "working_coil_body_mm": body,
                    "tau_static_top_MPa": coil_body_shear_stress_pa(Ftop, geom)/1e6,
                    "tau_design_top_MPa": coil_body_shear_stress_pa(Fdesign, geom)/1e6,
                    "tau_proof_top_MPa": coil_body_shear_stress_pa(Fproof, geom)/1e6,
                    "min_tensile_yield_for_body_proof_MPa":
                        math.sqrt(3)*coil_body_shear_stress_pa(Fproof, geom)/1e6,
                })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["target_error_pct"] = 100.0*abs(
            df["local_f_Hz_with_spring_mass"]/cfg.target_mode1_hz - 1.0
        )
        # A transparent heuristic ranking; it is NOT a safety certification.
        df["ranking_score"] = (
            12.0*df["target_error_pct"]
            + 0.015*df["tau_design_top_MPa"]
            + 0.06*df["spring_mass_each_kg"]
            + 0.002*df["OD_mm"]
            + 0.0008*df["working_coil_body_mm"]
        )
        df = df.sort_values("ranking_score").reset_index(drop=True)
    return df


def scan_secondary(cfg, G_pa):
    rows = []
    for d_mm in np.arange(1.5, 2.51, 0.05):
        for C in np.arange(8.0, 12.01, 0.25):
            D_mm = d_mm*C
            for N in range(12, 36):
                geom = SpringGeometry(float(d_mm), float(D_mm), int(N))
                if geom.od_mm > cfg.secondary_max_od_mm:
                    continue

                k = spring_rate_N_per_m(G_pa, geom)
                ms = spring_body_mass_kg(geom)
                f_local = local_secondary_frequency_hz(k, ms, cfg)
                if not (cfg.secondary_local_f_window_hz[0] <= f_local <= cfg.secondary_local_f_window_hz[1]):
                    continue

                Fpayload = cfg.m2_kg*G0
                Ftop = Fpayload + ms*G0
                Fproof = cfg.proof_factor*Ftop
                x = extension_due_payload_and_self_weight_m(Fpayload, ms, k)
                body = N*d_mm + x*1e3
                if body > cfg.secondary_max_working_body_mm:
                    continue

                rows.append({
                    "d_mm": d_mm,
                    "D_mean_mm": D_mm,
                    "OD_mm": geom.od_mm,
                    "active_turns": N,
                    "spring_index": C,
                    "k_N_m": k,
                    "spring_mass_kg": ms,
                    "local_f_Hz_with_spring_mass": f_local,
                    "static_extension_mm": x*1e3,
                    "working_coil_body_mm": body,
                    "tau_static_top_MPa": coil_body_shear_stress_pa(Ftop, geom)/1e6,
                    "tau_proof_top_MPa": coil_body_shear_stress_pa(Fproof, geom)/1e6,
                    "min_tensile_yield_for_body_proof_MPa":
                        math.sqrt(3)*coil_body_shear_stress_pa(Fproof, geom)/1e6,
                })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["target_error_pct"] = 100.0*abs(
            df["local_f_Hz_with_spring_mass"]/cfg.target_mode2_hz - 1.0
        )
        df["ranking_score"] = (
            12.0*df["target_error_pct"]
            + 0.015*df["tau_static_top_MPa"]
            + 0.3*df["spring_mass_kg"]
            + 0.002*df["OD_mm"]
            + 0.0008*df["working_coil_body_mm"]
        )
        df = df.sort_values("ranking_score").reset_index(drop=True)
    return df


def three_point_loads_N(total_supported_mass_kg, support_radius_m, com_x_m, com_y_m):
    """
    Exact static vertical load distribution for three supports located at
    azimuths 0, 120, 240 deg on a circle of radius R.

    Positive forces mean tensile load carried by each vertical spring.

    Use this instead of the blanket 15% imbalance factor once you know the
    actual COM offset and support radius.
    """
    th = np.deg2rad([0.0, 120.0, 240.0])
    x = support_radius_m*np.cos(th)
    y = support_radius_m*np.sin(th)
    W = total_supported_mass_kg*G0

    A = np.array([
        [1.0, 1.0, 1.0],
        x,
        y,
    ], dtype=float)
    b = np.array([W, W*com_x_m, W*com_y_m], dtype=float)
    return np.linalg.solve(A, b)


def main():
    cfg = SystemConfig()

    # Rounded, manufacturable baseline geometries.
    # These are preliminary candidates, not fabrication approval.
    primary = SpringGeometry(d_mm=12.0, D_mm=118.0, active_turns=16)
    secondary = SpringGeometry(d_mm=2.0, D_mm=22.0, active_turns=25)

    out = Path(__file__).resolve().parent
    Gcold = cfg.G_cold_proxy_pa

    summary = evaluate_pair(primary, secondary, cfg, Gcold)

    # Add geometry and material sensitivity fields.
    summary.update({
        "primary_wire_d_mm": primary.d_mm,
        "primary_mean_D_mm": primary.D_mm,
        "primary_OD_mm": primary.od_mm,
        "primary_active_turns": primary.active_turns,
        "primary_spring_index": primary.spring_index,
        "secondary_wire_d_mm": secondary.d_mm,
        "secondary_mean_D_mm": secondary.D_mm,
        "secondary_OD_mm": secondary.od_mm,
        "secondary_active_turns": secondary.active_turns,
        "secondary_spring_index": secondary.spring_index,
        "G_cold_proxy_GPa": Gcold/1e9,
        "G_room_reference_GPa": cfg.G_room_pa/1e9,
        "note_1": "NIST G(T) regression valid 4-300 K only; 51.2 GPa is a 4 K proxy, not a 70 mK certification.",
        "note_2": "Coil-body stress only. End hooks/eyes/terminations require separate design and proof testing.",
    })

    pd.DataFrame([summary]).to_csv(out/"baseline_summary.csv", index=False)

    # Candidate scans
    sec_df = scan_secondary(cfg, Gcold)
    prim_df = scan_primary(cfg, secondary, Gcold)
    prim_df.head(100).to_csv(out/"primary_candidates_top100.csv", index=False)
    sec_df.head(100).to_csv(out/"secondary_candidates_top100.csv", index=False)

    # Static sag trade-off based on massless ideal relationship.
    f = np.linspace(0.7, 6.0, 400)
    sag_mm = G0/(2*math.pi*f)**2 * 1e3
    pd.DataFrame({"frequency_Hz": f, "ideal_static_sag_mm": sag_mm}).to_csv(
        out/"frequency_sag_tradeoff.csv", index=False
    )

    plt.figure(figsize=(7.0, 4.6))
    plt.plot(f, sag_mm)
    plt.xlabel("Uncoupled vertical natural frequency (Hz)")
    plt.ylabel("Ideal static sag (mm)")
    plt.title("Vertical spring frequency–sag trade-off")
    plt.yscale("log")
    plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out/"frequency_sag_tradeoff.png", dpi=180)
    plt.close()

    # Transfer function
    freq = np.logspace(-1, 2.5, 3500)
    H2 = transfer_detector_over_base(freq, primary, secondary, cfg, Gcold)

    plt.figure(figsize=(7.0, 4.6))
    plt.loglog(freq, np.abs(H2))
    plt.axhline(1.0, linewidth=0.8)
    for fm in coupled_modes_hz(primary, secondary, cfg, Gcold):
        plt.axvline(fm, linewidth=0.8, linestyle="--")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("|X_detector / Y_base|")
    plt.title("Two-stage base-to-detector transmissibility")
    plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out/"transmissibility.png", dpi=180)
    plt.close()

    # Cold-vs-room sensitivity (same geometry).
    rows = []
    for Gpa in np.linspace(cfg.G_room_pa, cfg.G_cold_proxy_pa, 80):
        modes = coupled_modes_hz(primary, secondary, cfg, Gpa)
        rows.append((Gpa/1e9, modes[0], modes[1]))
    sens = pd.DataFrame(rows, columns=["G_GPa", "mode1_Hz", "mode2_Hz"])
    sens.to_csv(out/"modulus_sensitivity.csv", index=False)

    plt.figure(figsize=(7.0, 4.6))
    plt.plot(sens["G_GPa"], sens["mode1_Hz"], label="Mode 1")
    plt.plot(sens["G_GPa"], sens["mode2_Hz"], label="Mode 2")
    plt.xlabel("Shear modulus G (GPa)")
    plt.ylabel("Coupled mode frequency (Hz)")
    plt.title("Sensitivity to copper shear modulus")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out/"modulus_sensitivity.png", dpi=180)
    plt.close()

    # Compact console report
    print("=== Baseline two-stage spring design ===")
    print(f"m1 = {cfg.m1_kg:.3f} kg, m2 = {cfg.m2_kg:.3f} kg")
    print()
    print("Primary spring, each of 3:")
    print(f"  d = {primary.d_mm:.2f} mm")
    print(f"  D_mean = {primary.D_mm:.2f} mm")
    print(f"  OD = {primary.od_mm:.2f} mm")
    print(f"  active turns = {primary.active_turns}")
    print(f"  k_each(cold proxy) = {summary['primary_k_each_N_m']:.1f} N/m")
    print(f"  static extension incl. self-weight = {summary['primary_static_extension_mm']:.1f} mm")
    print(f"  coil-body mass each = {summary['primary_spring_body_mass_each_kg']:.2f} kg")
    print(f"  static top-coil stress = {summary['primary_tau_static_MPa']:.1f} MPa")
    print(f"  design top-coil stress = {summary['primary_tau_design_MPa']:.1f} MPa")
    print(f"  proof top-coil stress = {summary['primary_tau_proof_MPa']:.1f} MPa")
    print()
    print("Secondary spring:")
    print(f"  d = {secondary.d_mm:.2f} mm")
    print(f"  D_mean = {secondary.D_mm:.2f} mm")
    print(f"  OD = {secondary.od_mm:.2f} mm")
    print(f"  active turns = {secondary.active_turns}")
    print(f"  k(cold proxy) = {summary['secondary_K_N_m']:.1f} N/m")
    print(f"  static extension incl. self-weight = {summary['secondary_static_extension_mm']:.1f} mm")
    print(f"  coil-body mass = {summary['secondary_spring_body_mass_kg']:.3f} kg")
    print()
    print(f"Coupled modes at G={Gcold/1e9:.1f} GPa proxy: "
          f"{summary['mode1_Hz']:.3f}, {summary['mode2_Hz']:.3f} Hz")
    print()
    print("WARNING: extension-spring end hooks/eyes are NOT qualified by this calculation.")


if __name__ == "__main__":
    main()
