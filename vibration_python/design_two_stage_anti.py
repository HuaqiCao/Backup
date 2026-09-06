"""
Preliminary design tool for the two-stage cryogenic vibration isolator.

Second stage:
    three identical rectangular fixed-guided leaf flexures at 120 degrees.

The default geometry is a baseline design point, not an as-built claim.
Replace material and geometric inputs with measured/certified values.

Outputs:
  data/design_summary.txt
  data/leaf_thickness_sweep.csv
  figures/leaf_frequency_vs_thickness.png
  figures/two_stage_transfer_function.png
"""

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
DATA.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

G = 9.80665


@dataclass
class Design:
    # Moving masses
    shield_mass_kg: float = 90.0
    detector_mass_kg: float = 0.8

    # Stage 1: three helical springs in parallel
    stage1_spring_count: int = 3
    stage1_target_frequency_hz: float = 1.20

    # Stage 2: three rectangular fixed-guided leaves in parallel
    leaf_count: int = 3
    leaf_length_mm: float = 80.0
    leaf_width_mm: float = 15.0
    leaf_thickness_mm: float = 0.50

    # Reference elastic modulus only. Replace by the selected screened material value.
    youngs_modulus_GPa: float = 110.0

    # Damping ratios used only to plot an illustrative transfer function.
    zeta1: float = 0.05
    zeta2: float = 0.03

    # Additional vertical travel above the static equilibrium used for a stress check.
    design_dynamic_travel_mm: float = 1.0

    # Required material yield = design_factor * calculated peak bending stress.
    design_factor: float = 2.0

    # Optional parasitic vertical stiffnesses from wires/thermal links.
    parasitic_K1_N_per_m: float = 0.0
    parasitic_K2_N_per_m: float = 0.0


def leaf_stiffness(E, b, t, L):
    """One fixed-guided rectangular leaf: k = E b t^3 / L^3."""
    return E * b * t**3 / L**3


def leaf_max_stress(force, L, b, t):
    """Fixed-guided end stress from transverse force: sigma = 3 F L / (b t^2)."""
    return 3.0 * force * L / (b * t**2)


def thickness_for_target_f2(f2_hz, m2, n_leaf, E, b, L):
    """Required thickness for a target uncoupled second-stage frequency."""
    K2_target = m2 * (2.0 * math.pi * f2_hz)**2
    k_leaf_target = K2_target / n_leaf
    return (k_leaf_target * L**3 / (E * b))**(1.0 / 3.0)


def coupled_modes(M1, m2, K1, K2):
    """Undamped coupled vertical eigenfrequencies."""
    A = m2 * (K1 + K2) + M1 * K2
    disc = A*A - 4.0*M1*m2*K1*K2
    w2_minus = (A - math.sqrt(disc)) / (2.0*M1*m2)
    w2_plus = (A + math.sqrt(disc)) / (2.0*M1*m2)
    return math.sqrt(w2_minus)/(2.0*math.pi), math.sqrt(w2_plus)/(2.0*math.pi)


def transfer_function(f, M1, m2, K1, K2, zeta1, zeta2):
    """Base-to-shield and base-to-detector transfer functions."""
    C1 = 2.0*zeta1*math.sqrt(K1*(M1 + m2))
    C2 = 2.0*zeta2*math.sqrt(K2*m2)

    w = 2.0*np.pi*f
    s = 1j*w
    Z1 = K1 + C1*s
    Z2 = K2 + C2*s
    D = (M1*s**2 + Z1 + Z2)*(m2*s**2 + Z2) - Z2**2

    H1 = Z1*(m2*s**2 + Z2)/D
    H2 = Z1*Z2/D
    return H1, H2


def evaluate(d: Design):
    M1 = d.shield_mass_kg
    m2 = d.detector_mass_kg

    L = d.leaf_length_mm * 1e-3
    b = d.leaf_width_mm * 1e-3
    t = d.leaf_thickness_mm * 1e-3
    E = d.youngs_modulus_GPa * 1e9

    # Stage 1: use target frequency to obtain the required total stiffness.
    K1_susp = (2.0*math.pi*d.stage1_target_frequency_hz)**2 * (M1 + m2)
    K1 = K1_susp + d.parasitic_K1_N_per_m
    k1_each = K1_susp / d.stage1_spring_count
    stage1_sag = (M1 + m2)*G / K1

    # Stage 2 leaf flexures.
    k_leaf = leaf_stiffness(E, b, t, L)
    K2_susp = d.leaf_count * k_leaf
    K2 = K2_susp + d.parasitic_K2_N_per_m
    f2_uncoupled = math.sqrt(K2/m2)/(2.0*math.pi)
    stage2_sag = m2*G/K2

    static_force_each = m2*G/d.leaf_count
    sigma_static = leaf_max_stress(static_force_each, L, b, t)

    dynamic_force = k_leaf * (d.design_dynamic_travel_mm*1e-3)
    peak_force_each = static_force_each + dynamic_force
    sigma_peak = leaf_max_stress(peak_force_each, L, b, t)
    required_yield = d.design_factor * sigma_peak

    f_minus, f_plus = coupled_modes(M1, m2, K1, K2)

    return {
        "K1_susp": K1_susp,
        "K1_total": K1,
        "k1_each": k1_each,
        "stage1_sag": stage1_sag,
        "k_leaf": k_leaf,
        "K2_susp": K2_susp,
        "K2_total": K2,
        "f2_uncoupled": f2_uncoupled,
        "stage2_sag": stage2_sag,
        "static_force_each": static_force_each,
        "sigma_static": sigma_static,
        "dynamic_force": dynamic_force,
        "sigma_peak": sigma_peak,
        "required_yield": required_yield,
        "f_minus": f_minus,
        "f_plus": f_plus,
        "deflection_ratio": stage2_sag/L,
    }


