"""
QZS_App.py — Python/PyQt5 port of QZS_App.m (MATLAB App Designer)
Quasi-Zero Stiffness Nonlinear Isolation System
Based on: Zhao F, et al. Int J Mech Sci, 2021, 192: 106093

Run:
    pip install PyQt5 matplotlib numpy scipy pandas openpyxl
    python QZS_App.py
"""

# ── WSL2 / Qt version-mismatch fix ──────────────────────────────────────────
# PyQt5 (pip) bundles its own Qt5 libs; the system Qt5 libs can clash and
# cause "undefined symbol" errors on the xcb platform plugin.  Re-launch with
# PyQt5's bundled lib path prepended to LD_LIBRARY_PATH.
import sys, os, importlib.util
_pyqt5_lib = os.path.join(
    os.path.dirname(os.path.abspath(importlib.util.find_spec('PyQt5').origin)),
    'Qt5', 'lib')
if os.path.isdir(_pyqt5_lib) and _pyqt5_lib not in os.environ.get('LD_LIBRARY_PATH', ''):
    os.environ['LD_LIBRARY_PATH'] = _pyqt5_lib + ':' + os.environ.get('LD_LIBRARY_PATH', '')
    os.execv(sys.executable, [sys.executable] + sys.argv)
# ────────────────────────────────────────────────────────────────────────────

import sys
import os
import warnings
import numpy as np
import pandas as pd
from scipy.signal import welch

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QDoubleSpinBox, QSizePolicy,
    QFileDialog, QFrame, QScrollArea, QGroupBox, QSlider, QSpacerItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


