# -*- coding: utf-8 -*-
"""
GAS constant-width / variable-thickness optimization
=====================================================

Main purpose
------------
1. Reproduce a reference variable-width / constant-thickness GAS blade.
2. Construct an EXACT-EI + equal-volume constant-width variable-thickness blade.
3. Optimize h(s) for the constant-width blade.
4. Compare:
       force-displacement curve
       tangent stiffness
       resonant frequency
       payload
       stress
       low-frequency payload range
       volume
5. Use forward/backward continuation to detect possible branch problems.

Governing equations
-------------------
For one blade:

    dtheta/ds = M / D(s)

    dM/ds = Fx*sin(theta) - Fy*cos(theta)

    dx/ds = cos(theta)

    dy/ds = sin(theta)

where

    I(s) = b(s)*h(s)^3/12

and optionally

    D(s) = E*I(s)/(1-nu^2)

for a Poisson/plate correction.

IMPORTANT
---------
This is a 1-D large-deformation screening/optimization model.

Final candidates should still be checked using 3-D geometric-nonlinear FEA,
especially near clamps and for wide blades.

Author note
-----------
The published 2017 gamma definition deserves careful checking against the
actual blade CAD/profile.  Therefore this script exposes two interpretations:

    reference_mapping = "mechanical_taper"
        w = w0 * [c1+c2*cos(beta*xi)+c3*sin(beta*xi)]

    reference_mapping = "paper_literal"
        w = w0 / [c1+c2*cos(beta*xi)+c3*sin(beta*xi)]

The first gives the physically familiar wide-base / narrow-tip taper and is
used as the default here.

Replace reference_width() with your actual measured/CAD profile if available.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence, List, Dict, Tuple
import csv
import math
import os
import warnings

import numpy as np

from scipy.integrate import solve_bvp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import differential_evolution

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


# ======================================================================
# 0. CONSTANTS
# ======================================================================

G0 = 9.80665


# ======================================================================
# 1. USER SETTINGS
# ======================================================================

@dataclass(frozen=True)
class ModelConfig:

    # --------------------------------------------------------------
    # Material
    # --------------------------------------------------------------
    E: float = 196.0e9
    nu: float = 0.30
    yield_strength: float = 1665.0e6

    # --------------------------------------------------------------
    # Blade geometry
    # --------------------------------------------------------------
    L: float = 120.0e-3

    theta0_deg: float = 45.0
    thetaL_deg: float = -30.0

    # Horizontal compression / geometry parameter
    x_ratio: float = 0.92

    # Number of blades in complete GAS
    n_blades: int = 6

    # --------------------------------------------------------------
    # 2017 reference blade
    # --------------------------------------------------------------
    w0: float = 36.0e-3
    h0: float = 0.78e-3

    # "mechanical_taper" or "paper_literal"
    reference_mapping: str = "mechanical_taper"

    # --------------------------------------------------------------
    # Poisson correction
    # --------------------------------------------------------------
    # Classical wide-blade GAS formulations may use:
    #
    #     D = EI/(1-nu^2)
    #
    # Set False if you want pure Euler-Bernoulli EI.
    # --------------------------------------------------------------
    use_poisson_correction: bool = True

    # --------------------------------------------------------------
    # S-curve scan range
    # y_tip / L
    # --------------------------------------------------------------
    y_ratio_min: float = 0.020
    y_ratio_max: float = 0.170

    # --------------------------------------------------------------
    # Manufacturing limits for variable thickness
    # --------------------------------------------------------------
    h_min: float = 0.30e-3
    h_max: float = 1.60e-3

    # Maximum |dh/ds|.
    # Dimensionless because both h and s are lengths.
    max_dh_ds: float = 0.025

    # --------------------------------------------------------------
    # Structural safety
    # --------------------------------------------------------------
    safety_factor: float = 1.50

    # --------------------------------------------------------------
    # Optimization constraints relative to reference
    # --------------------------------------------------------------
    max_frequency_increase: float = 0.03
    max_payload_loss: float = 0.03
    max_window_loss: float = 0.20

    # Low-frequency working range:
    # points below factor * reference minimum/rated frequency
    low_frequency_factor: float = 1.25

    # --------------------------------------------------------------
    # BVP numerical settings
    # --------------------------------------------------------------
    bvp_tol: float = 2.0e-7
    bc_tol: float = 2.0e-8

    initial_mesh_points: int = 161
    max_nodes: int = 15000

    # Fast optimization curve
    fast_curve_points: int = 25

    # Final reported curve
    accurate_curve_points: int = 91

    # --------------------------------------------------------------
    # Differential Evolution
    # --------------------------------------------------------------
    random_seed: int = 7

    de_popsize: int = 10
    de_maxiter: int = 20

    # Four logarithmic Bernstein ratios
    min_control_ratio: float = 0.35
    max_control_ratio: float = 3.00

    penalty: float = 2.0e4

    # --------------------------------------------------------------
    # Output
    # --------------------------------------------------------------
    output_directory: str = "gas_variable_thickness_results"

    @property
    def theta0(self):
        return math.radians(self.theta0_deg)

    @property
    def thetaL(self):
        return math.radians(self.thetaL_deg)

    @property
    def Xtip(self):
        return self.x_ratio * self.L

    @property
    def allowable_stress(self):
        return self.yield_strength / self.safety_factor


# ======================================================================
# 2. SECTION PROFILES
# ======================================================================

class SectionProfile:
    """
    Generic blade cross-section profile.
    """

    name = "generic"

    def width(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        raise NotImplementedError

    def thickness(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        raise NotImplementedError

    def area(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        return (
            self.width(s, cfg)
            * self.thickness(s, cfg)
        )

    def inertia(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        b = self.width(s, cfg)
        h = self.thickness(s, cfg)

        return b * h**3 / 12.0

    def rigidity(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        EI = cfg.E * self.inertia(s, cfg)

        if cfg.use_poisson_correction:
            EI = EI / (1.0 - cfg.nu**2)

        return EI

    def volume(
        self,
        cfg: ModelConfig,
        n: int = 5001
    ) -> float:

        s = np.linspace(0.0, cfg.L, n)

        return float(
            np.trapz(
                self.area(s, cfg),
                s
            )
        )

    def extrema(
        self,
        cfg: ModelConfig,
        n: int = 3001
    ) -> Dict[str, float]:

        s = np.linspace(0.0, cfg.L, n)

        b = self.width(s, cfg)
        h = self.thickness(s, cfg)

        dh_ds = np.gradient(h, s)

        return {
            "b_min": float(np.min(b)),
            "b_max": float(np.max(b)),
            "h_min": float(np.min(h)),
            "h_max": float(np.max(h)),
            "max_abs_dh_ds": float(
                np.max(np.abs(dh_ds))
            ),
        }


# ======================================================================
# 3. REFERENCE VARIABLE-WIDTH BLADE
# ======================================================================

class ReferenceVariableWidth(SectionProfile):

    name = "reference-variable-width"

    def denominator(
        self,
        xi: np.ndarray
    ) -> np.ndarray:

        c1 = -0.377
        c2 = 1.377
        c3 = 0.195
        beta = 1.361

        return (
            c1
            + c2 * np.cos(beta * xi)
            + c3 * np.sin(beta * xi)
        )

    def width(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        xi = np.asarray(s, dtype=float) / cfg.L

        den = self.denominator(xi)

        if np.any(den <= 0.0):
            raise ValueError(
                "Reference width denominator became non-positive."
            )

        if cfg.reference_mapping == "mechanical_taper":

            # Wide base -> narrow tip.
            return cfg.w0 * den

        elif cfg.reference_mapping == "paper_literal":

            # Literal interpretation of printed gamma=w/w0.
            return cfg.w0 / den

        else:
            raise ValueError(
                "reference_mapping must be "
                "'mechanical_taper' or 'paper_literal'"
            )

    def thickness(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        return np.full_like(
            np.asarray(s, dtype=float),
            cfg.h0
        )


# ======================================================================
# 4. BERNSTEIN PARAMETERIZATION
# ======================================================================

def bernstein_degree4(
    xi: np.ndarray
) -> np.ndarray:
    """
    Returns shape (5, N).

    Degree-4 Bernstein basis.
    """

    xi = np.asarray(xi, dtype=float)

    return np.vstack([
        (1.0 - xi)**4,

        4.0
        * xi
        * (1.0 - xi)**3,

        6.0
        * xi**2
        * (1.0 - xi)**2,

        4.0
        * xi**3
        * (1.0 - xi),

        xi**4,
    ])


class ConstantWidthVariableThickness(
    SectionProfile
):
    """
    Constant-width / variable-thickness blade.

    h(s) = scale * sum(c_i B_i)

    Exact equal-volume constraint is enforced analytically.
    """

    name = "constant-width-variable-thickness"

    def __init__(
        self,
        constant_width: float,
        controls: Sequence[float],
        target_volume: float
    ):

        self.constant_width = float(
            constant_width
        )

        self.controls = np.asarray(
            controls,
            dtype=float
        )

        self.target_volume = float(
            target_volume
        )

        if self.controls.shape != (5,):
            raise ValueError(
                "Exactly five Bernstein controls required."
            )

        if np.any(self.controls <= 0.0):
            raise ValueError(
                "All Bernstein controls must be positive."
            )

    def raw_thickness_shape(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        xi = np.asarray(s, dtype=float) / cfg.L

        B = bernstein_degree4(xi)

        return self.controls @ B

    def thickness_scale(
        self,
        cfg: ModelConfig
    ) -> float:
        """
        Integral of every degree-4 Bernstein basis over [0,1]
        is exactly 1/5.

        Therefore mean(raw shape) = sum(controls)/5.
        """

        raw_mean = (
            np.sum(self.controls) / 5.0
        )

        return (
            self.target_volume
            /
            (
                self.constant_width
                * cfg.L
                * raw_mean
            )
        )

    def width(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        return np.full_like(
            np.asarray(s, dtype=float),
            self.constant_width
        )

    def thickness(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        return (
            self.thickness_scale(cfg)
            * self.raw_thickness_shape(s, cfg)
        )


# ======================================================================
# 5. EXACT-EI + EQUAL-VOLUME VARIABLE-THICKNESS BLADE
# ======================================================================

class ExactEquivalentThickness(
    SectionProfile
):

    name = "exact-EI-equal-volume-thickness"

    def __init__(
        self,
        reference: SectionProfile,
        constant_width: float
    ):

        self.reference = reference
        self.constant_width = float(
            constant_width
        )

    def width(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        return np.full_like(
            np.asarray(s, dtype=float),
            self.constant_width
        )

    def thickness(
        self,
        s: np.ndarray,
        cfg: ModelConfig
    ) -> np.ndarray:

        w_ref = self.reference.width(
            s,
            cfg
        )

        return (
            cfg.h0
            * (
                w_ref
                / self.constant_width
            )**(1.0 / 3.0)
        )


def build_exact_equivalent(
    reference: SectionProfile,
    cfg: ModelConfig
) -> ExactEquivalentThickness:
    """
    Solve for constant width b0 such that:

        b0*h(s)^3 = w(s)*h0^3

    AND

        b0*Integral[h(s) ds]
        =
        h0*Integral[w(s) ds]

    Result:

        b0 =
        [ Integral(w ds)
          /
          Integral(w^(1/3) ds)
        ]^(3/2)
    """

    s = np.linspace(
        0.0,
        cfg.L,
        10001
    )

    w = reference.width(s, cfg)

    int_w = np.trapz(
        w,
        s
    )

    int_w13 = np.trapz(
        w**(1.0 / 3.0),
        s
    )

    b0 = (
        int_w / int_w13
    )**1.5

    return ExactEquivalentThickness(
        reference,
        b0
    )


# ======================================================================
# 6. BVP DATA
# ======================================================================

@dataclass
class PointSolution:

    success: bool

    y_tip: float

    Fx: float = np.nan
    Fy: float = np.nan

    max_stress: float = np.nan

    bc_error: float = np.inf

    s: Optional[np.ndarray] = None
    theta: Optional[np.ndarray] = None
    moment: Optional[np.ndarray] = None
    x: Optional[np.ndarray] = None
    y: Optional[np.ndarray] = None

    raw: object = None

    message: str = ""


@dataclass
class CurveResult:

    y: np.ndarray
    Fx: np.ndarray
    Fy: np.ndarray
    stress: np.ndarray

    solutions: List[PointSolution]

    branch_discrepancy: float

    failed_points: int


# ======================================================================
# 7. INITIAL BVP GUESS
# ======================================================================

def initial_state(
    profile: SectionProfile,
    y_tip: float,
    cfg: ModelConfig
):

    s = np.linspace(
        0.0,
        cfg.L,
        cfg.initial_mesh_points
    )

    t = s / cfg.L

    theta = (
        cfg.theta0
        + (
            cfg.thetaL
            - cfg.theta0
        ) * t
    )

    curvature = (
        cfg.thetaL
        - cfg.theta0
    ) / cfg.L

    M = (
        profile.rigidity(s, cfg)
        * curvature
    )

    # Initial x/y guesses do not need to satisfy ODE exactly.
    x = cfg.Xtip * t
    y = y_tip * t

    state = np.vstack([
        theta,
        M,
        x,
        y
    ])

    return s, state


# ======================================================================
# 8. SOLVE ONE PRESCRIBED Y-TIP POSITION
# ======================================================================

def solve_point(
    profile: SectionProfile,
    y_tip: float,
    cfg: ModelConfig,
    previous: Optional[PointSolution] = None,
    use_multistart: bool = True
) -> PointSolution:

    s = np.linspace(
        0.0,
        cfg.L,
        cfg.initial_mesh_points
    )

    starts = []

    # --------------------------------------------------------------
    # Continuation solution first
    # --------------------------------------------------------------
    if (
        previous is not None
        and previous.success
        and previous.raw is not None
    ):

        state = previous.raw.sol(s)

        p0 = np.asarray(
            previous.raw.p,
            dtype=float
        )

        starts.append(
            (state, p0)
        )

    # --------------------------------------------------------------
    # Generic initial state
    # --------------------------------------------------------------
    base_s, base_state = initial_state(
        profile,
        y_tip,
        cfg
    )

    # Characteristic blade force
    Dmid = float(
        profile.rigidity(
            np.array([0.5 * cfg.L]),
            cfg
        )[0]
    )

    Fchar = max(
        Dmid / cfg.L**2,
        1.0
    )

    if (
        previous is None
        or use_multistart
    ):

        force_factors = [
            (-2.0, -2.0),
            (-5.0, -2.0),
            (-10.0, -3.0),
            (-15.0, -5.0),

            (-5.0, 2.0),
            (-10.0, 3.0),

            (2.0, -2.0),
            (5.0, -3.0),

            (2.0, 2.0),
        ]

        for ax, ay in force_factors:

            p0 = np.array([
                ax * Fchar,
                ay * Fchar
            ])

            starts.append(
                (
                    base_state.copy(),
                    p0
                )
            )

    # --------------------------------------------------------------
    # ODE
    # --------------------------------------------------------------
    def ode(ss, z, p):

        theta = z[0]
        M = z[1]

        Fx = p[0]
        Fy = p[1]

        D = profile.rigidity(
            ss,
            cfg
        )

        if np.any(D <= 0.0):
            raise FloatingPointError(
                "Non-positive bending rigidity."
            )

        return np.vstack([
            M / D,

            (
                Fx * np.sin(theta)
                - Fy * np.cos(theta)
            ),

            np.cos(theta),

            np.sin(theta),
        ])

    # --------------------------------------------------------------
    # Boundary conditions
    #
    # theta(0) = theta0
    # x(0)     = 0
    # y(0)     = 0
    #
    # theta(L) = thetaL
    # x(L)     = Xtip
    # y(L)     = prescribed y_tip
    #
    # Fx/Fy are two unknown BVP parameters.
    # --------------------------------------------------------------
    def bc(za, zb, p):

        return np.array([
            za[0] - cfg.theta0,
            za[2],
            za[3],

            zb[0] - cfg.thetaL,
            zb[2] - cfg.Xtip,
            zb[3] - y_tip,
        ])

    best = None
    best_error = np.inf

    for state0, p0 in starts:

        try:

            sol = solve_bvp(
                ode,
                bc,
                s,
                state0,
                p=p0,

                tol=cfg.bvp_tol,
                bc_tol=cfg.bc_tol,

                max_nodes=cfg.max_nodes,

                verbose=0
            )

            bc_residual = bc(
                sol.y[:, 0],
                sol.y[:, -1],
                sol.p
            )

            bc_error = float(
                np.max(
                    np.abs(
                        bc_residual
                    )
                )
            )

            score = (
                bc_error
                + (
                    0.0
                    if sol.success
                    else 1.0
                )
            )

            if score < best_error:

                best_error = score
                best = sol

            if (
                sol.success
                and bc_error
                < 5.0 * cfg.bc_tol
            ):
                break

        except Exception:
            continue

    if best is None:

        return PointSolution(
            success=False,
            y_tip=y_tip,
            message="All BVP initial guesses failed."
        )

    # --------------------------------------------------------------
    # Dense stress calculation
    # --------------------------------------------------------------
    sd = np.linspace(
        0.0,
        cfg.L,
        1401
    )

    zd = best.sol(sd)

    M = zd[1]

    b = profile.width(
        sd,
        cfg
    )

    h = profile.thickness(
        sd,
        cfg
    )

    # Rectangular-section longitudinal bending stress.
    sigma = (
        6.0
        * np.abs(M)
        /
        (
            b
            * h**2
        )
    )

    bc_error = float(
        np.max(
            np.abs(
                bc(
                    best.y[:, 0],
                    best.y[:, -1],
                    best.p
                )
            )
        )
    )

    return PointSolution(
        success=bool(best.success),

        y_tip=float(y_tip),

        Fx=float(best.p[0]),
        Fy=float(best.p[1]),

        max_stress=float(
            np.max(sigma)
        ),

        bc_error=bc_error,

        s=sd,
        theta=zd[0],
        moment=zd[1],
        x=zd[2],
        y=zd[3],

        raw=best,

        message=str(best.message)
    )


# ======================================================================
# 9. TRACE ONE CONTINUATION DIRECTION
# ======================================================================

def trace_direction(
    profile: SectionProfile,
    y_values: np.ndarray,
    cfg: ModelConfig
) -> List[PointSolution]:

    results = []

    previous = None

    for i, yy in enumerate(y_values):

        sol = solve_point(
            profile,
            float(yy),
            cfg,
            previous=previous,
            use_multistart=(
                previous is None
            )
        )

        # If continuation fails, retry globally.
        if not sol.success:

            sol = solve_point(
                profile,
                float(yy),
                cfg,
                previous=None,
                use_multistart=True
            )

        results.append(sol)

        if sol.success:
            previous = sol
        else:
            previous = None

    return results


# ======================================================================
# 10. COMPLETE S-CURVE
# ======================================================================

def trace_curve(
    profile: SectionProfile,
    cfg: ModelConfig,
    accurate: bool = True,
    bidirectional: bool = True
) -> CurveResult:

    n = (
        cfg.accurate_curve_points
        if accurate
        else cfg.fast_curve_points
    )

    y_values = (
        cfg.L
        * np.linspace(
            cfg.y_ratio_min,
            cfg.y_ratio_max,
            n
        )
    )

    forward = trace_direction(
        profile,
        y_values,
        cfg
    )

    selected = forward
    discrepancy = 0.0

    # --------------------------------------------------------------
    # Reverse continuation check
    # --------------------------------------------------------------
    if bidirectional:

        reverse_raw = trace_direction(
            profile,
            y_values[::-1],
            cfg
        )

        reverse = list(
            reversed(reverse_raw)
        )

        relative_errors = []

        selected = []

        for fwd, rev in zip(
            forward,
            reverse
        ):

            if (
                fwd.success
                and rev.success
            ):

                denominator = max(
                    abs(fwd.Fy),
                    abs(rev.Fy),
                    1.0
                )

                err = (
                    abs(
                        fwd.Fy
                        - rev.Fy
                    )
                    / denominator
                )

                relative_errors.append(
                    err
                )

                # Prefer lower BC residual.
                if (
                    fwd.bc_error
                    <= rev.bc_error
                ):
                    selected.append(fwd)
                else:
                    selected.append(rev)

            elif fwd.success:

                selected.append(fwd)

            else:

                selected.append(rev)

        if relative_errors:

            discrepancy = float(
                np.max(
                    relative_errors
                )
            )

        else:

            discrepancy = np.inf

    good = [
        q
        for q in selected
        if (
            q.success
            and np.isfinite(q.Fy)
            and np.isfinite(q.max_stress)
        )
    ]

    return CurveResult(

        y=np.array(
            [q.y_tip for q in good]
        ),

        Fx=np.array(
            [q.Fx for q in good]
        ),

        Fy=np.array(
            [q.Fy for q in good]
        ),

        stress=np.array(
            [q.max_stress for q in good]
        ),

        solutions=good,

        branch_discrepancy=discrepancy,

        failed_points=(
            n - len(good)
        )
    )


# ======================================================================
# 11. PERFORMANCE METRICS
# ======================================================================

@dataclass
class Metrics:

    valid: bool

    rated_y: float = np.nan

    rated_payload_kg: float = np.nan

    rated_stiffness: float = np.nan

    rated_frequency: float = np.nan

    minimum_frequency: float = np.nan

    rated_stress: float = np.nan

    working_window_stress: float = np.nan

    low_frequency_payload_window: float = np.nan

    stable_fraction: float = np.nan

    stability_sign: float = 1.0

    branch_discrepancy: float = np.nan

    note: str = ""


def calculate_metrics(
    curve: CurveResult,
    cfg: ModelConfig,
    stability_sign: Optional[float] = None,
    frequency_limit: Optional[float] = None
) -> Metrics:

    if len(curve.y) < 9:

        return Metrics(
            valid=False,
            branch_discrepancy=(
                curve.branch_discrepancy
            ),
            note="Too few converged BVP points."
        )

    order = np.argsort(
        curve.y
    )

    y = curve.y[order]

    # Positive physical load magnitude
    P = (
        cfg.n_blades
        * np.abs(
            curve.Fy[order]
        )
    )

    stress = curve.stress[order]

    # --------------------------------------------------------------
    # PCHIP avoids oscillatory derivatives from high-order fits.
    # --------------------------------------------------------------
    pP = PchipInterpolator(
        y,
        P
    )

    dP = pP.derivative()

    pStress = PchipInterpolator(
        y,
        stress
    )

    span = y[-1] - y[0]

    # Avoid endpoint differentiation.
    grid = np.linspace(
        y[0] + 0.025 * span,
        y[-1] - 0.025 * span,
        2501
    )

    derivative = dP(grid)

    # --------------------------------------------------------------
    # Coordinate sign convention
    #
    # The reference curve determines which slope sign corresponds
    # to the physically stable working branch.
    # --------------------------------------------------------------
    if stability_sign is None:

        med = float(
            np.median(derivative)
        )

        stability_sign = (
            1.0
            if med >= 0.0
            else -1.0
        )

    k = (
        stability_sign
        * derivative
    )

    k_scale = max(
        float(
            np.max(
                np.abs(k)
            )
        ),
        1.0
    )

    k_floor = (
        1.0e-9
        * k_scale
    )

    stable = (
        k > k_floor
    )

    if not np.any(stable):

        return Metrics(
            valid=False,
            stability_sign=stability_sign,
            branch_discrepancy=(
                curve.branch_discrepancy
            ),
            note="No stable positive-stiffness region."
        )

    # --------------------------------------------------------------
    # Rated GAS point:
    # minimum positive tangent stiffness
    # --------------------------------------------------------------
    k_search = np.where(
        stable,
        k,
        np.inf
    )

    j = int(
        np.argmin(
            k_search
        )
    )

    y0 = float(
        grid[j]
    )

    P0 = float(
        pP(y0)
    )

    k0 = float(
        k[j]
    )

    mass0 = (
        P0 / G0
    )

    if (
        mass0 <= 0.0
        or k0 <= 0.0
    ):

        return Metrics(
            valid=False,
            stability_sign=stability_sign,
            note="Nonphysical mass or stiffness."
        )

    f0 = (
        math.sqrt(
            k0 / mass0
        )
        /
        (
            2.0
            * math.pi
        )
    )

    # --------------------------------------------------------------
    # Frequency across branch
    # --------------------------------------------------------------
    P_grid = pP(grid)

    mass_grid = (
        P_grid / G0
    )

    frequency = np.full_like(
        grid,
        np.nan
    )

    usable = (
        stable
        & (mass_grid > 0.0)
    )

    frequency[usable] = (
        np.sqrt(
            k[usable]
            / mass_grid[usable]
        )
        /
        (
            2.0
            * np.pi
        )
    )

    min_frequency = float(
        np.nanmin(
            frequency
        )
    )

    # --------------------------------------------------------------
    # Low-frequency operating range
    # --------------------------------------------------------------
    if frequency_limit is None:

        frequency_limit = (
            cfg.low_frequency_factor
            * f0
        )

    low_frequency = (
        usable
        & (
            frequency
            <= frequency_limit
        )
    )

    stress_grid = pStress(grid)

    if np.any(low_frequency):

        masses = mass_grid[
            low_frequency
        ]

        payload_window = float(
            np.max(masses)
            - np.min(masses)
        )

        working_stress = float(
            np.max(
                stress_grid[
                    low_frequency
                ]
            )
        )

    else:

        payload_window = 0.0

        working_stress = float(
            pStress(y0)
        )

    stable_fraction = float(
        np.mean(stable)
    )

    return Metrics(

        valid=True,

        rated_y=y0,

        rated_payload_kg=mass0,

        rated_stiffness=k0,

        rated_frequency=f0,

        minimum_frequency=min_frequency,

        rated_stress=float(
            pStress(y0)
        ),

        working_window_stress=(
            working_stress
        ),

        low_frequency_payload_window=(
            payload_window
        ),

        stable_fraction=stable_fraction,

        stability_sign=stability_sign,

        branch_discrepancy=(
            curve.branch_discrepancy
        ),

        note="OK"
    )


# ======================================================================
# 12. CONVERT OPTIMIZATION VARIABLES -> THICKNESS PROFILE
# ======================================================================

def controls_from_z(
    z: Sequence[float]
) -> np.ndarray:
    """
    Four independent logarithmic ratios.

    First Bernstein control is fixed at 1.

    Positive controls are guaranteed by exp().
    """

    z = np.asarray(
        z,
        dtype=float
    )

    if z.shape != (4,):
        raise ValueError(
            "Optimization vector must have four variables."
        )

    return np.r_[
        1.0,
        np.exp(z)
    ]


# ======================================================================
# 13. FIT EXACT-EI PROFILE AS OPTIMIZER INITIAL SEED
# ======================================================================

def fit_initial_seed(
    exact_profile: SectionProfile,
    cfg: ModelConfig
) -> np.ndarray:

    xi = np.linspace(
        0.0,
        1.0,
        501
    )

    s = xi * cfg.L

    target = exact_profile.thickness(
        s,
        cfg
    )

    # Normalize because total scale is removed by equal-volume constraint.
    target = (
        target
        / np.mean(target)
    )

    B = bernstein_degree4(
        xi
    ).T

    controls, *_ = np.linalg.lstsq(
        B,
        target,
        rcond=None
    )

    controls = np.maximum(
        controls,
        1.0e-8
    )

    controls = (
        controls
        / controls[0]
    )

    return np.log(
        controls[1:]
    )


# ======================================================================
# 14. VARIABLE-THICKNESS OPTIMIZATION
# ======================================================================

def optimize_variable_thickness(
    reference: SectionProfile,
    exact_profile: ExactEquivalentThickness,
    reference_metrics: Metrics,
    cfg: ModelConfig
):

    target_volume = (
        reference.volume(cfg)
    )

    b0 = (
        exact_profile.constant_width
    )

    reference_stress = max(
        reference_metrics.working_window_stress,
        1.0
    )

    reference_window = max(
        reference_metrics.low_frequency_payload_window,
        1.0e-9
    )

    frequency_limit = (
        cfg.low_frequency_factor
        * reference_metrics.rated_frequency
    )

    zmin = math.log(
        cfg.min_control_ratio
    )

    zmax = math.log(
        cfg.max_control_ratio
    )

    bounds = [
        (zmin, zmax)
    ] * 4

    cache = {}

    evaluation_counter = 0

    def objective(z):

        nonlocal evaluation_counter

        evaluation_counter += 1

        key = tuple(
            np.round(
                np.asarray(z),
                6
            )
        )

        if key in cache:
            return cache[key]

        controls = controls_from_z(
            z
        )

        profile = (
            ConstantWidthVariableThickness(
                constant_width=b0,
                controls=controls,
                target_volume=target_volume
            )
        )

        # ----------------------------------------------------------
        # Manufacturing checks before expensive BVP solve
        # ----------------------------------------------------------
        ex = profile.extrema(
            cfg,
            n=1001
        )

        violation = 0.0

        if ex["h_min"] < cfg.h_min:

            violation += (
                cfg.h_min
                - ex["h_min"]
            ) / cfg.h_min

        if ex["h_max"] > cfg.h_max:

            violation += (
                ex["h_max"]
                - cfg.h_max
            ) / cfg.h_max

        if (
            ex["max_abs_dh_ds"]
            > cfg.max_dh_ds
        ):

            violation += (
                ex["max_abs_dh_ds"]
                - cfg.max_dh_ds
            ) / cfg.max_dh_ds

        if violation > 0.0:

            J = (
                1000.0
                + cfg.penalty
                * violation**2
            )

            cache[key] = J

            return J

        # ----------------------------------------------------------
        # Fast BVP curve
        # ----------------------------------------------------------
        curve = trace_curve(
            profile,
            cfg,
            accurate=False,
            bidirectional=False
        )

        metrics = calculate_metrics(
            curve,
            cfg,

            stability_sign=(
                reference_metrics.stability_sign
            ),

            frequency_limit=(
                frequency_limit
            )
        )

        if (
            not metrics.valid
            or not np.isfinite(
                metrics.working_window_stress
            )
        ):

            cache[key] = 1.0e6
            return 1.0e6

        # ==========================================================
        # MAIN OBJECTIVE
        #
        # Minimize worst stress over useful low-frequency region.
        # ==========================================================
        J = (
            metrics.working_window_stress
            / reference_stress
        )

        # ----------------------------------------------------------
        # Constraint 1:
        # frequency cannot become significantly worse
        # ----------------------------------------------------------
        fmax = (
            reference_metrics.rated_frequency
            * (
                1.0
                + cfg.max_frequency_increase
            )
        )

        if metrics.rated_frequency > fmax:

            violation_f = (
                metrics.rated_frequency
                - fmax
            ) / fmax

            J += (
                cfg.penalty
                * violation_f**2
            )

        # ----------------------------------------------------------
        # Constraint 2:
        # payload cannot be sacrificed
        # ----------------------------------------------------------
        mmin = (
            reference_metrics.rated_payload_kg
            * (
                1.0
                - cfg.max_payload_loss
            )
        )

        if metrics.rated_payload_kg < mmin:

            violation_m = (
                mmin
                - metrics.rated_payload_kg
            ) / mmin

            J += (
                cfg.penalty
                * violation_m**2
            )

        # ----------------------------------------------------------
        # Constraint 3:
        # low-frequency payload range
        # ----------------------------------------------------------
        minimum_window = (
            reference_window
            * (
                1.0
                - cfg.max_window_loss
            )
        )

        if (
            metrics.low_frequency_payload_window
            < minimum_window
        ):

            violation_w = (
                minimum_window
                - metrics.low_frequency_payload_window
            ) / reference_window

            J += (
                cfg.penalty
                * violation_w**2
            )

        # ----------------------------------------------------------
        # Constraint 4:
        # stress safety
        # ----------------------------------------------------------
        if (
            metrics.working_window_stress
            > cfg.allowable_stress
        ):

            violation_s = (
                metrics.working_window_stress
                - cfg.allowable_stress
            ) / cfg.allowable_stress

            J += (
                cfg.penalty
                * violation_s**2
            )

        # ----------------------------------------------------------
        # Constraint 5:
        # stable branch fraction
        # ----------------------------------------------------------
        if metrics.stable_fraction < 0.95:

            violation_stability = (
                0.95
                - metrics.stable_fraction
            )

            J += (
                cfg.penalty
                * violation_stability**2
            )

        J = float(J)

        cache[key] = J

        if (
            evaluation_counter
            % 25
            == 0
        ):

            print(
                f"eval={evaluation_counter:5d} | "
                f"J={J:10.6f} | "
                f"f={metrics.rated_frequency:8.4f} Hz | "
                f"M={metrics.rated_payload_kg:8.3f} kg | "
                f"sigma={metrics.working_window_stress/1e6:9.2f} MPa"
            )

        return J

    # --------------------------------------------------------------
    # Strong physically meaningful initial seed:
    # fit Bernstein curve to exact-EI profile
    # --------------------------------------------------------------
    z0 = fit_initial_seed(
        exact_profile,
        cfg
    )

    z0 = np.clip(
        z0,
        zmin,
        zmax
    )

    print()
    print(
        "Initial optimization seed:",
        z0
    )

    result = differential_evolution(

        objective,

        bounds=bounds,

        strategy="best1bin",

        popsize=cfg.de_popsize,

        maxiter=cfg.de_maxiter,

        seed=cfg.random_seed,

        tol=1.0e-3,

        mutation=(0.5, 1.0),

        recombination=0.8,

        polish=True,

        updating="immediate",

        workers=1,

        x0=z0,

        disp=True
    )

    best_controls = controls_from_z(
        result.x
    )

    best_profile = (
        ConstantWidthVariableThickness(

            constant_width=b0,

            controls=best_controls,

            target_volume=target_volume
        )
    )

    # --------------------------------------------------------------
    # IMPORTANT:
    #
    # Final result is NOT the fast optimization result.
    #
    # Recalculate with dense bidirectional continuation.
    # --------------------------------------------------------------
    final_curve = trace_curve(

        best_profile,

        cfg,

        accurate=True,

        bidirectional=True
    )

    final_metrics = calculate_metrics(

        final_curve,

        cfg,

        stability_sign=(
            reference_metrics.stability_sign
        ),

        frequency_limit=(
            frequency_limit
        )
    )

    return (
        result,
        best_profile,
        final_curve,
        final_metrics
    )


# ======================================================================
# 15. INTERNAL EI / VOLUME VERIFICATION
# ======================================================================

def verify_exact_equivalent(
    reference: SectionProfile,
    equivalent: SectionProfile,
    cfg: ModelConfig
):

    s = np.linspace(
        0.0,
        cfg.L,
        10001
    )

    Iref = reference.inertia(
        s,
        cfg
    )

    Ieq = equivalent.inertia(
        s,
        cfg
    )

    EI_relative_error = float(
        np.max(
            np.abs(
                Ieq - Iref
            )
            /
            np.maximum(
                np.abs(Iref),
                1.0e-30
            )
        )
    )

    Vref = reference.volume(
        cfg
    )

    Veq = equivalent.volume(
        cfg
    )

    volume_relative_error = (
        abs(
            Veq - Vref
        )
        / Vref
    )

    return (
        EI_relative_error,
        volume_relative_error
    )


# ======================================================================
# 16. SAVE PROFILE
# ======================================================================

def save_profile_csv(
    filename: str,
    profile: SectionProfile,
    cfg: ModelConfig
):

    s = np.linspace(
        0.0,
        cfg.L,
        501
    )

    b = profile.width(
        s,
        cfg
    )

    h = profile.thickness(
        s,
        cfg
    )

    I = profile.inertia(
        s,
        cfg
    )

    data = np.column_stack([
        s,
        s / cfg.L,
        b,
        h,
        I
    ])

    np.savetxt(

        filename,

        data,

        delimiter=",",

        header=(
            "s_m,"
            "s_over_L,"
            "width_m,"
            "thickness_m,"
            "I_m4"
        ),

        comments=""
    )


# ======================================================================
# 17. RESULT SUMMARY
# ======================================================================

def result_dictionary(
    name: str,
    profile: SectionProfile,
    metrics: Metrics,
    cfg: ModelConfig
):

    ex = profile.extrema(
        cfg
    )

    return {

        "design": name,

        "volume_mm3":
            profile.volume(cfg) * 1.0e9,

        "width_min_mm":
            ex["b_min"] * 1.0e3,

        "width_max_mm":
            ex["b_max"] * 1.0e3,

        "thickness_min_mm":
            ex["h_min"] * 1.0e3,

        "thickness_max_mm":
            ex["h_max"] * 1.0e3,

        "max_abs_dh_ds":
            ex["max_abs_dh_ds"],

        "rated_y_mm":
            metrics.rated_y * 1.0e3,

        "rated_payload_kg":
            metrics.rated_payload_kg,

        "rated_stiffness_N_m":
            metrics.rated_stiffness,

        "rated_frequency_Hz":
            metrics.rated_frequency,

        "minimum_frequency_Hz":
            metrics.minimum_frequency,

        "rated_stress_MPa":
            metrics.rated_stress / 1.0e6,

        "working_window_stress_MPa":
            metrics.working_window_stress / 1.0e6,

        "low_frequency_payload_window_kg":
            metrics.low_frequency_payload_window,

        "stable_fraction":
            metrics.stable_fraction,

        "branch_discrepancy":
            metrics.branch_discrepancy,

        "note":
            metrics.note,
    }


def write_summary_csv(
    rows: List[Dict],
    filename: str
):

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(rows)


# ======================================================================
# 18. PLOTS
# ======================================================================

def make_plots(
    results,
    cfg: ModelConfig,
    outdir: str
):

    if plt is None:

        warnings.warn(
            "matplotlib is not installed; plots skipped."
        )

        return

    s = np.linspace(
        0.0,
        cfg.L,
        1001
    )

    # --------------------------------------------------------------
    # Thickness
    # --------------------------------------------------------------
    plt.figure(
        figsize=(7.2, 4.8)
    )

    for name, profile, curve, metrics in results:

        plt.plot(
            s / cfg.L,
            profile.thickness(
                s,
                cfg
            ) * 1.0e3,
            linewidth=2,
            label=name
        )

    plt.xlabel(
        "Normalized arc coordinate s/L"
    )

    plt.ylabel(
        "Thickness (mm)"
    )

    plt.title(
        "Thickness distribution"
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend(
        fontsize=8
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            outdir,
            "01_thickness.png"
        ),
        dpi=240
    )

    plt.close()

    # --------------------------------------------------------------
    # Width
    # --------------------------------------------------------------
    plt.figure(
        figsize=(7.2, 4.8)
    )

    for name, profile, curve, metrics in results:

        plt.plot(
            s / cfg.L,
            profile.width(
                s,
                cfg
            ) * 1.0e3,
            linewidth=2,
            label=name
        )

    plt.xlabel(
        "Normalized arc coordinate s/L"
    )

    plt.ylabel(
        "Width (mm)"
    )

    plt.title(
        "Width distribution"
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend(
        fontsize=8
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            outdir,
            "02_width.png"
        ),
        dpi=240
    )

    plt.close()

    # --------------------------------------------------------------
    # I(s)
    # --------------------------------------------------------------
    plt.figure(
        figsize=(7.2, 4.8)
    )

    for name, profile, curve, metrics in results:

        I = profile.inertia(
            s,
            cfg
        )

        plt.plot(
            s / cfg.L,
            I,
            linewidth=2,
            label=name
        )

    plt.xlabel(
        "Normalized arc coordinate s/L"
    )

    plt.ylabel(
        "Second moment I (m^4)"
    )

    plt.title(
        "Second moment distribution"
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend(
        fontsize=8
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            outdir,
            "03_inertia.png"
        ),
        dpi=240
    )

    plt.close()

    # --------------------------------------------------------------
    # Force / payload curve
    # --------------------------------------------------------------
    plt.figure(
        figsize=(7.2, 4.8)
    )

    for name, profile, curve, metrics in results:

        payload = (
            cfg.n_blades
            * np.abs(curve.Fy)
            / G0
        )

        plt.plot(
            curve.y * 1.0e3,
            payload,
            linewidth=2,
            label=name
        )

        if metrics.valid:

            plt.plot(
                metrics.rated_y * 1.0e3,
                metrics.rated_payload_kg,
                "o"
            )

    plt.xlabel(
        "Blade tip vertical position Y (mm)"
    )

    plt.ylabel(
        "Equivalent total payload (kg)"
    )

    plt.title(
        "GAS load-displacement curve"
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend(
        fontsize=8
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            outdir,
            "04_load_displacement.png"
        ),
        dpi=240
    )

    plt.close()

    # --------------------------------------------------------------
    # Stress at closest point to rated condition
    # --------------------------------------------------------------
    plt.figure(
        figsize=(7.2, 4.8)
    )

    for name, profile, curve, metrics in results:

        if (
            not metrics.valid
            or not curve.solutions
        ):
            continue

        index = int(
            np.argmin(
                np.abs(
                    curve.y
                    - metrics.rated_y
                )
            )
        )

        sol = curve.solutions[
            index
        ]

        b = profile.width(
            sol.s,
            cfg
        )

        h = profile.thickness(
            sol.s,
            cfg
        )

        sigma = (
            6.0
            * np.abs(
                sol.moment
            )
            /
            (
                b
                * h**2
            )
        )

        plt.plot(
            sol.s / cfg.L,
            sigma / 1.0e6,
            linewidth=2,
            label=name
        )

    plt.axhline(
        cfg.allowable_stress / 1.0e6,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="Allowable stress"
    )

    plt.xlabel(
        "Normalized arc coordinate s/L"
    )

    plt.ylabel(
        "Bending stress (MPa)"
    )

    plt.title(
        "Stress distribution near rated point"
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend(
        fontsize=8
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            outdir,
            "05_stress.png"
        ),
        dpi=240
    )

    plt.close()


# ======================================================================
# 19. MAIN
# ======================================================================

def main():

    cfg = ModelConfig()

    os.makedirs(
        cfg.output_directory,
        exist_ok=True
    )

    print("=" * 78)
    print("GAS CONSTANT-WIDTH VARIABLE-THICKNESS OPTIMIZATION")
    print("=" * 78)

    print()
    print(
        f"L                 = {cfg.L*1e3:.3f} mm"
    )

    print(
        f"x/L               = {cfg.x_ratio:.5f}"
    )

    print(
        f"theta0            = {cfg.theta0_deg:.3f} deg"
    )

    print(
        f"thetaL            = {cfg.thetaL_deg:.3f} deg"
    )

    print(
        f"E                 = {cfg.E/1e9:.3f} GPa"
    )

    print(
        f"Poisson ratio     = {cfg.nu:.4f}"
    )

    print(
        f"Poisson correction= {cfg.use_poisson_correction}"
    )

    print(
        f"Reference mapping = {cfg.reference_mapping}"
    )

    # ==============================================================
    # REFERENCE
    # ==============================================================

    reference = (
        ReferenceVariableWidth()
    )

    print()
    print(
        "[1/4] Solving reference variable-width blade..."
    )

    curve_reference = trace_curve(
        reference,
        cfg,
        accurate=True,
        bidirectional=True
    )

    metrics_reference = (
        calculate_metrics(
            curve_reference,
            cfg
        )
    )

    if not metrics_reference.valid:

        raise RuntimeError(
            "Reference calculation failed. "
            "Check geometry, y-range and reference mapping."
        )

    # ==============================================================
    # EXACT EI + VOLUME EQUIVALENT
    # ==============================================================

    print()
    print(
        "[2/4] Constructing exact-EI + equal-volume "
        "constant-width variable-thickness blade..."
    )

    exact_profile = (
        build_exact_equivalent(
            reference,
            cfg
        )
    )

    EI_error, volume_error = (
        verify_exact_equivalent(
            reference,
            exact_profile,
            cfg
        )
    )

    print()
    print(
        "Constant width from exact mapping:"
    )

    print(
        f"    b0 = "
        f"{exact_profile.constant_width*1e3:.6f} mm"
    )

    print(
        f"Max relative I(s) error = "
        f"{EI_error:.6e}"
    )

    print(
        f"Relative volume error   = "
        f"{volume_error:.6e}"
    )

    print()
    print(
        "Solving exact-equivalent blade..."
    )

    curve_exact = trace_curve(
        exact_profile,
        cfg,
        accurate=True,
        bidirectional=True
    )

    metrics_exact = calculate_metrics(

        curve_exact,

        cfg,

        stability_sign=(
            metrics_reference.stability_sign
        ),

        frequency_limit=(
            cfg.low_frequency_factor
            * metrics_reference.rated_frequency
        )
    )

    # ==============================================================
    # OPTIMIZATION
    # ==============================================================

    print()
    print(
        "[3/4] Optimizing variable-thickness profile..."
    )

    (
        optimization_result,
        optimized_profile,
        curve_optimized,
        metrics_optimized

    ) = optimize_variable_thickness(

        reference,
        exact_profile,
        metrics_reference,
        cfg
    )

    if not metrics_optimized.valid:

        raise RuntimeError(
            "Final optimized design is not valid."
        )

    # ==============================================================
    # SUMMARY
    # ==============================================================

    print()
    print(
        "[4/4] Generating final comparison..."
    )

    results = [

        (
            "Reference variable-width",
            reference,
            curve_reference,
            metrics_reference
        ),

        (
            "Exact-EI variable-thickness",
            exact_profile,
            curve_exact,
            metrics_exact
        ),

        (
            "Optimized variable-thickness",
            optimized_profile,
            curve_optimized,
            metrics_optimized
        ),
    ]

    rows = [
        result_dictionary(
            name,
            profile,
            metrics,
            cfg
        )
        for (
            name,
            profile,
            curve,
            metrics
        ) in results
    ]

    print()
    print("=" * 120)

    print(
        f"{'Design':34s}"
        f"{'Payload/kg':>12s}"
        f"{'Freq/Hz':>12s}"
        f"{'Stress/MPa':>14s}"
        f"{'Window/kg':>12s}"
        f"{'hmin/mm':>11s}"
        f"{'hmax/mm':>11s}"
    )

    print("-" * 120)

    for row in rows:

        print(
            f"{row['design'][:34]:34s}"
            f"{row['rated_payload_kg']:12.4f}"
            f"{row['rated_frequency_Hz']:12.5f}"
            f"{row['working_window_stress_MPa']:14.3f}"
            f"{row['low_frequency_payload_window_kg']:12.4f}"
            f"{row['thickness_min_mm']:11.4f}"
            f"{row['thickness_max_mm']:11.4f}"
        )

    print("=" * 120)

    # --------------------------------------------------------------
    # Improvements
    # --------------------------------------------------------------
    stress_reduction = (

        metrics_reference.working_window_stress
        - metrics_optimized.working_window_stress

    ) / metrics_reference.working_window_stress

    frequency_change = (

        metrics_optimized.rated_frequency
        - metrics_reference.rated_frequency

    ) / metrics_reference.rated_frequency

    payload_change = (

        metrics_optimized.rated_payload_kg
        - metrics_reference.rated_payload_kg

    ) / metrics_reference.rated_payload_kg

    print()
    print("FINAL COMPARISON")
    print("----------------")

    print(
        f"Stress reduction = "
        f"{100.0*stress_reduction:+.3f} %"
    )

    print(
        f"Frequency change = "
        f"{100.0*frequency_change:+.3f} %"
    )

    print(
        f"Payload change   = "
        f"{100.0*payload_change:+.3f} %"
    )

    print(
        f"Reference branch discrepancy = "
        f"{curve_reference.branch_discrepancy:.3e}"
    )

    print(
        f"Optimized branch discrepancy = "
        f"{curve_optimized.branch_discrepancy:.3e}"
    )

    print()
    print(
        "Best logarithmic variables:"
    )

    print(
        optimization_result.x
    )

    print()
    print(
        "Best Bernstein controls:"
    )

    print(
        optimized_profile.controls
    )

    # ==============================================================
    # SAVE FILES
    # ==============================================================

    write_summary_csv(

        rows,

        os.path.join(
            cfg.output_directory,
            "comparison_summary.csv"
        )
    )

    save_profile_csv(

        os.path.join(
            cfg.output_directory,
            "reference_profile.csv"
        ),

        reference,
        cfg
    )

    save_profile_csv(

        os.path.join(
            cfg.output_directory,
            "exact_equivalent_profile.csv"
        ),

        exact_profile,
        cfg
    )

    save_profile_csv(

        os.path.join(
            cfg.output_directory,
            "optimized_thickness_profile.csv"
        ),

        optimized_profile,
        cfg
    )

    np.savetxt(

        os.path.join(
            cfg.output_directory,
            "best_optimization_variables.txt"
        ),

        optimization_result.x
    )

    make_plots(
        results,
        cfg,
        cfg.output_directory
    )

    # ==============================================================
    # DECISION FILE
    # ==============================================================

    decision_file = os.path.join(
        cfg.output_directory,
        "decision.txt"
    )

    with open(
        decision_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "GAS CONSTANT-WIDTH VARIABLE-THICKNESS RESULT\n"
        )

        f.write(
            "============================================\n\n"
        )

        f.write(
            f"Stress reduction relative to reference: "
            f"{100*stress_reduction:+.4f}%\n"
        )

        f.write(
            f"Frequency change relative to reference: "
            f"{100*frequency_change:+.4f}%\n"
        )

        f.write(
            f"Payload change relative to reference: "
            f"{100*payload_change:+.4f}%\n"
        )

        f.write(
            f"\nConstant width: "
            f"{exact_profile.constant_width*1e3:.6f} mm\n"
        )

        ex = optimized_profile.extrema(
            cfg
        )

        f.write(
            f"Optimized minimum thickness: "
            f"{ex['h_min']*1e3:.6f} mm\n"
        )

        f.write(
            f"Optimized maximum thickness: "
            f"{ex['h_max']*1e3:.6f} mm\n"
        )

        f.write(
            "\nIMPORTANT:\n"
        )

        f.write(
            "This result demonstrates optimality only inside the "
            "declared 4-DOF Bernstein variable-thickness design space.\n"
        )

        f.write(
            "It is not a proof of universal mathematical global optimality.\n"
        )

        f.write(
            "Final candidates require 3-D geometric-nonlinear FEA.\n"
        )

    print()
    print(
        "Results written to:"
    )

    print(
        os.path.abspath(
            cfg.output_directory
        )
    )


# ======================================================================
# 20. ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    main()