def main():
    d = Design()
    r = evaluate(d)

    summary = f"""
TWO-STAGE VIBRATION ISOLATOR — PRELIMINARY DESIGN SUMMARY
=========================================================

Stage 1
-------
Shield mass                          {d.shield_mass_kg:8.3f} kg
Detector mass                        {d.detector_mass_kg:8.3f} kg
Number of helical springs            {d.stage1_spring_count:8d}
Target uncoupled frequency           {d.stage1_target_frequency_hz:8.3f} Hz
Required suspension K1               {r['K1_susp']:8.2f} N/m
Required stiffness per spring        {r['k1_each']:8.2f} N/m
Static vertical sag                  {1e3*r['stage1_sag']:8.2f} mm

Stage 2 — 3 fixed-guided rectangular leaf flexures
---------------------------------------------------
Leaf count                           {d.leaf_count:8d}
Leaf length                          {d.leaf_length_mm:8.3f} mm
Leaf width                           {d.leaf_width_mm:8.3f} mm
Leaf thickness                       {d.leaf_thickness_mm:8.3f} mm
Reference Young's modulus            {d.youngs_modulus_GPa:8.3f} GPa
Stiffness per leaf                   {r['k_leaf']:8.2f} N/m
Total suspension K2                  {r['K2_susp']:8.2f} N/m
Uncoupled second-stage frequency     {r['f2_uncoupled']:8.3f} Hz
Static detector sag                  {1e3*r['stage2_sag']:8.3f} mm
Static load per leaf                 {r['static_force_each']:8.3f} N
Static bending stress                {r['sigma_static']/1e6:8.2f} MPa
Extra design travel                  {d.design_dynamic_travel_mm:8.3f} mm
Peak bending stress                  {r['sigma_peak']/1e6:8.2f} MPa
Design factor                        {d.design_factor:8.3f}
Minimum required yield strength      {r['required_yield']/1e6:8.2f} MPa
Static deflection / leaf span        {r['deflection_ratio']:8.4f}

Coupled undamped modes
----------------------
Lower mode                           {r['f_minus']:8.3f} Hz
Upper mode                           {r['f_plus']:8.3f} Hz

IMPORTANT
---------
1. Replace E with the selected, screened material value at the relevant temperature.
2. Check clamp compliance and actual free span after assembly.
3. The beam model is linear; if deflection/span is not small, verify with FEA or a load test.
4. Add measured wire/thermal-link stiffness through parasitic_K1/K2.
5. The yield-strength requirement is a screening criterion, not a material certification.
""".strip() + "\n"

    (DATA / "design_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)

    # Thickness sweep for the three-leaf second stage.
    thicknesses_mm = np.arange(0.30, 0.805, 0.025)
    rows = []
    for tmm in thicknesses_mm:
        dd = Design(**{**d.__dict__, "leaf_thickness_mm": float(tmm)})
        rr = evaluate(dd)
        rows.append([
            tmm,
            rr["K2_susp"],
            rr["f2_uncoupled"],
            1e3*rr["stage2_sag"],
            rr["sigma_static"]/1e6,
            rr["sigma_peak"]/1e6,
            rr["required_yield"]/1e6,
        ])

    with (DATA / "leaf_thickness_sweep.csv").open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow([
            "thickness_mm",
            "K2_N_per_m",
            "f2_uncoupled_Hz",
            "static_sag_mm",
            "static_stress_MPa",
            "peak_stress_with_design_travel_MPa",
            "minimum_required_yield_MPa",
        ])
        w.writerows(rows)

    # Plot second-stage frequency versus leaf thickness.
    plt.figure(figsize=(7.0, 4.6))
    plt.plot(thicknesses_mm, [row[2] for row in rows], marker="o", markersize=3)
    plt.xlabel("Leaf thickness (mm)")
    plt.ylabel("Uncoupled second-stage frequency (Hz)")
    plt.title("Three fixed-guided leaf flexures")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(FIG / "leaf_frequency_vs_thickness.png", dpi=220)
    plt.close()

    # Coupled transfer function for the baseline design.
    f = np.logspace(-1, 2.5, 2200)
    H1, H2 = transfer_function(
        f,
        d.shield_mass_kg,
        d.detector_mass_kg,
        r["K1_total"],
        r["K2_total"],
        d.zeta1,
        d.zeta2,
    )

    plt.figure(figsize=(7.0, 4.8))
    plt.loglog(f, np.abs(H1), label="Base to shield")
    plt.loglog(f, np.abs(H2), label="Base to detector")
    plt.axhline(1.0, linewidth=0.8)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Transmissibility magnitude")
    plt.title("Illustrative coupled two-stage response")
    plt.grid(True, which="both")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "two_stage_transfer_function.png", dpi=220)
    plt.close()

    # Demonstrate thickness inversion for a target second-stage frequency.
    t6 = thickness_for_target_f2(
        6.0,
        d.detector_mass_kg,
        d.leaf_count,
        d.youngs_modulus_GPa*1e9,
        d.leaf_width_mm*1e-3,
        d.leaf_length_mm*1e-3,
    )
    print(f"Thickness required for f2 = 6.0 Hz with baseline L, b and E: {1e3*t6:.3f} mm")


if __name__ == "__main__":
    main()