class QZSApp(QMainWindow):
    TITLE_FS  = 9
    LABEL_FS  = 8
    TICK_FS   = 7
    LEGEND_FS = 7

    def __init__(self):
        super().__init__()
        self.setWindowTitle('QZS Nonlinear Isolation System')
        self.resize(1445, 850)

        # ── geometry defaults ────────────────────────────────────────────────
        self.a1 = 30.0;  self.h3 = 90.0;  self.platform_d = 20.0
        self.h4 = 20.0;  self.d_actual = 48.0;  self.a = 60.0
        self.base_thickness = 5.0;  self.column_thickness = 15.0
        self.support_h = 48.0;  self.support_d = 20.0
        self.base_w = 200.0;  self.base_h = 15.0;  self.base_d = -90.0
        self.p_ratio = 0.5

        # ── spring defaults ──────────────────────────────────────────────────
        self.n_bottom = 16; self.d_bottom = 1.2; self.D_bottom = 14.4
        self.n_upper  = 17; self.d_upper  = 1.2; self.D_upper  = 14.4
        self.n_mid    = 32; self.d_mid    = 1.2; self.D_mid    = 14.4
        self.n_lower  = 17; self.d_lower  = 1.2; self.D_lower  = 14.4

        # ── state arrays ────────────────────────────────────────────────────
        self.y_hat         = np.linspace(-3.0, 3.0, 1000)
        self.y_dim         = np.linspace(-100.0, 100.0, 1000)
        self.f_hat_theory  = np.zeros(1000)
        self.K_hat_theory  = np.zeros(1000)
        self.f_actual_real = np.zeros(1000)
        self.K_actual_real = np.zeros(1000)
        self.test_params   = [60.0, 0.0, 0.0, 0.0]
        self.f0_val        = 0.0
        self.L0_bottom = self.L0_upper = self.L0_mid = self.L0_lower = 0.0

        # ── signal data ──────────────────────────────────────────────────────
        self.t_matrix = self.v_in_data = self.v_out_data = None
        self.f_psd_vec = self.v_in_psd_vec = self.v_out_psd = None
        self.fs_rate = self.N_points = None
        # stored after CSV load — reused on every parameter change
        self._sig_v_in  = None   # input signal array
        self._sig_fs    = None   # input sample rate
        self._sig_t     = None   # time array
        self._sig_v_ref = None   # reference signal (optional)
        self._sig_fs_ref= None

        self._block_signals = False
        self._setup_ui()
        self._map_geometry()
        self._calc_full()

    # ════════════════════════════════════════════════════════════════════════
    # UI construction
    # ════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ── left panel ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(250)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 6, 5, 6)
        left_layout.setSpacing(6)
        scroll.setWidget(left_widget)
        root.addWidget(scroll)

        # ── shared style helpers ─────────────────────────────────────────────
        GRP_STYLE = """
            QGroupBox {
                font-weight: bold; font-size: 10px;
                border: 1px solid #b0b8c8;
                border-radius: 5px; margin-top: 8px;
                padding-top: 4px; background: #f7f9fc;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 4px; color: #2c4a7c;
            }
        """

        def spin(val, lo=-1e6, hi=1e6, dec=3, step=0.001, tip=''):
            s = QDoubleSpinBox()
            s.setDecimals(dec); s.setRange(lo, hi)
            s.setValue(val); s.setSingleStep(step)
            s.setMinimumWidth(72); s.setMaximumWidth(90)
            if tip: s.setToolTip(tip)
            return s

        def param_row(label, sp, tip=''):
            w = QWidget(); h = QHBoxLayout(w)
            h.setContentsMargins(2, 1, 2, 1); h.setSpacing(4)
            lbl = QLabel(label)
            lbl.setFixedWidth(118)
            lbl.setStyleSheet('font-size:10px;')
            if tip: lbl.setToolTip(tip)
            h.addWidget(lbl); h.addWidget(sp); h.addStretch()
            return w

        def make_group(title, style=GRP_STYLE):
            gb = QGroupBox(title)
            gb.setStyleSheet(style)
            vb = QVBoxLayout(gb)
            vb.setContentsMargins(6, 4, 6, 6)
            vb.setSpacing(3)
            return gb, vb

        # ════════════════════════════════════════════════════════════════════
        # Section 1 — Dimensionless Theory
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('① Dimensionless Parameters')

        self.delta_hat_edit = spin(0.5,   step=0.001, tip='δ̂ = δ/√(a²+h₁²)  Pre-compression ratio')
        self.a_hat_edit     = spin(0.755, step=0.001, tip='â = a/√(a²+h₁²)  Geometry ratio (0<â<1)')
        self.alpha_edit     = spin(0.942, step=0.001, tip='α = k₁/k₂  Oblique-to-vertical stiffness ratio')
        self.alpha1_edit    = spin(0.501, step=0.001, tip='α₁ = k₃/k₂  Mid-to-vertical stiffness ratio')
        self.gamma_edit     = spin(2.143, step=0.001, tip='γ = h/d  Height ratio (γ > 1)')

        for lbl, sp, cb in [
            ('δ̂  (delta_hat)',  self.delta_hat_edit, self._on_left_changed),
            ('â  (a_hat)',       self.a_hat_edit,     self._on_left_changed),
            ('α  (alpha)',       self.alpha_edit,     self._on_left_changed),
            ('α₁ (alpha1)',      self.alpha1_edit,    self._on_left_changed),
            ('γ  (gamma)',       self.gamma_edit,     self._on_left_changed),
        ]:
            sp.valueChanged.connect(cb)
            vb.addWidget(param_row(lbl, sp))
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Section 2 — Physical / Material Parameters
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('② Physical & Material')

        self.a_target_edit = spin(60.0, dec=1, step=1, tip='Target horizontal arm length (mm)')
        self.tau_p_edit    = spin(70.0, dec=1, step=1, tip='Allowable shear stress τ_p (MPa)')
        self.G_edit        = spin(75000.0, dec=0, step=500, tip='Shear modulus G (MPa) — steel ≈ 75 000')

        for lbl, sp, cb in [
            ('a  target (mm)',    self.a_target_edit, self._calc_workflow_only),
            # τ_p is only used in Excel spring-design export — no plot depends on it
            ('τ_p  allow. (MPa)', self.tau_p_edit,   lambda *_: None),
            ('G  shear (MPa)',    self.G_edit,        self._calc_full),
        ]:
            sp.valueChanged.connect(cb)
            vb.addWidget(param_row(lbl, sp))

        design_btn = QPushButton('⚙  Design Springs → Excel')
        design_btn.setStyleSheet(
            'background:#2e7d52;color:white;font-weight:bold;'
            'font-size:11px;border-radius:4px;padding:4px;')
        design_btn.setFixedHeight(30)
        design_btn.setToolTip('Compute spring candidates and save to Spring_Parameters.xlsx')
        design_btn.clicked.connect(self._save_design_data)
        vb.addWidget(design_btn)
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Section 3 — Spring Coil Parameters
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('③ Spring Coil Parameters')

        # column header
        hdr = QWidget(); hh = QHBoxLayout(hdr)
        hh.setContentsMargins(2, 0, 2, 0); hh.setSpacing(4)
        for txt, wd in [('Spring', 52), ('n turns', 52), ('d wire\n(mm)', 52), ('D coil\n(mm)', 52)]:
            l = QLabel(txt); l.setFixedWidth(wd)
            l.setStyleSheet('font-size:9px; font-weight:bold; color:#2c4a7c;')
            l.setAlignment(Qt.AlignCenter); hh.addWidget(l)
        vb.addWidget(hdr)

        self.U_turns = spin(17,  1, 999, 0, 1,   tip='Active coils — Upper spring')
        self.U_wire  = spin(1.2, 0.1, 20, 2, 0.05, tip='Wire diameter d (mm) — Upper')
        self.U_cyl   = spin(14.4,0.5,200, 1, 0.5,  tip='Mean coil diameter D (mm) — Upper')
        self.M_turns = spin(32,  1, 999, 0, 1,   tip='Active coils — Mid spring')
        self.M_wire  = spin(1.2, 0.1, 20, 2, 0.05, tip='Wire diameter d (mm) — Mid')
        self.M_cyl   = spin(14.4,0.5,200, 1, 0.5,  tip='Mean coil diameter D (mm) — Mid')
        self.D_turns = spin(17,  1, 999, 0, 1,   tip='Active coils — Lower spring')
        self.D_wire  = spin(1.2, 0.1, 20, 2, 0.05, tip='Wire diameter d (mm) — Lower')
        self.D_cyl   = spin(14.4,0.5,200, 1, 0.5,  tip='Mean coil diameter D (mm) — Lower')
        self.B_turns = spin(16,  1, 999, 0, 1,   tip='Active coils — Bottom (vertical) spring')
        self.B_wire  = spin(1.2, 0.1, 20, 2, 0.05, tip='Wire diameter d (mm) — Bottom')
        self.B_cyl   = spin(14.4,0.5,200, 1, 0.5,  tip='Mean coil diameter D (mm) — Bottom')

        _spring_colors = {'Upper':'#e8f4ec','Mid':'#e8ecf4','Lower':'#f4ece8','Bot':'#f4f4e8'}
        for label, s_n, s_d, s_D, n_k, d_k, D_k, bg in [
            ('Upper', self.U_turns, self.U_wire, self.U_cyl, 'n_upper','d_upper','D_upper','#e8f4ec'),
            ('Mid',   self.M_turns, self.M_wire, self.M_cyl, 'n_mid',  'd_mid',  'D_mid',  '#e8ecf4'),
            ('Lower', self.D_turns, self.D_wire, self.D_cyl, 'n_lower','d_lower','D_lower','#f4ece8'),
            ('Bottom',self.B_turns, self.B_wire, self.B_cyl, 'n_bottom','d_bottom','D_bottom','#f4f4e8'),
        ]:
            rw = QWidget(); rw.setStyleSheet(f'background:{bg};border-radius:3px;')
            rl = QHBoxLayout(rw); rl.setContentsMargins(2, 2, 2, 2); rl.setSpacing(4)
            lb = QLabel(label); lb.setFixedWidth(52)
            lb.setStyleSheet('font-size:10px;font-weight:bold;'); lb.setAlignment(Qt.AlignCenter)
            rl.addWidget(lb)
            for sp, key in [(s_n, n_k), (s_d, d_k), (s_D, D_k)]:
                sp.valueChanged.connect(lambda v, k=key: self._spring_changed(k, v))
                sp.setMinimumWidth(48); sp.setMaximumWidth(58)
                rl.addWidget(sp)
            vb.addWidget(rw)
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Section 4 — Assembly Geometry
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('④ Assembly Geometry')

        # W / H / D sub-header
        shdr = QWidget(); sh = QHBoxLayout(shdr)
        sh.setContentsMargins(2, 0, 2, 0); sh.setSpacing(4)
        for txt, wd in [('Part', 52), ('W (mm)', 52), ('H (mm)', 52), ('D (mm)', 52)]:
            l = QLabel(txt); l.setFixedWidth(wd)
            l.setStyleSheet('font-size:9px;font-weight:bold;color:#2c4a7c;')
            l.setAlignment(Qt.AlignCenter); sh.addWidget(l)
        vb.addWidget(shdr)

        def geom_row(label, wv, hv, dv, tip=''):
            rw = QWidget(); rl = QHBoxLayout(rw)
            rl.setContentsMargins(2, 2, 2, 2); rl.setSpacing(4)
            lb = QLabel(label); lb.setFixedWidth(52)
            lb.setStyleSheet('font-size:10px;font-weight:bold;')
            lb.setAlignment(Qt.AlignCenter); rl.addWidget(lb)
            spins = []
            for val in [wv, hv, dv]:
                s = QDoubleSpinBox(); s.setDecimals(0); s.setRange(-9999, 9999)
                s.setValue(val); s.setMinimumWidth(48); s.setMaximumWidth(58)
                if tip: s.setToolTip(tip)
                s.valueChanged.connect(self._update_geometry_span)
                rl.addWidget(s); spins.append(s)
            return rw, spins

        row, self.plat_spins = geom_row('Platform', 20, self.h3, self.platform_d,
                                         'Platform width, height, depth (mm)')
        vb.addWidget(row)
        row, self.supp_spins = geom_row('Support', self.column_thickness, self.support_h,
                                         self.support_d, 'Column width, height, depth (mm)')
        vb.addWidget(row)
        row, self.base_spins = geom_row('Base', self.base_w, self.base_h, self.base_d,
                                         'Base width, height, depth (mm)')
        vb.addWidget(row)

        self.h4_edit       = spin(self.h4,    lo=0, hi=500, dec=1, step=1,
                                   tip='h4: vertical offset of spring attachment on platform (mm)')
        self.a_actual_edit = spin(60.0,        lo=1, hi=500, dec=1, step=1,
                                   tip='Actual horizontal arm length a (mm)')
        self.d_actual_edit = spin(self.d_actual,lo=1,hi=500, dec=1, step=1,
                                   tip='Actual column height / spring mount height d (mm)')
        self.h4_edit.valueChanged.connect(self._update_geometry_span)
        self.a_actual_edit.valueChanged.connect(self._calc_workflow_only)
        self.d_actual_edit.valueChanged.connect(self._calc_workflow_only)

        for lbl, sp in [('h4 offset (mm)', self.h4_edit),
                         ('a actual (mm)',  self.a_actual_edit),
                         ('d actual (mm)',  self.d_actual_edit)]:
            vb.addWidget(param_row(lbl, sp))
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Section 5 — Displacement Preview
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('⑤ Displacement Preview')

        self.y_disp_edit = spin(0.0, lo=-100.0, hi=100.0, dec=1, step=1.0,
                                 tip='Platform displacement y (mm) — animates assembly view')
        self.y_disp_edit.valueChanged.connect(self._on_disp_preview_changed)

        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setRange(-100, 100); self.y_slider.setValue(0)
        self.y_slider.setToolTip('Drag to preview platform displacement')
        self.y_slider.valueChanged.connect(
            lambda v: self.y_disp_edit.setValue(float(v)))
        self.y_disp_edit.valueChanged.connect(
            lambda v: self.y_slider.setValue(int(v)))

        vb.addWidget(self.y_slider)
        vb.addWidget(param_row('y preview (mm)', self.y_disp_edit,
                                'Displace platform to see spring deformation'))
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Section 6 — Vibration / PSD Analysis
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('⑥ Vibration Analysis')

        load_btn = QPushButton('📂  Load CSV & Compute PSD')
        load_btn.setStyleSheet(
            'background:#c0591a;color:white;font-weight:bold;'
            'font-size:11px;border-radius:4px;padding:4px;')
        load_btn.setFixedHeight(30)
        load_btn.setToolTip('Load input signal CSV, optionally a reference CSV,\n'
                            'then compute PSD using current group-1 parameters.')
        load_btn.clicked.connect(self._process_vibration_signals)
        vb.addWidget(load_btn)

        self.C_edit  = spin(20.0, lo=0, hi=1e5, dec=2, step=0.5,
                             tip='Viscous damping coefficient C (N·s/m)')
        self.Ze_edit = spin(3.0,  lo=0, hi=100,  dec=2, step=0.1,
                             tip='Excitation amplitude Ze (mm)')
        for lbl, sp, cb in [
            ('Damping C (N·s/m)', self.C_edit,  self._calc_full),
            ('Ze amplitude (mm)', self.Ze_edit, self._calc_full),
        ]:
            sp.valueChanged.connect(cb)
            vb.addWidget(param_row(lbl, sp))
        left_layout.addWidget(grp)

        # ════════════════════════════════════════════════════════════════════
        # Log output
        # ════════════════════════════════════════════════════════════════════
        grp, vb = make_group('ℹ  Output Log')
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont('Courier', 8))
        self.log_area.setMinimumHeight(100)
        self.log_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        vb.addWidget(self.log_area)
        left_layout.addWidget(grp)
        left_layout.addStretch()

        # ── matplotlib canvas ────────────────────────────────────────────────
        self.fig = Figure(figsize=(13, 8))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.canvas)

        gs = self.fig.add_gridspec(
            2, 3, hspace=0.48, wspace=0.42,
            left=0.05, right=0.98, top=0.96, bottom=0.06
        )
        self.ax_geom = self.fig.add_subplot(gs[0, 0])   # 2-D side view
        self.ax1     = self.fig.add_subplot(gs[0, 1])
        self.ax_dim  = self.fig.add_subplot(gs[0, 2])
        self.ax3     = self.fig.add_subplot(gs[1, 0])
        self.ax4     = self.fig.add_subplot(gs[1, 1])
        self.ax5     = self.fig.add_subplot(gs[1, 2])

        # twin axes stored so we can clear them properly on refresh
        self.ax1_twin   = self.ax1.twinx()
        self.ax_dim_twin = self.ax_dim.twinx()

        # inset position in figure-fraction coordinates (approx bottom-left region)
        self.ax3_inset = self.fig.add_axes([0.11, 0.08, 0.065, 0.115])

        self.ax4.set_title('Time Domain Vibration Signals',
                           fontsize=self.TITLE_FS, fontweight='bold')
        self.ax5.set_title('Power Spectral Density (PSD)',
                           fontsize=self.TITLE_FS, fontweight='bold')

        self.fig.text(0.52, 0.005,
                      '@ Zhao F, et al. Int J Mech Sci, 2021, 192: 106093',
                      ha='center', fontsize=7, style='italic', color='gray')

    # ════════════════════════════════════════════════════════════════════════
    # Callbacks
    # ════════════════════════════════════════════════════════════════════════

    def _on_left_changed(self, *_):
        if self._params_valid(): self._calc_workflow_only()

    def _spring_changed(self, key, val):
        setattr(self, key, val)
        self._map_geometry()
        if self._params_valid(): self._calc_full()

    def _update_geometry_span(self, *_):
        self._map_geometry()
        if self._params_valid(): self._calc_full()

    def _on_disp_preview_changed(self, *_):
        """Redraw only the geometry with the new preview displacement."""
        self._plot_geometry(*self.test_params)
        self.canvas.draw_idle()

    def _params_valid(self):
        """Return False while the user is mid-edit and values are degenerate."""
        try:
            ah = self.a_hat_edit.value()
            gm = self.gamma_edit.value()
            al = self.alpha_edit.value()
            return (0 < ah < 1) and (abs(gm - 1) > 1e-6) and (abs(al) > 1e-9)
        except Exception:
            return False

    # ════════════════════════════════════════════════════════════════════════
    # Core physics
    # ════════════════════════════════════════════════════════════════════════

    def _map_geometry(self):
        self.a1          = self.plat_spins[0].value()
        self.h3          = self.plat_spins[1].value()
        self.platform_d  = self.plat_spins[2].value()
        self.a           = self.a_target_edit.value()
        self.h4          = self.h4_edit.value()
        self.d_actual    = self.d_actual_edit.value()
        self.column_thickness = self.supp_spins[0].value()
        self.support_h   = self.supp_spins[1].value()
        self.support_d   = self.supp_spins[2].value()
        self.base_w      = self.base_spins[0].value()
        self.base_h      = self.base_spins[1].value()
        self.base_thickness = self.base_h
        self.base_d      = self.base_spins[2].value()

        self.n_bottom = self.B_turns.value(); self.d_bottom = self.B_wire.value(); self.D_bottom = self.B_cyl.value()
        self.n_upper  = self.U_turns.value(); self.d_upper  = self.U_wire.value(); self.D_upper  = self.U_cyl.value()
        self.n_mid    = self.M_turns.value(); self.d_mid    = self.M_wire.value(); self.D_mid    = self.M_cyl.value()
        self.n_lower  = self.D_turns.value(); self.d_lower  = self.D_wire.value(); self.D_lower  = self.D_cyl.value()

        p = self.p_ratio
        self.L0_bottom = self.n_bottom * p * self.D_bottom + 2 * self.d_bottom
        self.L0_upper  = self.n_upper  * p * self.D_upper  + 2 * self.d_upper
        self.L0_mid    = self.n_mid    * p * self.D_mid    + 2 * self.d_mid
        self.L0_lower  = self.n_lower  * p * self.D_lower  + 2 * self.d_lower

        a_hat = self.a_hat_edit.value(); gamma = self.gamma_edit.value()
        h1 = np.sqrt(max(0, self.a**2 * (1/a_hat**2 - 1)))
        d_p = h1 / (gamma - 1)
        self.test_params = [self.a, h1, h1 + d_p, h1 + 2*d_p]

        G = self.G_edit.value()
        self.f0_val = (G * self.d_bottom**4) / (8 * self.D_bottom**3 * self.n_bottom)
        self.y_hat  = np.linspace(-3.0, 3.0, 1000)
        self.y_dim  = np.linspace(-100.0, 100.0, 1000)   # actual displacement [mm]

    def _eval_system_response(self, delta_hat, a_hat, alpha, alpha1, gamma):
        if abs(gamma - 1) < 1e-9 or a_hat <= 0 or a_hat >= 1:
            return np.zeros_like(self.y_hat), np.ones_like(self.y_hat)
        rho = (1 - a_hat**2) / (gamma - 1)**2
        sq1 = np.sqrt(max(0, 1 - a_hat**2))
        sq_rho = np.sqrt(max(0, rho))
        delta_hat1 = 1 - np.sqrt(1 + 2*sq1*sq_rho + rho)       + delta_hat
        delta_hat2 = 1 - np.sqrt(1 + 4*sq1*sq_rho + 4*rho)     + delta_hat
        x_e_hat    = sq1 + sq_rho

        K_hat = np.zeros(len(self.y_hat))
        f_hat = np.zeros(len(self.y_hat))

        for i, y in enumerate(self.y_hat):
            xi = x_e_hat + y
            P1 = sq1 - xi
            P2 = 1 - 2*sq1*xi + xi**2
            P3 = 1 + delta_hat
            P4 = np.sqrt(max(0, 1 - a_hat**2 + rho + 2*sq1*sq_rho)) - xi
            P5 = (1 + rho + 2*sq1*sq_rho
                  - 2*np.sqrt(max(0, 1 - a_hat**2 + rho + 2*sq1*sq_rho))*xi + xi**2)
            P6 = np.sqrt(max(0, 1 + 2*sq1*sq_rho + rho)) + delta_hat1
            P7 = sq1 + 2*sq_rho - xi
            P8 = (1 + 4*sq1*sq_rho + 4*rho
                  - 2*(sq1 + 2*sq_rho)*xi + xi**2)
            P9 = np.sqrt(max(0, 1 + 4*sq1*sq_rho + 4*rho)) + delta_hat2

            dP2 = -2*sq1 + 2*xi
            dP5 = -2*np.sqrt(max(0, 1 - a_hat**2 + rho + 2*sq1*sq_rho)) + 2*xi
            dP8 = -2*(sq1 + 2*sq_rho) + 2*xi

            eps = 1e-30
            dN1 = 2*alpha*(1 - P3/max(eps,np.sqrt(P2))) - alpha*P1*(P2+eps)**(-1.5)*P3*dP2
            dN3 = 2*alpha1*(1 - P6/max(eps,np.sqrt(P5))) - alpha1*P4*(P5+eps)**(-1.5)*P6*dP5
            dN5 = 2*alpha*(1 - P9/max(eps,np.sqrt(P8))) - alpha*P7*(P8+eps)**(-1.5)*P9*dP8

            K_hat[i] = 1 + dN1 + dN3 + dN5
            f_hat[i] = (xi
                        - 2*alpha *P1*(np.sqrt(max(0,P2))-P3)/max(eps,np.sqrt(P2))
                        - 2*alpha1*P4*(np.sqrt(max(0,P5))-P6)/max(eps,np.sqrt(P5))
                        - 2*alpha *P7*(np.sqrt(max(0,P8))-P9)/max(eps,np.sqrt(P8)))

        return f_hat, K_hat

    def _f_actual_N(self, y_arr, a, d_vert):
        """Force [N] vs displacement y [mm].
        Uses COMPUTED free lengths and spring stiffnesses from the current UI
        so that every spinner (n, d_wire, D_coil, G, h4, d_actual …) drives the plot.

        a      : horizontal arm length [mm]  (= a_actual)
        d_vert : vertical spring-attachment offset [mm]  (= d_actual − h4)
        """
        G = self.G_edit.value()

        # Spring stiffnesses [N/mm] from coil geometry
        def k_spring(d_w, D_c, n_t):
            n_eff = max(1, n_t - 2)
            return (G * d_w**4) / (8.0 * D_c**3 * n_eff)

        k_up  = k_spring(self.d_upper,  self.D_upper,  self.n_upper)
        k_mid = k_spring(self.d_mid,    self.D_mid,    self.n_mid)
        k_lo  = k_spring(self.d_lower,  self.D_lower,  self.n_lower)
        k_bot = k_spring(self.d_bottom, self.D_bottom, self.n_bottom)

        # Free lengths [mm] already stored after _map_geometry()
        L0_up  = self.L0_upper
        L0_mid = self.L0_mid
        L0_lo  = self.L0_lower
        L0_bot = self.L0_bottom

        # Bottom spring equilibrium compressed length from geometry
        L_eq_bot = abs(-self.h3 / 2.0 - self.base_d)

        def sL(x, dv): return np.sqrt(np.maximum(x**2 + dv**2, 1e-12))

        L1 = sL(a + y_arr, d_vert)
        L2 = sL(y_arr,     d_vert)
        L3 = sL(a - y_arr, d_vert)

        f = (-2*(L0_up  - L1)*(a + y_arr)*k_up  / L1 +
              2*(L0_mid  - L2)*(-y_arr)   *k_mid / L2 +
              2*(L0_lo   - L3)*(a - y_arr)*k_lo  / L3 +
             (L0_bot - L_eq_bot + y_arr)  *k_bot)
        return f

    def _compute_K_actual_from_f(self):
        dy = self.y_dim[1] - self.y_dim[0]
        f  = self.f_actual_real
        K  = np.zeros_like(f)
        K[1:-1] = (f[2:] - f[:-2]) / (2*dy)
        K[0]    = (-3*f[0] + 4*f[1] - f[2]) / (2*dy)
        K[-1]   = (3*f[-1] - 4*f[-2] + f[-3]) / (2*dy)
        self.K_actual_real = K

    def _calc_full(self, *_):
        self.h4 = self.h4_edit.value()
        dh = self.delta_hat_edit.value(); ah = self.a_hat_edit.value()
        al = self.alpha_edit.value(); al1 = self.alpha1_edit.value()
        gm = self.gamma_edit.value()

        self.f_hat_theory, self.K_hat_theory = self._eval_system_response(dh, ah, al, al1, gm)

        a_act  = self.a_actual_edit.value()
        d_vert = self.d_actual_edit.value() - self.h4_edit.value()   # vertical offset
        self.f_actual_real = self._f_actual_N(self.y_dim, a_act, d_vert)
        self._compute_K_actual_from_f()

        G = self.G_edit.value()
        k_upper  = (G*self.d_upper**4)  / (8*self.D_upper**3  * max(1, self.n_upper-2))
        k_mid    = (G*self.d_mid**4)    / (8*self.D_mid**3    * max(1, self.n_mid-2))
        k_bottom = (G*self.d_bottom**4) / (8*self.D_bottom**3 * max(1, self.n_bottom-2))

        s_w       = self.supp_spins[0].value()
        a_assembly = (self.a1/2) + a_act + (s_w/2)
        d_assembly = self.d_actual_edit.value() - self.h4

        self.log_area.setPlainText('\n'.join([
            '--- Spring Stiffness ---',
            f'k1 (upper): {k_upper*1000:.1f} N/m',
            f'k2 (bot):   {k_bottom*1000:.1f} N/m',
            f'k3 (mid):   {k_mid*1000:.1f} N/m',
            '--- Assembly Dims ---',
            f'a_assembly: {a_assembly:.1f} mm',
            f'd_assembly: {d_assembly:.1f} mm',
            '--- Free Lengths ---',
            f'L1 (upper): {self.L0_upper:.1f} mm  (p={self.p_ratio})',
            f'L2 (mid):   {self.L0_mid:.1f} mm  (p={self.p_ratio})',
            f'L3 (lower): {self.L0_lower:.1f} mm  (p={self.p_ratio})',
            f'L  (bot):   {self.L0_bottom:.1f} mm  (p={self.p_ratio})',
        ]))

        self._refresh_plots()

    def _calc_workflow_only(self, *_):
        self.a        = self.a_target_edit.value()
        self.h4       = self.h4_edit.value()
        self.d_actual = self.d_actual_edit.value()
        self.base_thickness = self.base_spins[1].value()

        dh = self.delta_hat_edit.value(); ah = self.a_hat_edit.value()
        al = self.alpha_edit.value(); al1 = self.alpha1_edit.value()
        gm = self.gamma_edit.value()
        self.f_hat_theory, self.K_hat_theory = self._eval_system_response(dh, ah, al, al1, gm)

        a_act  = self.a_actual_edit.value()
        d_vert = self.d_actual_edit.value() - self.h4_edit.value()
        self.f_actual_real = self._f_actual_N(self.y_dim, a_act, d_vert)
        self._compute_K_actual_from_f()
        self._map_geometry()
        self._refresh_plots()

    # ════════════════════════════════════════════════════════════════════════
    # Transmissibility
    # ════════════════════════════════════════════════════════════════════════

    def _transmissibility(self, mu1, mu3, Omega, Ze, zeta):
        if Omega < 1e-6:
            return 1.0
        A = (9/16)*mu3**2*Ze**4
        B = float(np.real(1.5*mu3*(mu1 - Omega**2)*Ze**2))
        C = (mu1 - Omega**2)**2 + (2*zeta*Omega)**2
        D = -Omega**4
        roots = np.roots([A, B, C, D])
        cands = [r.real for r in roots if abs(r.imag) < 1e-6 and r.real > 0]
        if not cands:
            Z2 = (Omega**2 / np.sqrt((mu1-Omega**2)**2 + (2*zeta*Omega)**2))**2
        else:
            Z2 = min(cands)
        Zh = np.sqrt(Z2)
        cos_phi = np.clip(
            (0.75*mu3*Ze**2*Zh**3 + (mu1-Omega**2)*Zh) / Omega**2, -1, 1)
        return float(np.sqrt(max(0, 1 + 2*Zh*cos_phi + Zh**2)))

    def _transmissibility_vec(self, mu1, mu3, f_arr, f0_sys, Ze, zeta):
        """Vectorised transmissibility on a frequency array [Hz].
        Computes Ta at N_grid points then interpolates — avoids per-sample roots().
        """
        N_grid = 2000
        f_grid  = np.linspace(0, max(f_arr[-1], 1e-6), N_grid)
        Om_grid = f_grid / max(f0_sys, 1e-9)
        Ta_grid = np.array([self._transmissibility(mu1, mu3, O, Ze, zeta)
                            for O in Om_grid])
        return np.interp(f_arr, f_grid, Ta_grid)

    # ════════════════════════════════════════════════════════════════════════
    # Plot refresh
    # ════════════════════════════════════════════════════════════════════════

    def _refresh_plots(self):
        self._plot_geometry(*self.test_params)
        self._plot_ax1()
        self._plot_ax_dim()
        self._plot_ax3()
        if self._sig_v_in is not None:
            self._update_psd_plots()
        self.canvas.draw()

    def _plot_ax1(self):
        ax = self.ax1; ax.cla(); ax.grid(True)
        ax2 = self.ax1_twin; ax2.cla()
        ax.tick_params(labelsize=self.TICK_FS)
        pf, = ax.plot(self.y_hat, self.f_hat_theory,
                      color=[0.0,0.45,0.74], ls='--', lw=2)
        ax.set_ylabel('Dimensionless Force $\\hat{f}$',
                      fontsize=self.LABEL_FS, color=[0.0,0.45,0.74])
        ax.tick_params(axis='y', labelcolor=[0.0,0.45,0.74], labelsize=self.TICK_FS)
        ax.set_ylim(-6, 6); ax.set_xlim(-3, 3)
        ax.set_title('Dimensionless F & K  [driven by ①]',
                     fontsize=self.TITLE_FS, fontweight='bold')
        pk, = ax2.plot(self.y_hat, self.K_hat_theory,
                       color=[0.85,0.33,0.10], ls='--', lw=2)
        ax2.set_ylabel('Dimensionless Stiffness $\\hat{K}$',
                       fontsize=self.LABEL_FS, color=[0.85,0.33,0.10])
        ax2.tick_params(axis='y', labelcolor=[0.85,0.33,0.10], labelsize=self.TICK_FS)
        ax2.set_ylim(0, 12)
        ax.set_xlabel('Dimensionless Displacement $\\hat{y}$', fontsize=self.LABEL_FS)
        ax.legend([pf, pk], ['Force (Theory)', 'Stiffness (Theory)'],
                  loc='upper left', fontsize=self.LEGEND_FS)

    def _plot_ax_dim(self):
        ax = self.ax_dim; ax.cla(); ax.grid(True)
        ax2 = self.ax_dim_twin; ax2.cla()
        ax.tick_params(labelsize=self.TICK_FS)
        # f_actual_real is already in N, K_actual_real in N/mm — no extra scaling
        pf, = ax.plot(self.y_dim, self.f_actual_real, color=[0.0,0.2,0.5], lw=2.5)
        ax.set_ylabel('Force (N)', fontsize=self.LABEL_FS, color=[0.0,0.45,0.74])
        ax.tick_params(axis='y', labelcolor=[0.0,0.45,0.74], labelsize=self.TICK_FS)
        ax.set_title('Force & Stiffness  [driven by ③ ④]',
                     fontsize=self.TITLE_FS, fontweight='bold')
        pk, = ax2.plot(self.y_dim, self.K_actual_real, color=[0.55,0.12,0.0], lw=2.5)
        ax2.set_ylabel('Stiffness (N/mm)', fontsize=self.LABEL_FS, color=[0.85,0.33,0.10])
        ax2.tick_params(axis='y', labelcolor=[0.85,0.33,0.10], labelsize=self.TICK_FS)
        ax.set_xlabel('Displacement y (mm)', fontsize=self.LABEL_FS)
        ax.legend([pf, pk], ['Force (Actual)', 'Stiffness (Actual)'],
                  loc='upper left', fontsize=self.LEGEND_FS)

    def _plot_ax3(self):
        ah = self.a_hat_edit.value(); gm = self.gamma_edit.value()
        al = self.alpha_edit.value(); al1 = self.alpha1_edit.value()
        dh = self.delta_hat_edit.value()
        if abs(gm - 1) < 1e-9 or ah <= 0 or ah >= 1:
            return
        rho = (1 - ah**2) / (gm - 1)**2
        mu1 = (1 + 4*al + 2*al1
               - 2*(1+dh)*(2*al*ah**2 / (np.sqrt(rho+ah**2))**3 + al1/ah))
        mu3 = (-2*(1+dh)*(2*al*(12*ah**2*rho - 3*ah**4)
               / ((np.sqrt(rho+ah**2))**7) + al1*(-3)/ah**3)) / 6

        # ── compute Ze_hat and zeta from UI spinboxes ────────────────────────
        M_load = 2.0; g_acc = 9.81
        a_t  = self.a_target_edit.value() / 1000   # m
        h1_t = self.test_params[1]        / 1000   # m
        denom = np.sqrt(max(1e-30, a_t**2 + h1_t**2))
        k2_Nm   = (M_load*g_acc) / (1.229 * denom)
        omega0  = np.sqrt(k2_Nm / M_load)
        Ze_hat  = self.Ze_edit.value() / 1000 / denom
        zeta_ui = self.C_edit.value() * omega0 / (2 * k2_Nm)

        Om = np.arange(0, 10.01, 0.01)
        Ta_th  = np.array([self._transmissibility(mu1, mu3, O, Ze_hat, zeta_ui) for O in Om])
        Ta_act = np.array([self._transmissibility(0.0022, 0.00065, O, Ze_hat, 0.18) for O in Om])

        ax = self.ax3; ax.cla(); ax.grid(True)
        ax.tick_params(labelsize=self.TICK_FS)
        ax.plot(Om, Ta_th,  ls='--', lw=1.5, color=[0,0.447,0.741])
        ax.plot(Om, Ta_act, ls='-',  lw=2.0, color=[0.12,0.53,0.22])
        ax.set_xlim(0, 10); ax.set_ylim(0, 2)
        ax.set_xlabel('Frequency Ratio  Ω = ω/ω₀', fontsize=self.LABEL_FS)
        ax.set_ylabel('Transmissibility $T_a$', fontsize=self.LABEL_FS)
        ax.set_title(
            f'Transmissibility  [① ⑥]  ζ={zeta_ui:.3f}, Zₑ={self.Ze_edit.value():.1f} mm',
            fontsize=self.TITLE_FS, fontweight='bold')
        ax.legend([f'Theory (μ₁={mu1:.4f})', 'Reference (fixed)'],
                  loc='upper right', fontsize=self.LEGEND_FS)

        ix = Om <= 1.5
        ins = self.ax3_inset; ins.cla(); ins.grid(True)
        ins.plot(Om[ix], Ta_th[ix],  ls='--', lw=1.2, color=[0,0.447,0.741])
        ins.plot(Om[ix], Ta_act[ix], ls='-',  lw=1.5, color=[0.12,0.53,0.22])
        ins.set_xlim(0, 1.2); ins.set_ylim(0.5, 1.2)
        ins.tick_params(labelsize=5)
        ins.set_facecolor([0.98,0.98,0.98])

    # ════════════════════════════════════════════════════════════════════════
    # 3-D geometry
    # ════════════════════════════════════════════════════════════════════════

    def _plot_geometry(self, a_target, h1, h_target, h2_target):
        import matplotlib.patches as mpatches
        ax = self.ax_geom; ax.cla()
        ax.set_facecolor([0.97, 0.97, 0.98])
        ax.grid(True, alpha=0.25, zorder=0)
        ax.tick_params(labelsize=self.TICK_FS)

        # ── layout parameters ────────────────────────────────────────────────
        pw   = self.a1;          ph  = self.h3
        ins  = self.h4;          sp_h = self.d_actual
        s_w  = self.column_thickness
        b_w  = self.base_w;      b_h  = self.base_h;   b_d  = self.base_d
        a_act = self.a_actual_edit.value()
        col_x = pw/2 + a_act

        # preview displacement: platform moves by dy in y
        dy = float(getattr(self, 'y_disp_edit', type('', (), {'value': lambda s: 0.0})()).value()
                   if hasattr(self, 'y_disp_edit') else 0.0)

        # ── key attachment points (x, y) ─────────────────────────────────────
        # Column anchors are FIXED (attached to rigid frame)
        LCT = np.array([-col_x,  sp_h]);  RCT = np.array([ col_x,  sp_h])
        LCM = np.array([-col_x,  0   ]);  RCM = np.array([ col_x,  0   ])
        LCB = np.array([-col_x, -sp_h]);  RCB = np.array([ col_x, -sp_h])
        # Platform attachment points move with the platform (+dy)
        PLT = np.array([-pw/2,  ins + dy]);  PRT = np.array([ pw/2,  ins + dy])
        PLM = np.array([-pw/2,  0   + dy]);  PRM = np.array([ pw/2,  0   + dy])
        PLB = np.array([-pw/2, -ins + dy]);  PRB = np.array([ pw/2, -ins + dy])
        plat_bot = np.array([0, -ph/2 + dy]);  base_top = np.array([0, b_d])

        col_top_y = sp_h * 1.35;   col_bot_y = b_d - b_h - 6

        # ── base & ground ─────────────────────────────────────────────────────
        ax.add_patch(mpatches.FancyBboxPatch(
            (-b_w/2, b_d - b_h), b_w, b_h,
            boxstyle='round,pad=1', fc=[0.78,0.78,0.78], ec=[0.2,0.2,0.2], lw=1.2, zorder=2))
        ground = mpatches.Rectangle(
            (-b_w/2, col_bot_y), b_w, 6,
            fc=[0.88,0.88,0.88], ec=[0.4,0.4,0.4], lw=0.7, hatch='////', zorder=1)
        ax.add_patch(ground)

        # ── columns ───────────────────────────────────────────────────────────
        for cx in [-col_x, col_x]:
            ax.add_patch(mpatches.FancyBboxPatch(
                (cx - s_w/2, col_bot_y), s_w, col_top_y - col_bot_y,
                boxstyle='round,pad=0.5',
                fc=[0.28,0.28,0.28], ec='k', lw=0.8, zorder=2))
            # column cap
            ax.add_patch(mpatches.FancyBboxPatch(
                (cx - s_w*0.7, col_top_y - 2), s_w*1.4, 4,
                boxstyle='round,pad=0.5', fc=[0.45,0.45,0.45], ec='k', lw=0.8, zorder=3))

        # ── equilibrium ghost (dashed) when displaced ─────────────────────────
        if abs(dy) > 0.5:
            ax.add_patch(mpatches.FancyBboxPatch(
                (-pw/2, -ph/2), pw, ph,
                boxstyle='round,pad=1.5',
                fc='none', ec=[0.6,0.6,0.6], lw=1, ls='--', zorder=2))

        # ── platform (displaced) ──────────────────────────────────────────────
        ax.add_patch(mpatches.FancyBboxPatch(
            (-pw/2, -ph/2 + dy), pw, ph,
            boxstyle='round,pad=1.5',
            fc=[0.82, 0.91, 1.0], ec=[0.1,0.3,0.8], lw=2, zorder=3))
        ax.text(0, dy, 'Platform\n(Payload)', ha='center', va='center',
                fontsize=7, fontweight='bold', color=[0.1,0.3,0.8], zorder=4)
        # displacement label on platform
        if abs(dy) > 0.5:
            ax.text(pw/2 + 3, -ph/2 + dy + ph/2,
                    f'y={dy:+.1f} mm', color=[0.1,0.3,0.8],
                    fontsize=6.5, va='center', fontweight='bold', zorder=5)

        # ── springs ───────────────────────────────────────────────────────────
        sc = [0.40, 0.42, 0.50]   # oblique spring colour
        bc = [0.55, 0.30, 0.10]   # bottom spring colour
        n_obl  = max(4, min(12, int(self.n_upper)))
        n_vert = max(4, min(12, int(self.n_bottom)))
        amp_o  = max(2.5, min(6, a_act * 0.07))
        amp_v  = max(3,   min(8, ph   * 0.18))

        for p1, p2, n in [
            (LCT,PLT,n_obl),(LCM,PLM,n_obl),(LCB,PLB,n_obl),
            (RCT,PRT,n_obl),(RCM,PRM,n_obl),(RCB,PRB,n_obl),
        ]:
            self._draw_spring_2d(ax, p1, p2, n, amp_o, sc)
        self._draw_spring_2d(ax, base_top, plat_bot, n_vert, amp_v, bc)

        # attachment dots
        for pt in [LCT,LCM,LCB,RCT,RCM,RCB,PLT,PLM,PLB,PRT,PRM,PRB,plat_bot,base_top]:
            ax.plot(*pt, 'o', color=[0.15,0.15,0.15], ms=3.5, zorder=5)

        # ── dimension callouts ────────────────────────────────────────────────
        orange=[0.85,0.33,0.1]; green=[0.12,0.53,0.22]; blue=[0.0,0.45,0.74]
        kw = dict(arrowstyle='<->', lw=1.3, mutation_scale=12)

        # h4: vertical offset of spring attachment
        ax.annotate('', xy=(col_x+8, ins), xytext=(col_x+8, 0),
                    arrowprops=dict(color=orange, **kw))
        ax.text(col_x+11, ins/2, f'h4={ins:.0f}', color=orange,
                fontsize=6.5, va='center', fontweight='bold')

        # a_actual: horizontal arm
        ax.annotate('', xy=(col_x, -sp_h-18), xytext=(pw/2, -sp_h-18),
                    arrowprops=dict(color=blue, **kw))
        ax.text((col_x+pw/2)/2, -sp_h-27, f'a={a_act:.0f} mm',
                color=blue, fontsize=6.5, ha='center', fontweight='bold')

        # d_actual: total spring height
        ax.annotate('', xy=(-col_x-12, sp_h), xytext=(-col_x-12, -sp_h),
                    arrowprops=dict(color=green, **kw))
        ax.text(-col_x-28, 0, f'd={sp_h:.0f}', color=green,
                fontsize=6.5, va='center', ha='center', fontweight='bold')

        # ── displacement indicator (double arrow, fixed to frame) ────────────
        disp_range = ins * 0.75
        x_disp = pw/2 + 18
        ax.annotate('', xy=(x_disp, disp_range), xytext=(x_disp, -disp_range),
                    arrowprops=dict(arrowstyle='<->', color='purple', lw=1.8,
                                   mutation_scale=14))
        ax.text(x_disp + 4, disp_range,  f'+{disp_range:.0f}',
                color='purple', fontsize=6.5, va='bottom')
        ax.text(x_disp + 4, -disp_range, f'−{disp_range:.0f}',
                color='purple', fontsize=6.5, va='top')
        ax.text(x_disp + 4, 0, 'Δy\n(mm)', color='purple',
                fontsize=6, va='center')
        # marker dot at current preview displacement
        if abs(dy) > 0.5:
            ax.plot(x_disp, dy, 'D', color='purple', ms=6, zorder=6)

        # ── force arrow at current displacement ───────────────────────────────
        f_cur = float(np.interp(dy, self.y_dim, self.f_actual_real))
        f_max = np.max(np.abs(self.f_actual_real)) or 1
        arrow_len = (f_cur / f_max) * ph * 0.85
        plat_ctr_y = dy   # platform centre at displaced position
        if abs(arrow_len) > 0.5:
            ax.annotate('', xy=(0, plat_ctr_y + arrow_len),
                        xytext=(0, plat_ctr_y),
                        arrowprops=dict(arrowstyle='->', color='red', lw=2.2,
                                       mutation_scale=14))
        ax.text(pw/2*0.55, plat_ctr_y + arrow_len * 0.6,
                f'F = {f_cur:.2f} N', color='red',
                fontsize=6.5, va='center', fontweight='bold', zorder=5)

        # ── secondary right y-axis → Force (N) ──────────────────────────────
        f_data = self.f_actual_real; y_data = self.y_dim
        def y_to_f(y):
            return np.interp(y, y_data, f_data,
                             left=float(f_data[0]), right=float(f_data[-1]))
        def f_to_y(f):
            idx = np.argsort(f_data)
            return np.interp(f, f_data[idx], y_data[idx])
        try:
            secax = ax.secondary_yaxis('right', functions=(y_to_f, f_to_y))
            secax.set_ylabel('Force F (N)', color=[0.85,0.33,0.10],
                             fontsize=self.LABEL_FS)
            secax.tick_params(colors=[0.85,0.33,0.10], labelsize=self.TICK_FS)
            # horizontal reference line at current force value
            ax.axhline(dy, color=[0.85,0.33,0.10], lw=0.8, ls=':', alpha=0.7)
        except Exception:
            pass   # secondary_yaxis unavailable in old matplotlib

        # ── axis limits & labels ─────────────────────────────────────────────
        xmax = col_x * 1.55
        ymax = max(sp_h, ph/2) * 1.6
        ymin = min(b_d - b_h - 10, -ymax)
        ax.set_xlim(-xmax, xmax)
        ax.set_ylim(ymin, max(col_top_y + 5, ymax))
        ax.set_xlabel('Horizontal position x (mm)', fontsize=self.LABEL_FS)
        ax.set_ylabel('Displacement y (mm)', fontsize=self.LABEL_FS)
        ax.set_title('QZS Assembly  [③ ④ ⑤]', fontsize=self.TITLE_FS,
                     fontweight='bold')

    def _draw_spring_2d(self, ax, p1, p2, n_coils, amplitude, color, lw=1.5):
        """Draw a coil spring between p1 and p2 as a sinusoidal curve."""
        p1 = np.asarray(p1, float); p2 = np.asarray(p2, float)
        diff = p2 - p1; L = np.linalg.norm(diff)
        if L < 1e-6: return
        ux = diff / L                        # unit along spring
        px = np.array([-ux[1], ux[0]])       # perpendicular unit

        n_pts = max(80, n_coils * 18)
        t = np.linspace(0, 1, n_pts)

        # straight end stubs (8 % each side) + sinusoidal coil body
        coil = (t >= 0.08) & (t <= 0.92)
        t_c  = (t[coil] - 0.08) / 0.84      # 0 → 1 over coil region
        wave = np.zeros(n_pts)
        wave[coil] = amplitude * np.sin(2 * np.pi * n_coils * t_c)

        pts = p1 + np.outer(t, diff) + np.outer(wave, px)
        ax.plot(pts[:,0], pts[:,1], color=color, lw=lw,
                solid_capstyle='round', zorder=4)

    # ════════════════════════════════════════════════════════════════════════
    # CSV vibration signals
    # ════════════════════════════════════════════════════════════════════════

    def _process_vibration_signals(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Vibration Input CSV',
            os.path.expanduser('~'), 'CSV (*.csv)')
        if not path:
            self.log_area.append('Cancelled.'); return

        path_ref, _ = QFileDialog.getOpenFileName(
            self, 'Select Reference CSV (cancel to skip)',
            os.path.expanduser('~'), 'CSV (*.csv)')

        try:
            def load_csv(p):
                df = pd.read_csv(p, skiprows=4, header=None,
                                 encoding='utf-8-sig', engine='python',
                                 on_bad_lines='skip')
                t = df.iloc[:, 0].to_numpy(dtype=float)
                v = df.iloc[:, 1].to_numpy(dtype=float)
                v = v - v.mean()
                return t, v, 1.0 / (t[1] - t[0])

            t_in, v_in, fs = load_csv(path)
            self._sig_t    = t_in
            self._sig_v_in = v_in
            self._sig_fs   = fs
            self.t_matrix  = t_in
            self.v_in_data = v_in
            self.fs_rate   = fs
            self.N_points  = len(v_in)
            self.log_area.append(
                f'Input: {len(v_in)} pts @ {fs:.1f} Hz  ({t_in[-1]:.1f} s)')

            self._sig_v_ref = self._sig_fs_ref = None
            if path_ref:
                _, v_ref, fs_ref = load_csv(path_ref)
                self._sig_v_ref  = v_ref
                self._sig_fs_ref = fs_ref
                self.log_area.append(
                    f'Ref:   {len(v_ref)} pts @ {fs_ref:.1f} Hz')

            self._update_psd_plots()
            self.canvas.draw()

        except Exception as e:
            import traceback
            self.log_area.append(f'Error: {e}\n{traceback.format_exc()}')

    def _update_psd_plots(self):
        """Recompute transmissibility & redraw ax4/ax5 from stored signal data."""
        if self._sig_v_in is None:
            return
        try:
            v_in = self._sig_v_in
            fs   = self._sig_fs
            t_in = self._sig_t
            N    = len(v_in)

            # ── system parameters from UI ────────────────────────────────────
            M_load = 2.0; g = 9.81
            a_t  = self.a_target_edit.value() / 1000   # m
            h1_t = self.test_params[1]        / 1000   # m
            k2_Nm  = (M_load*g) / (1.229*np.sqrt(a_t**2 + h1_t**2))
            omega0 = np.sqrt(k2_Nm / M_load)
            f0_sys = omega0 / (2*np.pi)
            zeta   = self.C_edit.value() * omega0 / (2*k2_Nm)
            Ze_hat = self.Ze_edit.value()/1000 / np.sqrt(a_t**2 + h1_t**2)

            # ── mu1, mu3 from current left-panel params ──────────────────────
            dh = self.delta_hat_edit.value(); ah = self.a_hat_edit.value()
            al = self.alpha_edit.value();     al1= self.alpha1_edit.value()
            gm = self.gamma_edit.value()
            if abs(gm - 1) < 1e-9 or ah <= 0 or ah >= 1:
                return
            rho = (1 - ah**2) / (gm - 1)**2
            mu1 = (1 + 4*al + 2*al1
                   - 2*(1+dh)*(2*al*ah**2/(np.sqrt(rho+ah**2))**3 + al1/ah))
            mu3 = (-2*(1+dh)*(
                2*al*(12*ah**2*rho - 3*ah**4)/((np.sqrt(rho+ah**2))**7)
                + al1*(-3)/ah**3)) / 6

            # ── Welch PSD for input ──────────────────────────────────────────
            win_s = int(min(N, max(256, fs)))
            nfft  = int(2**np.ceil(np.log2(win_s)))
            f_psd, pxx_in = welch(v_in, fs=fs, window='hann',
                                   nperseg=win_s, nfft=nfft)

            # ── ASD_out = ASD_in × Ta(f) ─────────────────────────────────────
            Ta      = self._transmissibility_vec(mu1, mu3, f_psd, f0_sys, Ze_hat, zeta)
            asd_in  = np.sqrt(pxx_in)
            asd_out = asd_in * Ta

            # ── FFT filter → time-domain output ─────────────────────────────
            freq_rfft = np.fft.rfftfreq(N, d=1/fs)
            Ta_full   = self._transmissibility_vec(mu1, mu3, freq_rfft,
                                                   f0_sys, Ze_hat, zeta)
            v_out = np.fft.irfft(np.fft.rfft(v_in) * Ta_full, n=N)
            self.v_out_data = v_out

            # ── reference ASD ─────────────────────────────────────────────────
            asd_ref = None
            if self._sig_v_ref is not None:
                v_ref = self._sig_v_ref; fs_ref = self._sig_fs_ref
                win_r  = int(min(len(v_ref), max(256, fs_ref)))
                nfft_r = int(2**np.ceil(np.log2(win_r)))
                f_ref, pxx_ref = welch(v_ref, fs=fs_ref, window='hann',
                                        nperseg=win_r, nfft=nfft_r)
                asd_ref = np.interp(f_psd, f_ref, np.sqrt(pxx_ref), left=0, right=0)

            # ── time-domain plot ─────────────────────────────────────────────
            T_SHOW = min(2.0, t_in[-1])
            idx = t_in <= T_SHOW
            ax4 = self.ax4; ax4.cla(); ax4.grid(True)
            ax4.plot(t_in[idx], v_in[idx],  color=[0.5,0.5,0.5], lw=0.8,
                     label='Input Signal')
            ax4.plot(t_in[idx], v_out[idx], color=[0,0.447,0.741], lw=1.2,
                     label='Group1 Output')
            ax4.set_title('Time Domain  [① ⑥ — load CSV]',
                          fontsize=self.TITLE_FS, fontweight='bold')
            ax4.set_xlabel('Time (s)', fontsize=self.LABEL_FS)
            ax4.set_ylabel('Voltage (V)', fontsize=self.LABEL_FS)
            ax4.legend(loc='upper right', fontsize=self.LEGEND_FS)
            ax4.tick_params(labelsize=self.TICK_FS)

            # ── PSD log-log plot ──────────────────────────────────────────────
            ax5 = self.ax5; ax5.cla()
            ax5.grid(True, which='both', ls='--', alpha=0.45)
            eps   = np.finfo(float).tiny
            f_pos = f_psd[f_psd > 0]
            lbl2  = (f'δ̂={dh:.3f}  â={ah:.3f}  γ={gm:.3f}  '
                     f'α={al:.3f}  α₁={al1:.3f}')

            ax5.loglog(f_pos, np.maximum(asd_in[f_psd>0],  eps),
                       '--', color=[0.5,0.5,0.5], lw=2.5, label='Input Signal')
            ax5.loglog(f_pos, np.maximum(asd_out[f_psd>0], eps),
                       color=[0,0.447,0.741], lw=2.0, label=lbl2)
            if asd_ref is not None:
                ax5.loglog(f_pos, np.maximum(asd_ref[f_psd>0], eps),
                           'k-', lw=2.5, label='Reference Curve')

            ax5.set_title('PSD Comparison  [① ⑥ — load CSV]',
                          fontsize=self.TITLE_FS, fontweight='bold')
            ax5.set_xlabel('Frequency (Hz)', fontsize=self.LABEL_FS)
            ax5.set_ylabel(r'PSD $[V/\sqrt{Hz}]$', fontsize=self.LABEL_FS)
            ax5.set_xlim(max(f_pos[0], 0.5), min(fs/2, 500))
            ax5.legend(loc='upper right', fontsize=self.LEGEND_FS)
            ax5.tick_params(labelsize=self.TICK_FS, which='both')

        except Exception as e:
            import traceback
            self.log_area.append(f'PSD update error: {e}\n{traceback.format_exc()}')

    # ════════════════════════════════════════════════════════════════════════
    # Spring design → Excel
    # ════════════════════════════════════════════════════════════════════════

    def _save_design_data(self):
        dh = self.delta_hat_edit.value(); ah = self.a_hat_edit.value()
        al = self.alpha_edit.value(); al1 = self.alpha1_edit.value()
        gm = self.gamma_edit.value(); at = self.a_target_edit.value()
        tau_p = self.tau_p_edit.value(); G = self.G_edit.value()
        M = M1 = M2 = 2; g = 9.81

        h1  = np.sqrt(max(0, at**2*(1/ah**2 - 1)))
        dlt = dh * np.sqrt(at**2 + h1**2)
        L1  = np.sqrt(at**2 + h1**2) + dlt
        d_p = h1 / (gm - 1)
        ht  = h1 + d_p; h2t = h1 + 2*d_p
        rho = (1 - ah**2) / (gm-1)**2
        dh1 = 1 - np.sqrt(1+2*np.sqrt(1-ah**2)*np.sqrt(rho)+rho)   + dh
        dh2 = 1 - np.sqrt(1+4*np.sqrt(1-ah**2)*np.sqrt(rho)+4*rho) + dh
        d1  = dh1 * np.sqrt(at**2 + h1**2)
        d2  = dh2 * np.sqrt(at**2 + h1**2)
        L2  = np.sqrt(at**2 + ht**2)  + d1
        L3  = np.sqrt(at**2 + h2t**2) + d2

        k2 = (M*g) / (1.229*np.sqrt((at/1000)**2+(h1/1000)**2))
        k1 = k2*al; k3 = al1*k2
        f1 = -(k1/1000)*dlt*(h1/np.sqrt(at**2+h1**2))
        f3 = -(k3/1000)*d1*(ht/np.sqrt(at**2+ht**2))
        f4 = -(k1/1000)*d2*(h2t/np.sqrt(at**2+h2t**2))
        f2 = -(2*f1+2*f3+2*f4)
        Lv = h2t + f2/(k2/1000)

        d_eq  = L1 - np.sqrt(at**2 + d_p**2)
        d1_eq = L2 - at
        d3_eq = (M*g)/(k2/1000)

        Cs = range(5, 13); ratios = np.arange(0.28, 0.51, 0.01)
        cols = ['d_target_mm','d_mm','D_mm','D_out_mm','C','n','ratio','p_mm','G_Mpa','L_mm','k_actual_N_m']

        def spring_table(k_t, L_t, Ms):
            rows = []
            for C in Cs:
                for r in ratios:
                    ac = (G*r)/(8*C**4*(k_t/1000))
                    disc = 4/C**2 + 4*ac*L_t
                    if disc < 0: continue
                    Dv = (-2/C + np.sqrt(disc))/(2*ac)
                    dv = Dv/C; Do = Dv+dv
                    Kf = (4*C-1)/(4*C-4)+0.615/C
                    nv = (G*Dv)/(8*C**4*(k_t/1000))
                    ka = (G*Dv)/(8*C**4*nv) if nv else 0
                    dt = 1.6*np.sqrt(Kf*C*Ms*g/tau_p)
                    rows.append([dt,dv,Dv,Do,C,nv,r,r*Dv,G,L_t,ka*1000])
            df = pd.DataFrame(rows, columns=cols)
            return df.drop_duplicates(['C','ratio'])

        k2_df = spring_table(k2, Lv, M)
        k1_df = spring_table(k1, L1, M1)
        k3_df = spring_table(k3, L2, M2)

        out = os.path.join(os.path.expanduser('~'), 'Spring_Parameters.xlsx')
        try:
            with pd.ExcelWriter(out, engine='openpyxl') as w:
                k2_df.to_excel(w, sheet_name='K2_Spring',      index=False)
                k1_df.to_excel(w, sheet_name='Up_Down_Spring',  index=False)
                k3_df.to_excel(w, sheet_name='Middle_Spring',   index=False)
            self.log_area.setPlainText('\n'.join([
                f'Excel saved: {out}',
                '--- Geometry ---',
                f'd:  {d_p:.1f} mm',  f'h:  {ht:.1f} mm',
                f'h1: {h1:.1f} mm',   f'h2: {h2t:.1f} mm',
                '--- Precompression ---',
                f'delta:  {dlt:.1f} mm', f'delta2: {d1:.1f} mm', f'delta3: {d2:.1f} mm',
                '--- Equilibrium compression ---',
                f'delta_eq:  {d_eq:.1f} mm',
                f'delta1_eq: {d1_eq:.1f} mm',
                f'delta3_eq: {d3_eq:.1f} mm',
                '--- Target stiffness ---',
                f'k1: {k1:.1f} N/m', f'k2: {k2:.1f} N/m', f'k3: {k3:.1f} N/m',
                '--- Free lengths ---',
                f'L1: {L1:.1f} mm', f'L2: {L2:.1f} mm',
                f'L3: {L3:.1f} mm', f'L:  {Lv:.1f} mm',
            ]))
        except Exception as e:
            self.log_area.append(f'Excel Write Error: {e}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QZSApp()
    win.show()
    sys.exit(app.exec_())
