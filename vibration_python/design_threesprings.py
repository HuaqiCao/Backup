#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
淘宝拉伸弹簧批量筛选 v14 长期悬挂版
重点修复：
- 同一图片多次OCR投票，不再直接拼接错误结果
- 支持 1.5-12-120 / 1.5x12x120 / 1.5×12×120
- 修正常见OCR漏小数点：15->1.5, 18->1.8, 25->2.5
- 支持双横线：1.8-15--80
"""

from __future__ import annotations
import csv, math, re, shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple, Iterable

# 系统参数
N = 3
MASS_KG = 90.0
G0 = 9.80665
DYNAMIC_FACTOR = 1.25

# 长期静载筛选降额
# 不是材料标准常数；用于淘宝材料状态未知时保守筛选
LONG_TERM_DERATE = 0.80

# 常温默认1.0；高温时应按材料数据重新设定
TEMPERATURE_FACTOR = 1.00

# 几何估算
HOOK_AXIAL_FACTOR = 1.0
COIL_ERR = 1.0
N_MIN = 3.0
C_MIN, C_MAX = 4.0, 20.0

# 当前淘宝小型拉簧目录的线径上限
# 用于修复OCR漏小数点，例如15应为1.5
WIRE_D_MAX = 8.0

# 至少两个OCR模式识别一致才接受
MIN_OCR_VOTES = 2

MAT = {
    "304": {
        "name": "304不锈钢",
        "Gmin": 70.0, "Gnom": 73.5, "Gmax": 77.0,
        "rho": 7930.0,
        "tau_allow": 350.0,
    },
    "spring_steel": {
        "name": "弹簧钢",
        "Gmin": 78.0, "Gnom": 80.0, "Gmax": 82.0,
        "rho": 7850.0,
        "tau_allow": 550.0,
    },
}

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

@dataclass
class Result:
    image: str
    material: str
    spec: str
    d_mm: float
    OD_mm: float
    L0_mm: float
    D_mm: float
    C: float
    n_nom: float
    k_nom_N_mm: float
    k_min_N_mm: float
    k_max_N_mm: float
    L_nom_mm: float
    L_worst_mm: float
    fn_nom_Hz: float
    fn_min_Hz: float
    fn_max_Hz: float
    tau_normal_MPa: float
    tau_emergency_MPa: float
    tau_allow_MPa: float
    SF_normal: float
    SF_1fail: float
    SF_longterm: float
    max_mass_3spring_kg: float
    max_mass_longterm_kg: float
    tau_allow_longterm_MPa: float
    status: str
    reason: str
    score: float

def choose_folder() -> Optional[Path]:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    p = filedialog.askdirectory(title="选择包含淘宝弹簧截图的文件夹")
    root.destroy()
    return Path(p).resolve() if p else None

def setup_tesseract() -> bool:
    try:
        import pytesseract
    except ImportError:
        print("Missing pytesseract. Run: pip install pytesseract pillow")
        return False

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    exe = next((p for p in candidates if p.exists()), None)

    if exe is None:
        x = shutil.which("tesseract")
        exe = Path(x) if x else None

    if exe is None:
        print("Tesseract not found.")
        return False

    pytesseract.pytesseract.tesseract_cmd = str(exe)
    return True

def preprocess(path: Path):
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    img = Image.open(path).convert("RGB")
    img = img.resize(
        (int(img.width * 3.0), int(img.height * 3.0)),
        Image.Resampling.LANCZOS
    )
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return img.filter(ImageFilter.SHARPEN)

# 分开执行OCR，供后续投票
def ocr_passes(path: Path) -> List[Tuple[str, str]]:
    import pytesseract
    img = preprocess(path)
    out = []

    # PSM 6适合整体表格，11/12适合稀疏文本
    for psm in (6, 11, 12):
        for lang in ("chi_sim+eng", "eng"):
            try:
                text = pytesseract.image_to_string(
                    img, lang=lang, config=f"--psm {psm}"
                )
                if text.strip():
                    out.append((f"{lang}_psm{psm}", text))
            except Exception:
                pass

    return out

def materials(text: str) -> List[str]:
    low = text.lower()
    out = []

    if "304" in low or "sus304" in low or "不锈钢" in text:
        out.append("304")

    if (
        "65mn" in low or "60si2mn" in low or
        "弹簧钢" in text or "锰钢" in text or "高碳钢" in text
    ):
        out.append("spring_steel")

    return list(dict.fromkeys(out)) or ["304", "spring_steel"]

def normalize_text(text: str) -> str:
    table = {
        "×": "-", "X": "-", "x": "-", "✕": "-", "*": "-", "＊": "-",
        "－": "-", "–": "-", "—": "-", "−": "-",
        "Φ": "", "φ": "", "Ø": "",
        "，": ",", "：": ":",
    }
    for a, b in table.items():
        text = text.replace(a, b)

    # 连续横线合并
    text = re.sub(r"-{2,}", "-", text)
    return text

def repair_wire_diameter(d: float) -> float:
    """
    修复常见OCR漏小数点。
    当前目录线径主要<=8 mm。
    例：15->1.5, 18->1.8, 25->2.5
    """
    if d <= WIRE_D_MAX:
        return d

    # 尝试除10
    d2 = d / 10.0
    if 0.3 <= d2 <= WIRE_D_MAX:
        return d2

    return d

def plausible(d: float, od: float, L0: float) -> bool:
    return (
        0.3 <= d <= WIRE_D_MAX
        and od > d
        and od <= 300
        and L0 > od
        and L0 <= 3000
    )

# 单次OCR文本提取规格
def specs_one_pass(text: str) -> List[Tuple[float, float, float]]:
    text = normalize_text(text)
    out = []

    # 标准三段式
    pat = re.compile(
        r"(?<![\d.])"
        r"(\d+(?:\.\d+)?)\s*-\s*"
        r"(\d+(?:\.\d+)?)\s*-\s*"
        r"(\d+(?:\.\d+)?)"
        r"(?![\d.])"
    )

    for m in pat.finditer(text):
        d, od, L0 = map(float, m.groups())
        d = repair_wire_diameter(d)

        if plausible(d, od, L0):
            out.append((
                round(d, 3),
                round(od, 3),
                round(L0, 3)
            ))

    return list(dict.fromkeys(out))

# 多OCR结果投票
def voted_specs(passes: List[Tuple[str, str]]):
    votes = Counter()
    sources = defaultdict(list)

    for pass_name, text in passes:
        found = set(specs_one_pass(text))
        for spec in found:
            votes[spec] += 1
            sources[spec].append(pass_name)

    accepted = []
    rejected = []

    for spec, count in votes.items():
        if count >= MIN_OCR_VOTES:
            accepted.append((spec, count, sources[spec]))
        else:
            rejected.append((spec, count, sources[spec]))

    accepted.sort(key=lambda x: x[0])
    rejected.sort(key=lambda x: x[0])

    return accepted, rejected

def wahl(C: float) -> float:
    if C <= 1:
        return float("inf")
    return (4*C - 1)/(4*C - 4) + 0.615/C

def rate(G_GPa: float, d: float, D: float, n: float) -> float:
    return G_GPa * 1000 * d**4 / (8 * D**3 * n)

def shear(F: float, d: float, D: float) -> float:
    if d <= 0 or D <= 0:
        return float("inf")

    C = D / d
    if C <= 1:
        return float("inf")

    Kw = wahl(C)
    return Kw * 8 * F * D / (math.pi * d**3)

def coil_count(d: float, OD: float, L0: float):
    n = (L0 - 2 * HOOK_AXIAL_FACTOR * OD) / d
    return n, n + COIL_ERR, n - COIL_ERR

def spring_mass(mat: str, d: float, OD: float, D: float, n: float) -> float:
    rho = MAT[mat]["rho"]
    A = math.pi * (d/1000)**2 / 4
    wire = math.pi * (D/1000) * n + 2 * math.pi * (OD/1000)
    return rho * A * wire

def natural_frequency(k: float, ms: float) -> float:
    K = N * k * 1000
    m_eff = MASS_KG + N * ms / 3
    return (1/(2*math.pi)) * math.sqrt(K/m_eff)

def analyze(image: Path, mat: str, d: float, OD: float, L0: float) -> Result:
    p = MAT[mat]
    D = OD - d
    C = D / d

    F_total = MASS_KG * G0
    F_normal = F_total / N
    F_emergency = F_total / (N - 1) * DYNAMIC_FACTOR

    n, nsoft, nstiff = coil_count(d, OD, L0)

    geometry_ok = (
        D > 0
        and C_MIN <= C <= C_MAX
        and nstiff >= N_MIN
    )

    nc = max(n, N_MIN)
    nso = max(nsoft, N_MIN)
    nst = max(nstiff, N_MIN)

    k = rate(p["Gnom"], d, D, nc)
    kmin = rate(p["Gmin"], d, D, nso)
    kmax = rate(p["Gmax"], d, D, nst)

    # Fi未知，取0为偏保守长度
    L = L0 + F_normal / k
    Lworst = L0 + F_normal / kmin

    tauN = shear(F_normal, d, D)
    tauE = shear(F_emergency, d, D)

    # 两种主体筛选安全系数
    if not math.isfinite(tauN) or tauN <= 0:
        SF_normal = 0.0
    else:
        SF_normal = p["tau_allow"] / tauN

    if not math.isfinite(tauE) or tauE <= 0:
        SF_1fail = 0.0
    else:
        SF_1fail = p["tau_allow"] / tauE

    # 三根都完好时的最大静态总质量
    max_mass_3spring_kg = MASS_KG * SF_normal

    # 长期静载许用剪应力：对当前筛选许用值再降额
    tau_allow_longterm = (
        p["tau_allow"] * LONG_TERM_DERATE * TEMPERATURE_FACTOR
    )

    # 长期静载筛选安全系数
    if not math.isfinite(tauN) or tauN <= 0:
        SF_longterm = 0.0
    else:
        SF_longterm = tau_allow_longterm / tauN

    # 三根都完好、长期悬挂时的筛选最大总质量
    max_mass_longterm_kg = MASS_KG * SF_longterm

    ms = spring_mass(mat, d, OD, D, nc)
    fn = natural_frequency(k, ms)
    fnmin = natural_frequency(kmin, ms)
    fnmax = natural_frequency(kmax, ms)

    if not geometry_ok:
        status = "REJECT"
        reason = f"geometry C={C:.2f}, n={n:.2f}"
    elif SF_longterm < 1.0:
        status = "REJECT"
        reason = "long-term static body stress"
    elif SF_1fail < 1.0:
        status = "MARGINAL"
        reason = "long-term static passes, but one-spring-fail case does not"
    else:
        status = "PASS"
        reason = "long-term static and one-spring-fail body screening passed; hook strength unknown"

    status_penalty = 0
    if status == "MARGINAL":
        status_penalty = 50
    elif status == "REJECT":
        status_penalty = 100

    score = (
        status_penalty + fn
        - 0.10 * min(SF_longterm, 3)
        - 0.05 * min(SF_1fail, 3)
    )

    return Result(
        str(image), p["name"], f"{d:g}x{OD:g}x{L0:g}",
        d, OD, L0, D, C, n,
        k, kmin, kmax,
        L, Lworst,
        fn, fnmin, fnmax,
        tauN, tauE, p["tau_allow"],
        SF_normal, SF_1fail, SF_longterm,
        max_mass_3spring_kg, max_mass_longterm_kg,
        tau_allow_longterm,
        status, reason, score
    )

def images(folder: Path) -> Iterable[Path]:
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXT:
            # 避免重复读输出文件夹
            if "spring_analysis_output" not in p.parts:
                yield p

def save_csv(path: Path, rows: List[Result]):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=asdict(rows[0]).keys())
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

def main():
    folder = choose_folder()
    if not folder:
        print("No folder selected.")
        return

    if not setup_tesseract():
        return

    out = folder / "spring_analysis_output"
    out.mkdir(exist_ok=True)

    imgs = list(images(folder))
    rows = []
    ocr_log = []

    print(f"\nSelected folder: {folder}")
    print(f"Found {len(imgs)} image(s)\n")

    for idx, img in enumerate(imgs, 1):
        print(f"[{idx}/{len(imgs)}] Processing: {img.name}")

        passes = ocr_passes(img)

        # 记录每次OCR原文
        for pass_name, text in passes:
            ocr_log += [
                "=" * 100,
                f"IMAGE: {img}",
                f"PASS: {pass_name}",
                text,
                ""
            ]

        accepted, rejected = voted_specs(passes)

        all_text = "\n".join(text for _, text in passes)
        found_mats = materials(all_text)

        print(f"  OCR passes: {len(passes)}")
        print(f"  Accepted specs: {len(accepted)}")
        print(f"  Materials: {', '.join(found_mats)}")

        for (d, OD, L0), votes, srcs in accepted:
            print(
                f"    {d:g}x{OD:g}x{L0:g} "
                f"[votes={votes}]"
            )

            for mat in found_mats:
                try:
                    rows.append(analyze(img, mat, d, OD, L0))
                except Exception as e:
                    print(
                        f"      Skip calculation: "
                        f"{type(e).__name__}: {e}"
                    )

        # 把低票候选写进日志，便于人工核对
        if rejected:
            ocr_log += [
                "-" * 80,
                f"LOW-VOTE CANDIDATES: {img}",
            ]
            for spec, votes, srcs in rejected:
                ocr_log.append(
                    f"{spec} votes={votes} sources={srcs}"
                )
            ocr_log.append("")

    rows.sort(key=lambda r: r.score)

    save_csv(out / "spring_results_ranked.csv", rows)
    (out / "ocr_raw_text.txt").write_text(
        "\n".join(ocr_log),
        encoding="utf-8"
    )

    print(f"\nFound {len(rows)} candidate row(s)\n")

    for i, r in enumerate(rows, 1):
        print(
            f"{i:02d}. {r.material} {r.spec} | {r.status} | "
            f"C={r.C:.2f} | "
            f"L={r.L_nom_mm:.1f} mm | "
            f"fn={r.fn_nom_Hz:.2f} Hz | "
            f"SF={r.SF_normal:.2f} | "
            f"SFLong={r.SF_longterm:.2f} | "
            f"SF1Fail={r.SF_1fail:.2f} | "
            f"Mmax={r.max_mass_3spring_kg:.1f} kg | "
            f"MmaxLong={r.max_mass_longterm_kg:.1f} kg"
        )

    print(f"\nCSV: {out / 'spring_results_ranked.csv'}")
    print(f"OCR log: {out / 'ocr_raw_text.txt'}")
    print("Only specifications confirmed by multiple OCR passes are calculated.")
    print("SF = normal static body-stress screening factor at 90 kg.")
    print("SFLong = long-term static screening factor after long-term derating.")
    print("SF1Fail = screening factor after one spring fails, including dynamic factor.")
    print("Mmax = static screening mass for 3 intact springs.")
    print("MmaxLong = long-term static screening mass for 3 intact springs.")
    print("Long-term derating is a conservative screening assumption, not a material standard.")
    print("Hook/root strength, initial tension, stress relaxation and certified material strength remain unknown.")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
