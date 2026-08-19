"""Pulse-tube research expansion + stable Zotero analysis pipeline.

v21 extends the stable v20 resume/write-repair foundation into a focused
engineering literature expansion for pulse-tube dry dilution refrigerators.
The expansion searches pulse-tube operating principles, pressure/mass-flow
phase physics, vibration generation, rotary-valve/cold-head mechanisms,
transfer paths, cryogenic isolation and transferable precision-isolation
methods. Three useful method classes are added: pulse-tube phase cancellation,
exchange-gas/non-contact thermal coupling, and cable/microphonic control.

The old library is repaired before expansion. Existing valid 深度分析 notes are
never re-run merely because the search taxonomy grew. Focused discovery is
run once per expansion ID, imports metadata/abstracts without downloading PDFs,
and analyzes only genuinely new or invalid items. The deep prompt now turns
papers into source/path/receiver engineering decisions and distinguishes
paper evidence from generic theory. After a valid library is obtained, one
cached cross-paper synthesis can create pulse_tube_isolation_design_guide.html.

Safety from v20 remains: progress is loaded before use, paid Analysis is reused,
cached-write failures stop before AI, child notes use explicit parentItem,
there are zero runtime zot.item_template()/GET /items/new calls, ordinary user
tags/unrelated Collections are preserved, and the final Zotero note contract
remains authoritative.
"""
import os
import re
import sys
import json
import time
import html
import math
import hashlib
import base64
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd
import requests
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel


# ============================================================
# 1. 用户配置
# ============================================================

# AI
AI_API_KEY = "sk-azx-cdx-Fnq68AxCOVskeBo7ohPl_g.aFoXwOwsandOGNIG4WuL85v8RO2HaVCHi_Livz0_asA"
AI_PRIMARY_BASE_URL = "https://ca.memofun.net/v1"
AI_BACKUP_BASE_URL = "https://codex-api.aizex.net/v1"
AI_BASE_URLS = [AI_PRIMARY_BASE_URL, AI_BACKUP_BASE_URL]
AI_MODEL_OVERRIDE = ""

# Zotero
ZOTERO_API_KEY = "Vv2P2zqSbOh326qpi84q35rW"
ZOTERO_LIBRARY_ID = "17163770"
ZOTERO_LIBRARY_TYPE = "user"

# Whole library mode
# True = scan the entire Zotero library; no Collection setting required
WHOLE_LIBRARY = True

# New English classification tree created at Zotero library root
CLASSIFICATION_ROOT_NAME = ""

# Existing user Collections are never deleted or moved
PRESERVE_EXISTING_COLLECTIONS = True

# Clean rebuild
# WARNING: removes ALL existing tags from paper items before retagging
RESET_ALL_PAPER_TAGS = True

# Remove EVERY existing Zotero Collection before rebuilding.
# Items and PDF attachments remain in My Library.
DELETE_ALL_COLLECTIONS_BEFORE_REBUILD = True

# Clear this script's local output folder before a fresh run
RESET_LOCAL_OUTPUT = True

# Smart organization detection
SMART_ORGANIZATION_CHECK = True
FORCE_REBUILD_LIBRARY = False
ORGANIZED_MIN_RATIO = 0.80

# Once organization is already complete, go straight to deep analysis
RUN_DISCOVERY_IF_ALREADY_ORGANIZED = False
# On a fresh rebuild, discovery still runs after classification
RUN_DISCOVERY_AFTER_REBUILD = False
# Math output
RENDER_ZOTERO_MATH = True
WRITE_RENDERED_HTML = True
WRITE_MARKDOWN = False
WRITE_EXCEL = False
OUTPUT_LANGUAGE = "zh-CN"

# Institution PDF fallback:
# do not store university credentials; reuse PDFs downloaded through
# an already authenticated school browser session.
USE_INSTITUTION_PDF_DIR = True
INSTITUTION_PDF_DIR = "~/Downloads"
INSTITUTION_PDF_LOOKBACK_DAYS = 30

# Automatic duplicate cleanup
AUTO_DELETE_DUPLICATES = True
DUPLICATE_TITLE_MIN_CHARS = 18
MOVE_DUPLICATE_CHILDREN = True
VERIFY_DUPLICATE_DELETE = True

DUPLICATE_DELETE_RETRIES = 4
DUPLICATE_WRITE_RETRIES = 4
DUPLICATE_RETRY_WAIT = 0.5

# Zotero may return response-only attachment fields that Pyzotero will not
# accept on PATCH. These are removed before duplicate child moves.
NONWRITABLE_ITEM_DATA_KEYS = {
    "lastRead",
}

# Repair only missing/incomplete organization; never reclassify the whole
# library when the existing organization is already usable.
REPAIR_INCOMPLETE_ORGANIZATION = True

# Terminal UI
SHOW_CURRENT_PAPER = True
CURRENT_TITLE_MAX_CHARS = 72

# Per-paper child structure
STANDARDIZE_OLD_AI_NOTES = True
CREATE_MISSING_AI_SUMMARY = True
ENSURE_PDF_CHILD = False
# Old generated note titles recognized as already analyzed
LEGACY_DEEP_NOTE_TITLES = (
    "AI总结",
    "AI 总结",
    "AI深度分析",
    "AI 深度分析",
    "AI Review | Cryogenic Vibration",
    "AI Deep Analysis",
)

LEGACY_SUMMARY_NOTE_TITLES = (
    "摘要",
    "AI摘要",
    "AI 摘要",
    "AI Summary",
)

# Verify actual Zotero Collection membership after classification
VERIFY_COLLECTION_WRITES = True

# Keep bibliography items, PDFs and ordinary Zotero notes
DELETE_PAPERS_OR_PDFS = False

# Zotero 本地 storage；留空自动尝试 ~/Zotero/storage
ZOTERO_LOCAL_STORAGE_DIR = ""

# ------------------------------------------------------------
# 自动扩展文献
# ------------------------------------------------------------

AUTO_DISCOVER_RELATED = True

# OpenAlex：建议申请免费 key；留空也可少量使用
OPENALEX_API_KEY = ""

# Unpaywall 要求 email；建议填写真实邮箱
UNPAYWALL_EMAIL = "your_email@example.com"

# 从已有论文扩展
DISCOVER_FROM_REFERENCES = True
DISCOVER_FROM_RELATED = True
DISCOVER_FROM_CITING = True

# 网络主题搜索
DISCOVER_FROM_TOPIC_SEARCH = True

DOMAIN_SEARCH_QUERIES = [
    # ---- Pulse-tube working principle / thermoacoustics ----
    '"pulse tube refrigerator" operating principle regenerator phase shift',
    '"pulse tube cryocooler" pressure oscillation mass flow phase',
    '"pulse tube refrigerator" inertance tube reservoir regenerator',
    '"pulse tube" acoustic impedance pressure flow phase cryocooler',
    '"orifice pulse tube refrigerator" phase shift cooling principle',

    # ---- How the pulse tube generates vibration ----
    '"vibration generation in a pulse tube refrigerator"',
    '"pulse tube cryocooler" vibration source pressure force cold stage',
    '"pulse tube cryocooler" vibration spectrum cold head',
    '"vibration spectrum of a pulse-tube cryostat" 1 Hz 20 kHz',
    '"pulse tube" rotary valve vibration cryocooler',
    '"pulse tube" pressure oscillation mechanical vibration cold head',
    '"pulse tube" 1.4 Hz harmonics dilution refrigerator',

    # ---- Transfer paths in dry dilution refrigerators ----
    '"pulse tube" vibration transfer path cryostat',
    '"pulse tube" 300 K flange vibration mixing chamber',
    '"pulse tube" cold stage thermal link vibration cryostat',
    '"dry dilution refrigerator" vibration transmission mixing chamber',
    '"pulse tube" cable microphonics dilution refrigerator',
    '"vibration-induced electrical noise" cryogen-free dilution refrigerator',
    '"thermal strap" copper braid vibration cryogenic',
    '"flexible bellows" pulse tube cryostat vibration',
    '"remote motor" pulse tube dilution refrigerator vibration',

    # ---- Directly relevant cryogenic isolation architectures ----
    '"Decoupling Pulse Tube Vibrations from a Dry Dilution Refrigerator at milli-Kelvin Temperatures"',
    '"Vibrations on pulse tube based Dry Dilution Refrigerators for low noise measurements"',
    '"A simple and efficient passive vibration isolation system" cryostat',
    '"Closed-cycle, low-vibration 4 K cryostat" pulse tube',
    '"Atomic resolution STM in a cryogen free dilution refrigerator at 15 mK"',
    '"ultra-low vibration cryostat" pulse tube split design',
    '"pulse tube cryocooler with self-cancellation of cold stage vibration"',
    '"active noise cancellation" CUORE pulse tube cryocoolers',
    '"pulse tube" phase cancellation cryocooler vibration',
    '"exchange gas" vibration isolation cryostat pulse tube',
    '"non-contact heat exchanger" vibration isolation cryostat',
    '"cryogenic torsion balance" pulse tube vibration isolation',

    # ---- Detector / low-noise consequences ----
    '"cryogenic detector" pulse tube vibration isolation',
    '"bolometer" pulse tube vibration microphonics',
    '"neutrinoless double beta decay" pulse tube vibration',
    '"mixing chamber" vibration pulse tube',
    '"cryogenic cable" vibration microphonics pulse tube',
]

# Focused Pulse-Tube research expansion
PULSE_TUBE_EXPANSION_ENABLED = True
PULSE_TUBE_EXPANSION_ID = "pt-principle-vibration-isolation-v21"
PULSE_TUBE_EXPANSION_RUN_ONCE = True
FORCE_PULSE_TUBE_EXPANSION = False

# The user will manage PDFs manually. Discovery imports metadata/abstracts only.
DISCOVERY_DOWNLOAD_PDFS = False

# One cross-paper strong-model synthesis after the library is valid.
GENERATE_PULSE_TUBE_DESIGN_GUIDE = True
FORCE_REGENERATE_DESIGN_GUIDE = False
DESIGN_GUIDE_MAX_PAPERS = 18
DESIGN_GUIDE_CHARS_PER_PAPER = 2400
DESIGN_GUIDE_MAX_OUTPUT_TOKENS = 10000

# 每种措施主动补充文献；允许非低温应用
DISCOVER_GENERIC_ISOLATION_METHODS = True
MAX_METHOD_PAPERS_PER_MEASURE = 2
EXTRA_METHOD_PAPERS_FOR_LIBRARY_MATCH = 1
METHOD_SEARCH_RESULTS_PER_QUERY = 15
MAX_TOTAL_NEW_PAPERS = 36
# 内容分类：AI + 规则兜底
USE_AI_CONTENT_CLASSIFIER = True
CLASSIFY_BATCH_SIZE = 12
CLASSIFY_TEXT_CHARS = 3200

# Fast classification
FAST_CLASSIFICATION = True
FAST_CLASSIFY_USE_FULLTEXT = False
FAST_AI_MODEL_OVERRIDE = ""
FAST_AI_TIMEOUT = 90
FAST_RULE_ONLY_IF_CLEAR = True

# Parallel OA PDF download
PDF_DOWNLOAD_WORKERS = 5
PDF_MAX_MB = 80
PDF_CONNECT_TIMEOUT = 15
PDF_READ_TIMEOUT = 60

# New PDFs are uploaded as child attachments under their paper
UPLOAD_PDF_TO_ZOTERO = False
MAX_SIMPLE_TAGS = 5

# 扩展规模
MAX_SEED_PAPERS_FOR_DISCOVERY = 12
MAX_REFERENCES_PER_SEED = 25
MAX_RELATED_PER_SEED = 12
MAX_CITING_PER_SEED = 6
SEARCH_RESULTS_PER_QUERY = 15

# 最终最多新增多少篇
MAX_NEW_PAPERS = 24
# 相关度阈值
MIN_RELEVANCE_SCORE = 6.0

# 是否导入“很相关但没有 OA PDF”的元数据
IMPORT_METADATA_WITHOUT_PDF = True

# 是否上传下载到的 OA PDF 到 Zotero storage
UPLOAD_PDF_TO_ZOTERO = False
# 新论文是否也立即进入深度分析
ANALYZE_NEW_PAPERS = True

# ------------------------------------------------------------
# 自动分类
# ------------------------------------------------------------

AUTO_CREATE_CATEGORY_COLLECTIONS = True
AUTO_ADD_TAGS = True

SOURCE_ROOT_NAME = "Sources"
MEASURE_ROOT_NAME = "Isolation"
MANUALS_FOLDER_NAME = "Manuals"

# Keep source classification intentionally simple
SOURCE_FOLDERS = {
    "PulseTube": "Pulse Tube",
}

# One isolation method = one folder
MEASURE_FOLDERS = {
    "SpringSuspension": "Spring Suspension",
    "Pendulum": "Pendulum",
    "MultiStage": "Multi-stage Isolation",
    "NegativeStiffness": "Negative Stiffness",
    "Elastomer": "Elastomer",
    "AirIsolation": "Air Spring",
    "ActiveIsolation": "Active Isolation",
    "TunedMassDamper": "Tuned Mass Damper",
    "MagneticEddy": "Magnetic-Eddy Damping",
    "FlexibleConnection": "Flexible Coupling",
    "SoftThermalLink": "Flexible Thermal Link",
    "StructuralDecoupling": "Structural Decoupling",
    "InertialMass": "Inertial Mass",
    "DampingMaterial": "Viscoelastic Damping",
    "IsolationPlatform": "Isolation Platform",
    "PhaseCancellation": "Pulse-Tube Phase Cancellation",
    "ExchangeGas": "Exchange-Gas / Non-contact Coupling",
    "CableIsolation": "Cable / Microphonic Control",
    "OtherIsolation": "Other Methods",
}

# These v21 method folders are additive. Their absence must never make an
# already-organized v20 library look "unorganized" and trigger a full rebuild.
OPTIONAL_EXPANSION_MEASURES = {
    "PhaseCancellation",
    "ExchangeGas",
    "CableIsolation",
}

# ------------------------------------------------------------
# 深度分析
# ------------------------------------------------------------

DEEP_TWO_PASS = False
ENABLE_VISION = True
MAX_SCAN_PAGES = 100
SELECTED_TEXT_PAGES = 12
MAX_INPUT_CHARS = 36000
MAX_VISION_PAGES = 3
VISION_DPI = 120
MIN_PDF_TEXT_CHARS = 600

TARGET_ANALYSIS_CHARS = "约 1800–3000 个中文字符；证据不足时宁可明确说明不足，也不要编造。"
REQUEST_TIMEOUT = 300
NETWORK_RETRIES = 1
SLEEP_SECONDS = 0.15

# 0 = 全部；测试时可先设 2
MAX_ANALYSIS_PAPERS = 0

# Strict note-contract audit
ENFORCE_NOTE_CONTRACT_FOR_ALL_BIBLIOGRAPHIC_ITEMS = True
PROMOTE_STANDALONE_PDFS_FOR_NOTE_CONTRACT = True
FINAL_NOTE_AUDIT_PASSES = 2
DEEP_QUALITY_RETRIES = 1
DEEP_MAX_OUTPUT_TOKENS = 8000
SUMMARY_USE_AI = False
BALANCED_MODE = True
REUSE_VALID_PROGRESS_ANALYSIS_FOR_WRITE_REPAIR = True
WRITE_REPAIR_FIRST = True
WRITE_REPAIR_NEVER_CALL_AI = True
STOP_BEFORE_AI_IF_WRITE_REPAIR_STILL_FAILS = True
AI_REJECTED_PREVIEW_CHARS = 260

DEEP_MIN_CHINESE_CHARS = 600
SUMMARY_MIN_CHINESE_CHARS = 60

REQUIRED_DEEP_SECTIONS = (
    "一句话结论",
    "问题定义",
    "实验装置",
    "隔振方案",
    "理论",
    "关键公式",
    "关键图表",
    "关键数据",
    "对低温系统的意义",
    "可行性",
    "下一步",
)

SKIP_IF_AI_NOTE_EXISTS = True
RESUME_FROM_PROGRESS = True
SAVE_AFTER_EACH_PAPER = True

# ------------------------------------------------------------
# 输出
# ------------------------------------------------------------

OUTPUT_BASE_DIR = ""
OUTPUT_FOLDER_NAME = "zotero_vibration_library"

AI_NOTE_MARKER = "zotero-ai-deep-analysis-0vbb-auto-v4"
DEEP_NOTE_TITLE = "深度分析"
SUMMARY_NOTE_TITLE = "摘要"

DEEP_NOTE_MARKER = "zotero-deep-analysis-v6"
SUMMARY_NOTE_MARKER = "zotero-summary-v6"

# Backward compatibility
AI_NOTE_TITLE = DEEP_NOTE_TITLE

HTTP_TIMEOUT = 45
USER_AGENT = (
    "Zotero-0vbb-literature-pipeline/1.0 "
    "(research literature discovery; open-access only)"
)


# ============================================================
# 2. 界面
# ============================================================

# True：仅显示阶段、进度、警告和最终结果
# False：显示更多调试信息
CLEAN_UI = True

# False 时可显示 AI 线路、保存等调试信息
SHOW_DEBUG = False

# 完成的进度条是否保留在终端
KEEP_FINISHED_PROGRESS = True

console = Console(
    highlight=False,
    soft_wrap=True,
)


def ui_title(title, subtitle=""):
    """Compact title."""
    body = f"[bold]{title}[/bold]"
    if subtitle:
        body += f"\n[dim]{subtitle}[/dim]"

    console.print(
        Panel.fit(
            body,
            border_style="dim",
            padding=(0, 2),
        )
    )


def log(text="", level="info"):
    """Console output."""
    text = str(text)

    if level == "debug" and not SHOW_DEBUG:
        return

    styles = {
        "ok": "green",
        "warn": "yellow",
        "error": "red",
        "info": "",
        "debug": "dim",
    }

    prefix = {
        "ok": "✓ ",
        "warn": "! ",
        "error": "× ",
        "info": "",
        "debug": "· ",
    }

    style = styles.get(level, "")

    console.print(
        prefix.get(level, "") + text,
        style=style or None,
    )


def progress_iter(iterable, description, unit="items"):
    """Progress bar."""
    try:
        total = len(iterable)
    except Exception:
        total = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(
            bar_width=26,
            complete_style="green",
            finished_style="green",
            pulse_style="cyan",
        ),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn(f"[dim]{unit}[/dim]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=not KEEP_FINISHED_PROGRESS,
        expand=False,
        refresh_per_second=8,
    ) as progress:
        task = progress.add_task(
            description,
            total=total,
        )

        for item in iterable:
            yield item
            progress.advance(task)



def analysis_progress_iter(papers):
    """Deep-analysis progress with current paper title and live stage."""
    total = len(papers)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]Deep analysis"),
        BarColumn(
            bar_width=20,
            complete_style="green",
            finished_style="green",
            pulse_style="cyan",
        ),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("[dim]papers[/dim]"),
        TextColumn("[cyan]{task.fields[current]}[/cyan]"),
        TextColumn("[magenta]{task.fields[stage]}[/magenta]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=not KEEP_FINISHED_PROGRESS,
        expand=False,
        refresh_per_second=8,
    ) as progress:
        task = progress.add_task(
            "Deep analysis",
            total=total,
            current="",
            stage="Waiting",
        )

        for index, paper in enumerate(
            papers,
            start=1,
        ):
            data = paper.get(
                "item",
                {},
            ).get(
                "data",
                {},
            )

            title = safe(
                data.get("title")
            ) or "Untitled"

            shown = title

            if len(shown) > CURRENT_TITLE_MAX_CHARS:
                shown = (
                    shown[:CURRENT_TITLE_MAX_CHARS - 1]
                    + "…"
                )

            current = (
                f"[{index}/{total}] "
                + shown
            )

            def set_stage(value):
                progress.update(
                    task,
                    current=current,
                    stage=safe(value) or "Working",
                    refresh=True,
                )

            set_stage("Starting")

            yield (
                index,
                total,
                paper,
                set_stage,
            )

            progress.advance(task)
            progress.update(
                task,
                stage="Completed",
                refresh=True,
            )

def print_summary(rows):
    """Final summary table."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
    )

    table.add_column(style="dim")
    table.add_column(justify="right")

    for name, value in rows:
        table.add_row(str(name), str(value))

    console.print(table)


# ============================================================
# 3. 基础工具
# ============================================================



def safe(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def norm_doi(doi):
    doi = safe(doi).lower()
    doi = re.sub(r"^\s*doi\s*:\s*", "", doi, flags=re.I)
    for x in (
        "https://doi.org/",
        "http://doi.org/",
        "http://dx.doi.org/",
    ):
        doi = doi.replace(x, "")
    return doi.strip().rstrip(" .;,)")


def norm_title(title):
    return re.sub(
        r"[\W_]+",
        "",
        safe(title).casefold(),
        flags=re.UNICODE,
    )


def filename_safe(text, n=130):
    text = re.sub(r'[\\/:*?"<>|\n\r\t]+', "_", safe(text))
    text = re.sub(r"\s+", " ", text).strip()
    return (text or "未命名")[:n]


def normalize_path(text):
    return "/".join(
        re.sub(r"\s+", " ", x).strip().casefold()
        for x in re.split(r"[\\/]+", safe(text))
        if x.strip()
    )


def html_to_text(text):
    text = re.sub(r"<[^>]+>", " ", safe(text))
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def http_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    })
    return s


SESSION = http_session()


def get_json(url, params=None, headers=None, timeout=HTTP_TIMEOUT):
    last = None

    for attempt in range(3):
        try:
            r = SESSION.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )

            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue

            if 500 <= r.status_code < 600:
                time.sleep(1.5 * (attempt + 1))
                continue

            if r.status_code != 200:
                return None

            return r.json()

        except Exception as e:
            last = e
            time.sleep(1.0 * (attempt + 1))

    if last:
        return None

    return None


def validate_config():
    """Validate only API credentials; whole library needs no Collection setting."""
    bad = ("PASTE_", "YOUR_", "CHANGE_ME")

    if not AI_API_KEY or any(x in AI_API_KEY for x in bad):
        raise RuntimeError("Please set AI_API_KEY.")

    if not ZOTERO_API_KEY or any(x in ZOTERO_API_KEY for x in bad):
        raise RuntimeError("Please set ZOTERO_API_KEY.")


def output_paths(collection_name='library'):
    if OUTPUT_BASE_DIR:
        base = Path(
            OUTPUT_BASE_DIR
        ).expanduser()
    else:
        try:
            base = Path(
                __file__
            ).resolve().parent
        except Exception:
            base = Path.cwd()

    root = base / OUTPUT_FOLDER_NAME
    one = root / "papers"
    download = root / "pdf_cache"

    root.mkdir(
        parents=True,
        exist_ok=True,
    )
    one.mkdir(
        parents=True,
        exist_ok=True,
    )
    download.mkdir(
        parents=True,
        exist_ok=True,
    )

    return {
        "root": root,
        "one": one,
        "download": download,
        "html": root / "library_analysis.html",
        "progress": root / "progress.json",
        "discovery": root / "discovery.json",
        "expansion_state": root / "pulse_tube_expansion_state.json",
        "design_guide": root / "pulse_tube_isolation_design_guide.html",
        "design_guide_state": root / "pulse_tube_design_guide_state.json",
    }


def pulse_tube_expansion_due(
    paths,
):
    """Run the focused expansion once per expansion ID unless forced."""
    if not PULSE_TUBE_EXPANSION_ENABLED:
        return False

    if FORCE_PULSE_TUBE_EXPANSION:
        return True

    if not PULSE_TUBE_EXPANSION_RUN_ONCE:
        return True

    state_path = paths.get(
        "expansion_state"
    )

    if not state_path or not state_path.exists():
        return True

    try:
        state = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return True

    return safe(
        state.get(
            "expansion_id"
        )
    ) != PULSE_TUBE_EXPANSION_ID


def mark_pulse_tube_expansion_done(
    paths,
    imported_count,
):
    state_path = paths.get(
        "expansion_state"
    )

    if not state_path:
        return

    state_path.write_text(
        json.dumps(
            {
                "expansion_id": PULSE_TUBE_EXPANSION_ID,
                "completed": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "imported_or_updated": int(
                    imported_count
                    or 0
                ),
                "pdf_download": bool(
                    DISCOVERY_DOWNLOAD_PDFS
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _design_guide_signature(
    rows,
):
    payload = []

    for row in rows:
        payload.append(
            safe(
                row.get(
                    "ZoteroKey"
                )
            )
            + "\n"
            + safe(
                row.get(
                    "Title"
                )
            )
            + "\n"
            + safe(
                row.get(
                    "Analysis"
                )
            )
        )

    return hashlib.sha256(
        "\n---\n".join(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _design_guide_row_score(
    row,
):
    text_value = (
        safe(
            row.get(
                "Title"
            )
        )
        + " "
        + safe(
            row.get(
                "Analysis"
            )
        )[:5000]
    ).casefold()

    score = 0.0

    weights = {
        "pulse tube": 9.0,
        "pulse-tube": 9.0,
        "dilution refrigerator": 6.0,
        "mixing chamber": 4.0,
        "vibration isolation": 6.0,
        "spring pendulum": 6.0,
        "phase cancellation": 6.0,
        "copper braid": 4.0,
        "thermal link": 4.0,
        "bellows": 4.0,
        "exchange gas": 5.0,
        "transfer path": 5.0,
        "transmissibility": 4.0,
        "microphonic": 3.0,
        "negative stiffness": 3.0,
        "quasi-zero stiffness": 3.0,
    }

    for phrase, weight in weights.items():
        if phrase in text_value:
            score += weight

    grade = safe(
        row.get(
            "Grade"
        )
    ).upper()

    if grade == "A":
        score += 8.0
    elif grade == "B":
        score += 4.0

    return score


def generate_pulse_tube_design_guide(
    routes,
    results,
    paths,
):
    """
    Generate one cross-paper engineering guide from existing deep analyses.

    This costs one strong-model synthesis call only when the analysis corpus
    changed. It never affects the Zotero note contract if synthesis fails.
    """
    if not GENERATE_PULSE_TUBE_DESIGN_GUIDE:
        return False

    rows = [
        row
        for row in (
            results
            or []
        )
        if safe(
            row.get(
                "Analysis"
            )
        ).strip()
    ]

    if not rows:
        return False

    rows.sort(
        key=_design_guide_row_score,
        reverse=True,
    )

    selected = rows[
        :DESIGN_GUIDE_MAX_PAPERS
    ]

    signature = _design_guide_signature(
        selected
    )

    state_path = paths.get(
        "design_guide_state"
    )

    guide_path = paths.get(
        "design_guide"
    )

    if (
        not FORCE_REGENERATE_DESIGN_GUIDE
        and state_path
        and state_path.exists()
        and guide_path
        and guide_path.exists()
    ):
        try:
            old_state = json.loads(
                state_path.read_text(
                    encoding="utf-8"
                )
            )

            if safe(
                old_state.get(
                    "signature"
                )
            ) == signature:
                log(
                    "Pulse-tube design guide unchanged -> skip synthesis",
                    "ok",
                )
                return True

        except Exception:
            pass

    evidence_blocks = []

    for index, row in enumerate(
        selected,
        start=1,
    ):
        evidence_blocks.append(
            f"""
===== 文献 {index} =====
标题：{safe(row.get("Title"))}
等级：{safe(row.get("Grade"))}
分类：{safe(row.get("Isolation"))}
深度分析摘录：
{safe(row.get("Analysis"))[:DESIGN_GUIDE_CHARS_PER_PAPER]}
""".strip()
        )

    prompt = rf"""
你是一名负责设计低振动 pulse-tube 干式稀释制冷机的高级低温机械工程师。
请基于下面已经完成的论文深度分析，生成一份可以直接用于实验室方案设计、
结构评审、测试计划和采购决策的中文工程指南。

对象：
- pulse-tube 预冷的 dry dilution refrigerator
- mixing chamber / detector stage 上的低噪声低温探测器
- 特别关注 0νββ / bolometer / quantum / scanning probe 等振动敏感负载

原则：
- 只把文献明确报告的数值当作“文献事实”。
- 跨论文推导、工程建议和计算必须明确写成“综合建议”。
- 不要因为某方法在室温有效就假定其在 mK 直接有效。
- 必须同时考虑机械隔振、冷量、热收缩、线缆、软管、结构旁路和可维护性。
- 如果不同论文结论冲突，明确列出差异和可能原因。
- 所有公式用 KaTeX 兼容 LaTeX。
- 目标不是综述文章，而是帮助我真正搭建和改进装置。

必须包含以下内容：

# 1. 系统级结论
给出最值得优先实施的 5 条结论。

# 2. Pulse Tube 工作原理
解释 regenerator、pulse tube、pressure/mass-flow phase、orifice/inertance/reservoir、
rotary valve/compressor 如何产生制冷；区分论文证据与通用理论。

# 3. 振动为什么产生
逐项分析：
- 周期压力力 $F \approx \Delta p A$
- cold head / cold stage 周期形变与反作用力
- rotary valve / motor / compressor / helium hose
- pulse-tube 基频与谐波
- 结构模态被谐波激发
- thermal link / support / cable / pumping line 的旁路
- microphonics / triboelectric coupling

# 4. 振动传播路径图
按 Source -> Path -> Receiver 写出完整路径，并分：
300 K、40–50 K、4 K、still、mixing chamber、detector stage。

# 5. 隔振方法比较
用表格比较：
spring suspension、pendulum、multi-stage、negative/QZS、air isolation、
active isolation、phase cancellation、flexible bellows/hose、copper braid、
exchange-gas/non-contact thermal coupling、structural decoupling、inertial mass、
eddy-current damping、viscoelastic damping、TMD、cable/microphonic control。
列出：作用频段、低温可行性、优点、风险、热学代价、最适合安装的位置。

# 6. 推荐的系统架构
给出一套“优先推荐”的分层方案：
A. source-side
B. 300 K interface
C. 40 K / 4 K thermal-mechanical links
D. mixing chamber / detector payload
E. cables / hoses
F. floor / frame / external services

# 7. 设计计算
至少解释并使用：
$$
f_n = \frac{{1}}{{2\pi}}\sqrt{{\frac{{k}}{{m}}}}
$$

$$
\delta = \frac{{mg}}{{k}}
$$

$$
r = \frac{{f}}{{f_n}}
$$

$$
T =
\sqrt{{
\frac{{1+(2\zeta r)^2}}
{{(1-r^2)^2+(2\zeta r)^2}}
}}
$$

并说明低频 pulse-tube 基频附近为什么不能只看“软一点”。
讨论多级隔振、共振避让、阻尼和横向/扭转模态。

# 8. 热学-机械折中
重点讨论 copper braid / flexible strap / exchange gas / non-contact link：
怎样在导热足够时尽量减小机械刚度，以及冷却时间、温差和热收缩风险。

# 9. 测量与诊断计划
给出传感器位置、三轴加速度、PSD/ASD、位移谱、transfer function、
PT on/off、compressor/valve isolation test、逐路径 A/B test 的具体顺序。

# 10. 我现在最值得做的实验
按“当天可做 / 一周内 / 结构改造后”列出动作。
每项写：目的、做法、需要测什么、成功判据。

# 11. 可直接采购/加工的部件类型
只写器件类别和关键规格，不编造具体商品：
springs、braids、bellows、flex hose、accelerometers、isolator、
eddy-current damper、QZS/negative-stiffness platform、cable clamps 等。

# 12. 风险清单
至少覆盖：
cooldown、thermal contraction、alignment、vacuum、heat leak、resonance、
wire bypass、hose bypass、ground loop、microphonics、maintenance。

# 13. 文献证据地图
列出最值得先读的论文，以及每篇最值得借鉴的设计点。

最后给：
**首选架构：**
**第一优先实验：**
**最可能的隐藏振动旁路：**
**最不建议直接照搬的方法：**

【已有深度分析】
{chr(10).join(evidence_blocks)}
""".strip()

    console.print()
    console.rule(
        "Pulse-tube design synthesis",
        style="dim",
    )

    guide, error, meta = call_ai(
        routes,
        prompt,
        max_output_tokens=DESIGN_GUIDE_MAX_OUTPUT_TOKENS,
    )

    if not guide:
        log(
            f"Design guide synthesis skipped/failed: {safe(error)[:500]}",
            "warn",
        )
        return False

    if len(
        re.findall(
            r"[\u4e00-\u9fff]",
            safe(
                guide
            ),
        )
    ) < 900:
        log(
            "Design guide output was too short; not saving as final guide.",
            "warn",
        )
        return False

    if guide_path:
        guide_path.write_text(
            rendered_html_document(
                "Pulse Tube 隔振工程设计指南",
                guide,
            ),
            encoding="utf-8",
        )

    if state_path:
        state_path.write_text(
            json.dumps(
                {
                    "signature": signature,
                    "updated": time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "paper_count": len(
                        selected
                    ),
                    "model": safe(
                        meta.get(
                            "model"
                        )
                    ),
                    "api": safe(
                        meta.get(
                            "api"
                        )
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    log(
        f"Pulse-tube design guide ready: {guide_path}",
        "ok",
    )

    return True
def zotero_client():
    from pyzotero import zotero

    z = zotero.Zotero(
        ZOTERO_LIBRARY_ID,
        ZOTERO_LIBRARY_TYPE,
        ZOTERO_API_KEY,
        upload_timeout=240,
    )

    info = z.key_info()

    log(
        "Zotero: "
        + (
            info.get("username")
            or info.get("displayName")
            or "Connected"
        )
    )

    return z


def safe_item_template(
    zot,
    itemtype,
    linkmode=None,
):
    """
    Build the small Zotero payloads used by this pipeline locally.

    IMPORTANT:
    This function never calls zot.item_template(), therefore this script never
    performs GET /items/new. That endpoint is unnecessary for our write paths
    and caused long-run failures in some Pyzotero versions/proxies.

    Zotero accepts partial item JSON for create_items() as long as itemType and
    the fields being written are supplied.
    """
    itemtype = safe(itemtype).strip()

    if not itemtype:
        raise ValueError("itemtype is required")

    if itemtype == "note":
        return {
            "itemType": "note",
            "note": "",
            "tags": [],
            "relations": {},
        }

    if itemtype == "journalArticle":
        return {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "abstractNote": "",
            "publicationTitle": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "date": "",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "",
            "language": "",
            "DOI": "",
            "ISSN": "",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "tags": [],
            "collections": [],
            "relations": {},
        }

    if itemtype == "document":
        return {
            "itemType": "document",
            "title": "",
            "creators": [],
            "abstractNote": "",
            "publisher": "",
            "date": "",
            "language": "",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "tags": [],
            "collections": [],
            "relations": {},
        }

    if itemtype == "attachment":
        payload = {
            "itemType": "attachment",
            "title": "",
            "linkMode": linkmode or "linked_url",
            "contentType": "",
            "charset": "",
            "url": "",
            "filename": "",
            "note": "",
            "tags": [],
            "relations": {},
        }
        return payload

    # We do not create other types in the current pipeline. Failing loudly is
    # safer than silently touching /items/new.
    raise ValueError(
        f"Unsupported local Zotero template type: {itemtype}"
    )

def collection_key(c):
    return safe(
        c.get("key")
        or c.get("data", {}).get("key")
    )


def collection_name(c):
    return safe(
        c.get("data", {}).get(
            "name",
            c.get("name", ""),
        )
    )


def collection_parent(c):
    p = c.get("data", {}).get(
        "parentCollection",
        False,
    )
    return "" if not p else safe(p)


def collection_index(zot):
    cols = zot.everything(zot.collections())
    by_key = {
        collection_key(c): c
        for c in cols
        if collection_key(c)
    }

    cache = {}

    def build(k, seen=None):
        if k in cache:
            return cache[k]

        seen = seen or set()

        if k in seen:
            return collection_name(by_key.get(k, {}))

        seen.add(k)

        c = by_key.get(k, {})
        name = collection_name(c)
        parent = collection_parent(c)

        if parent and parent in by_key:
            value = build(parent, seen) + "/" + name
        else:
            value = name

        cache[k] = value
        return value

    for k in by_key:
        build(k)

    return cols, by_key, cache


def resolve_collection(zot):
    cols, by_key, paths = collection_index(zot)

    if COLLECTION_KEY:
        if COLLECTION_KEY not in by_key:
            raise RuntimeError(
                f"找不到 Collection Key：{COLLECTION_KEY}"
            )
        k = COLLECTION_KEY
        return by_key[k], by_key, paths

    if COLLECTION_PATH:
        wanted = normalize_path(COLLECTION_PATH)
        matches = [
            k
            for k, p in paths.items()
            if normalize_path(p) == wanted
        ]

        if len(matches) != 1:
            raise RuntimeError(
                f"COLLECTION_PATH 匹配数量={len(matches)}，"
                "建议改用 COLLECTION_KEY。"
            )

        k = matches[0]
        return by_key[k], by_key, paths

    matches = [
        k
        for k, c in by_key.items()
        if collection_name(c).casefold()
        == COLLECTION_NAME.casefold()
    ]

    if len(matches) == 1:
        k = matches[0]
        return by_key[k], by_key, paths

    if len(matches) > 1:
        log("Duplicate Collection names:", "warn")
        for k in matches:
            log(f"   {paths[k]} [{k}]")

    raise RuntimeError(
        "无法唯一确定 Collection，请填写 COLLECTION_KEY。"
    )


def descendant_keys(target_key, by_key):
    keys = [target_key]

    if not INCLUDE_SUBCOLLECTIONS:
        return keys

    changed = True

    while changed:
        changed = False

        for k, c in by_key.items():
            if (
                collection_parent(c) in keys
                and k not in keys
            ):
                keys.append(k)
                changed = True

    return keys


def is_paper(item):
    return safe(
        item.get("data", {}).get("itemType")
    ) not in (
        "note",
        "attachment",
        "annotation",
    )


def collect_collection_papers(zot, keys, paths):
    found = {}

    for k in progress_iter(
        keys,
        description="Read folders",
        unit="folders",
    ):
        items = zot.everything(
            zot.collection_items_top(k)
        )

        for item in items:
            if not is_paper(item):
                continue

            ikey = safe(item.get("key"))

            if not ikey:
                continue

            if ikey not in found:
                found[ikey] = {
                    "item": item,
                    "collections": [],
                }

            if paths.get(k, k) not in found[ikey]["collections"]:
                found[ikey]["collections"].append(
                    paths.get(k, k)
                )

    return list(found.values())


def all_library_index(zot):
    """用于新增前去重。"""
    doi_map = {}
    title_map = {}

    log("Build Zotero index", "info")

    items = zot.everything(
        zot.top()
    )

    for item in progress_iter(
        items,
        description="Build index",
        unit="items",
    ):
        if not is_paper(item):
            continue

        data = item.get("data", {})
        doi = norm_doi(data.get("DOI"))
        title = norm_title(data.get("title"))

        if doi:
            doi_map[doi] = item

        if title:
            title_map[title] = item

    return doi_map, title_map


# ============================================================
# 5. OpenAlex / Unpaywall
# ============================================================

def openalex_params(extra=None):
    p = {}
    if OPENALEX_API_KEY:
        p["api_key"] = OPENALEX_API_KEY
    if extra:
        p.update(extra)
    return p


def reconstruct_abstract(inv):
    if not isinstance(inv, dict):
        return ""

    pairs = []

    for word, positions in inv.items():
        if not isinstance(positions, list):
            continue

        for pos in positions:
            try:
                pairs.append((int(pos), word))
            except Exception:
                pass

    pairs.sort(key=lambda x: x[0])
    return " ".join(word for _, word in pairs)


def openalex_work_by_doi(doi):
    doi = norm_doi(doi)

    if not doi:
        return None

    url = (
        "https://api.openalex.org/works/"
        + quote(
            "https://doi.org/" + doi,
            safe=":/",
        )
    )

    return get_json(
        url,
        params=openalex_params(),
    )


def openalex_work_by_title(title):
    data = get_json(
        "https://api.openalex.org/works",
        params=openalex_params({
            "search": title,
            "per_page": 5,
        }),
    )

    if not data:
        return None

    results = data.get("results", [])

    if not results:
        return None

    wanted = norm_title(title)

    best = None
    best_score = 0

    for work in results:
        got = norm_title(work.get("title"))

        if not got:
            continue

        # 简单标题重合
        common = len(
            set(re.findall(r"[a-z0-9]+", wanted))
            & set(re.findall(r"[a-z0-9]+", got))
        )

        score = common

        if wanted == got:
            score += 100

        if score > best_score:
            best_score = score
            best = work

    return best or results[0]


def openalex_work_for_zotero_item(item):
    data = item.get("data", {})
    doi = norm_doi(data.get("DOI"))

    if doi:
        work = openalex_work_by_doi(doi)

        if work:
            return work

    title = safe(data.get("title"))

    if title:
        return openalex_work_by_title(title)

    return None


def openalex_batch_ids(ids):
    ids = [
        safe(x).split("/")[-1]
        for x in ids
        if safe(x)
    ]

    out = []

    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]

        if not batch:
            continue

        data = get_json(
            "https://api.openalex.org/works",
            params=openalex_params({
                "filter": (
                    "openalex:"
                    + "|".join(batch)
                ),
                "per_page": 100,
            }),
        )

        if data:
            out.extend(
                data.get("results", [])
            )

    return out


def openalex_citing(openalex_id, limit):
    wid = safe(openalex_id).split("/")[-1]

    if not wid:
        return []

    data = get_json(
        "https://api.openalex.org/works",
        params=openalex_params({
            "filter": f"cites:{wid}",
            "sort": "-publication_date",
            "per_page": min(limit, 100),
        }),
    )

    return (
        data.get("results", [])
        if data
        else []
    )


def openalex_search(query, limit):
    data = get_json(
        "https://api.openalex.org/works",
        params=openalex_params({
            "search": query,
            "filter": "type:article|preprint",
            "sort": "-relevance_score",
            "per_page": min(limit, 100),
        }),
    )

    return (
        data.get("results", [])
        if data
        else []
    )


def work_doi(work):
    doi = safe(work.get("doi"))
    return norm_doi(doi)


def work_title(work):
    return safe(
        work.get("title")
        or work.get("display_name")
    )


def work_year(work):
    return safe(
        work.get("publication_year")
        or work.get("publication_date", "")[:4]
    )


def work_authors(work):
    names = []

    for a in work.get("authorships", []) or []:
        name = safe(
            a.get("author", {}).get("display_name")
            or a.get("raw_author_name")
        )

        if name:
            names.append(name)

    return names


def work_venue(work):
    loc = work.get("primary_location") or {}
    source = loc.get("source") or {}
    return safe(source.get("display_name"))


def work_abstract(work):
    return reconstruct_abstract(
        work.get("abstract_inverted_index")
    )


def work_landing_url(work):
    loc = work.get("best_oa_location") or {}
    return safe(
        loc.get("landing_page_url")
        or (
            work.get("primary_location")
            or {}
        ).get("landing_page_url")
        or work.get("doi")
        or work.get("id")
    )


def unpaywall_pdf(doi):
    doi = norm_doi(doi)

    if (
        not doi
        or not UNPAYWALL_EMAIL
        or "请改成" in UNPAYWALL_EMAIL
    ):
        return ""

    data = get_json(
        "https://api.unpaywall.org/v2/"
        + quote(doi, safe=""),
        params={
            "email": UNPAYWALL_EMAIL,
        },
    )

    if not data:
        return ""

    best = data.get("best_oa_location") or {}

    url = safe(
        best.get("url_for_pdf")
    )

    if url:
        return url

    for loc in data.get("oa_locations", []) or []:
        url = safe(
            loc.get("url_for_pdf")
        )

        if url:
            return url

    return ""


def oa_pdf_urls(work):
    """只收集 OA 元数据明确提供的 PDF。"""
    urls = []

    for loc in [
        work.get("best_oa_location"),
        work.get("primary_location"),
        *(work.get("locations", []) or []),
    ]:
        if not isinstance(loc, dict):
            continue

        if loc.get("is_oa") is False:
            continue

        url = safe(loc.get("pdf_url"))

        if url and url not in urls:
            urls.append(url)

    doi = work_doi(work)
    up = unpaywall_pdf(doi)

    if up and up not in urls:
        urls.append(up)

    return urls


# ============================================================
# 6. 相关度、分类、标签
# ============================================================

CATEGORY_RULES = {
    "01_0νββ与低温探测器": [
        "neutrinoless double beta",
        "double beta decay",
        "0νββ",
        "0vbb",
        "bolometer",
        "bolometric",
        "cryogenic detector",
        "calorimeter",
        "cuore",
        "cupID",
        "legend",
        "nemo",
    ],
    "02_干式稀释制冷机": [
        "dry dilution refrigerator",
        "dilution refrigerator",
        "dilution refrigeration",
        "mixing chamber",
        "cryostat",
        "millikelvin",
        "milli-kelvin",
    ],
    "03_PulseTube振动源": [
        "pulse tube",
        "pulse-tube",
        "cryocooler",
        "cold head",
        "compressor vibration",
    ],
    "04_被动隔振": [
        "passive isolation",
        "passive vibration",
        "spring suspension",
        "pendulum",
        "elastomer",
        "negative stiffness",
        "mechanical filter",
    ],
    "05_主动隔振": [
        "active vibration",
        "active isolation",
        "feedback vibration",
        "feedforward vibration",
        "inertial sensor",
        "piezo actuator",
    ],
    "06_低温热连接": [
        "thermal link",
        "thermal conductance",
        "thermalization",
        "copper braid",
        "heat strap",
        "heat leak",
        "cooling power",
    ],
    "07_振动测量与PSD": [
        "power spectral density",
        "spectral density",
        "accelerometer",
        "geophone",
        "interferometer",
        "fft",
        "asd",
        "vibration measurement",
    ],
    "08_机械噪声与微音": [
        "mechanical noise",
        "microphonic",
        "microphonics",
        "vibration noise",
        "phonon noise",
    ],
    "09_基础隔振理论": [
        "transmissibility",
        "transfer function",
        "natural frequency",
        "resonance",
        "damping ratio",
        "vibration theory",
    ],
}


RELEVANCE_WEIGHTS = {
    "pulse tube": 8.0,
    "pulse-tube": 8.0,
    "pulse tube cryocooler": 8.0,
    "pulse tube refrigerator": 7.0,
    "dry dilution refrigerator": 7.0,
    "dilution refrigerator": 5.0,
    "vibration isolation": 6.0,
    "vibration generation": 6.0,
    "vibration spectrum": 5.0,
    "pressure oscillation": 4.0,
    "regenerator": 2.5,
    "inertance tube": 3.0,
    "rotary valve": 4.0,
    "cold head": 3.0,
    "cold stage": 2.5,
    "mixing chamber": 4.0,
    "transfer path": 5.0,
    "transmissibility": 4.0,
    "mechanical noise": 4.0,
    "microphonic": 4.0,
    "triboelectric": 3.0,
    "thermal link": 4.0,
    "copper braid": 4.0,
    "flexible bellows": 4.0,
    "phase cancellation": 6.0,
    "active noise cancellation": 6.0,
    "exchange gas": 5.0,
    "non-contact heat exchanger": 5.0,
    "spring pendulum": 6.0,
    "negative stiffness": 4.0,
    "quasi-zero stiffness": 4.0,
    "cryogenic detector": 4.0,
    "bolometer": 4.0,
    "bolometric": 4.0,
    "neutrinoless double beta": 4.0,
    "0νββ": 4.0,
    "0vbb": 4.0,
    "power spectral density": 3.0,
    "accelerometer": 2.0,
    "cryostat": 2.0,
    "millikelvin": 3.0,
}


def work_text(work):
    topic_names = []

    for t in work.get("topics", []) or []:
        if isinstance(t, dict):
            name = safe(
                t.get("display_name")
                or t.get("subfield", {}).get("display_name")
            )

            if name:
                topic_names.append(name)

    return " ".join([
        work_title(work),
        work_abstract(work),
        " ".join(topic_names),
        work_venue(work),
    ]).casefold()


def relevance_score(work, discovery_sources=None):
    text = work_text(work)
    score = 0.0

    for phrase, weight in RELEVANCE_WEIGHTS.items():
        if phrase.casefold() in text:
            score += weight

    sources = discovery_sources or []

    if "reference" in sources:
        score += 1.5

    if "related" in sources:
        score += 2.0

    if "citing" in sources:
        score += 2.0

    if "search" in sources:
        score += 1.0

    # 引用数只做轻微加分
    cited = work.get("cited_by_count") or 0

    try:
        score += min(
            math.log10(int(cited) + 1),
            2.5,
        )
    except Exception:
        pass

    return round(score, 2)


def classify_work(work):
    text = work_text(work)
    category_scores = {}

    for category, words in CATEGORY_RULES.items():
        score = 0

        for word in words:
            if word.casefold() in text:
                score += 1

        category_scores[category] = score

    best = max(
        category_scores,
        key=category_scores.get,
    )

    if category_scores[best] == 0:
        best = "10_相关背景"

    tags = {
        "AI-自动发现",
        "0νββ-文献扩展",
    }

    for category, score in category_scores.items():
        if score > 0:
            tags.add(
                category.split("_", 1)[-1]
            )

    # OpenAlex topics 取前 3 个
    for topic in (work.get("topics", []) or [])[:3]:
        name = safe(
            topic.get("display_name")
        )

        if name:
            tags.add(
                "OA主题:" + name[:60]
            )

    return best, sorted(tags)


# ============================================================
# 7. 自动发现候选文献
# ============================================================

def candidate_key(work):
    doi = work_doi(work)

    if doi:
        return "doi:" + doi

    oid = safe(work.get("id"))

    if oid:
        return "oa:" + oid.split("/")[-1]

    return "title:" + norm_title(work_title(work))


def merge_candidate(store, work, source, seed_title=""):
    if not work or not work_title(work):
        return

    key = candidate_key(work)

    if key not in store:
        store[key] = {
            "work": work,
            "sources": [],
            "seed_titles": [],
        }

    if source not in store[key]["sources"]:
        store[key]["sources"].append(source)

    if seed_title and seed_title not in store[key]["seed_titles"]:
        store[key]["seed_titles"].append(seed_title)


def choose_discovery_seeds(papers):
    scored = []

    for paper in papers:
        item = paper["item"]
        text = (
            safe(item.get("data", {}).get("title"))
            + " "
            + safe(item.get("data", {}).get("abstractNote"))
        ).casefold()

        score = sum(
            weight
            for phrase, weight in RELEVANCE_WEIGHTS.items()
            if phrase.casefold() in text
        )

        scored.append((score, paper))

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return [
        p
        for _, p in scored[
            :MAX_SEED_PAPERS_FOR_DISCOVERY
        ]
    ]


def discover_candidates(seed_papers):
    candidates = {}
    seeds = choose_discovery_seeds(seed_papers)

    log(
        f"文献扩展：使用 {len(seeds)} 篇种子论文。"
    )

    # 参考文献 / related / citing
    for paper in progress_iter(
        seeds,
        description="Reference network",
        unit="papers",
    ):
        item = paper["item"]
        seed_title = safe(
            item.get("data", {}).get("title")
        )

        work = openalex_work_for_zotero_item(
            item
        )

        if not work:
            continue

        if DISCOVER_FROM_REFERENCES:
            ids = (
                work.get("referenced_works", [])
                or []
            )[:MAX_REFERENCES_PER_SEED]

            refs = openalex_batch_ids(ids)

            for ref in refs:
                merge_candidate(
                    candidates,
                    ref,
                    "reference",
                    seed_title,
                )

        if DISCOVER_FROM_RELATED:
            ids = (
                work.get("related_works", [])
                or []
            )[:MAX_RELATED_PER_SEED]

            rels = openalex_batch_ids(ids)

            for rel in rels:
                merge_candidate(
                    candidates,
                    rel,
                    "related",
                    seed_title,
                )

        if DISCOVER_FROM_CITING:
            citing = openalex_citing(
                work.get("id"),
                MAX_CITING_PER_SEED,
            )

            for c in citing:
                merge_candidate(
                    candidates,
                    c,
                    "citing",
                    seed_title,
                )

    # 网络主题搜索
    if DISCOVER_FROM_TOPIC_SEARCH:
        for query in progress_iter(
            SEARCH_QUERIES,
            description="Topic search",
            unit="queries",
        ):
            works = openalex_search(
                query,
                SEARCH_RESULTS_PER_QUERY,
            )

            for work in works:
                merge_candidate(
                    candidates,
                    work,
                    "search",
                    query,
                )

    # 计算相关度
    ranked = []

    for record in candidates.values():
        work = record["work"]
        score = relevance_score(
            work,
            record["sources"],
        )

        record["score"] = score
        record["category"], record["tags"] = (
            classify_work(work)
        )

        if score >= MIN_RELEVANCE_SCORE:
            ranked.append(record)

    ranked.sort(
        key=lambda x: (
            x["score"],
            x["work"].get("cited_by_count", 0) or 0,
        ),
        reverse=True,
    )

    return ranked


# ============================================================
# 8. 下载 OA PDF + 导入 Zotero
# ============================================================

def download_pdf(url, target):
    """Stream a real PDF directly to disk."""
    tmp = target.with_suffix(
        target.suffix + ".part"
    )

    try:
        with requests.get(
            url,
            timeout=(
                PDF_CONNECT_TIMEOUT,
                PDF_READ_TIMEOUT,
            ),
            stream=True,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 ZoteroLiterature/1.0"
                )
            },
        ) as r:
            if r.status_code != 200:
                return False

            content_type = safe(
                r.headers.get("Content-Type")
            ).casefold()

            length = r.headers.get(
                "Content-Length"
            )

            if length:
                try:
                    if (
                        int(length)
                        > PDF_MAX_MB * 1024 * 1024
                    ):
                        return False
                except Exception:
                    pass

            total = 0
            first = b""

            with tmp.open("wb") as f:
                for chunk in r.iter_content(
                    chunk_size=1024 * 512
                ):
                    if not chunk:
                        continue

                    if not first:
                        first = chunk[:8]

                    total += len(chunk)

                    if (
                        total
                        > PDF_MAX_MB * 1024 * 1024
                    ):
                        f.close()
                        tmp.unlink(missing_ok=True)
                        return False

                    f.write(chunk)

            if (
                not first.startswith(b"%PDF")
                and "pdf" not in content_type
            ):
                tmp.unlink(missing_ok=True)
                return False

            tmp.replace(target)
            return True

    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return False

def download_work_pdf(work, folder):
    title = work_title(work)
    doi = work_doi(work)

    name = filename_safe(
        f"{work_year(work)}_{title}",
        150,
    ) + ".pdf"

    target = folder / name

    if target.exists():
        try:
            if target.read_bytes()[:4] == b"%PDF":
                return str(target), "OACache"
        except Exception:
            pass

    for url in oa_pdf_urls(work):
        if download_pdf(url, target):
            return str(target), url

    return "", ""


def ensure_category_collections(
    zot,
    target_key="",
    by_key=None,
):
    """Compatibility wrapper: reuse the current managed classification tree."""
    return ensure_library_classification_tree(zot)

def openalex_to_zotero_template(zot, record):
    work = record["work"]
    template = safe_item_template(zot, 
        "journalArticle"
    )

    template["title"] = work_title(work)

    authors = work_authors(work)
    creators = []

    for name in authors:
        parts = name.split()

        if len(parts) >= 2:
            creators.append({
                "creatorType": "author",
                "firstName": " ".join(parts[:-1]),
                "lastName": parts[-1],
            })
        else:
            creators.append({
                "creatorType": "author",
                "name": name,
            })

    template["creators"] = creators
    template["abstractNote"] = work_abstract(work)
    template["publicationTitle"] = work_venue(work)
    template["date"] = safe(
        work.get("publication_date")
        or work.get("publication_year")
    )
    template["DOI"] = work_doi(work)
    template["url"] = work_landing_url(work)

    biblio = work.get("biblio") or {}

    template["volume"] = safe(
        biblio.get("volume")
    )
    template["issue"] = safe(
        biblio.get("issue")
    )

    first = safe(
        biblio.get("first_page")
    )
    last = safe(
        biblio.get("last_page")
    )

    if first and last:
        template["pages"] = (
            first + "-" + last
        )
    elif first:
        template["pages"] = first

    tags = list(record.get("tags", []))

    tags.extend([
        f"AI相关度:{record['score']:.1f}",
        "来源:" + "+".join(
            record.get("sources", [])
        ),
    ])

    template["tags"] = [
        {"tag": x}
        for x in sorted(set(tags))
        if x
    ]

    return template


def add_item_to_collection(zot, key, item):
    """Add an item using the latest Zotero version."""
    if not key or not item:
        return False

    item_key = safe(
        item.get("key")
        or item.get("data", {}).get("key")
    )

    if not item_key:
        log("Collection write skipped: missing item key", "warn")
        return False

    try:
        fresh = zot.item(item_key)
        ok = zot.addto_collection(key, fresh)

        if ok:
            return True

        log(
            f"Collection write returned False: {item_key} -> {key}",
            "warn",
        )
        return False

    except Exception as e:
        log(
            f"Collection write failed: {item_key} -> {key} | {e}",
            "warn",
        )
        return False


def import_candidate(
    zot,
    record,
    target_key,
    category_map,
    doi_map,
    title_map,
    download_folder,
):
    work = record["work"]
    doi = work_doi(work)
    title_n = norm_title(work_title(work))

    # 已在文库
    existing = (
        doi_map.get(doi)
        if doi
        else None
    )

    if not existing and title_n:
        existing = title_map.get(title_n)

    category = record["category"]
    pdf_path = ""
    pdf_source = ""

    if existing:
        # 补标签/分类
        try:
            if AUTO_ADD_TAGS:
                zot.add_tags(
                    existing,
                    *record["tags"],
                    f"AI相关度:{record['score']:.1f}",
                )
        except Exception:
            pass

        if category_map.get(category):
            add_item_to_collection(
                zot,
                category_map[category],
                existing,
            )

        add_item_to_collection(
            zot,
            target_key,
            existing,
        )

        return {
            "status": "Existing",
            "item": existing,
            "pdf_path": "",
            "pdf_source": "",
        }

    # 先找 OA PDF
    pdf_path, pdf_source = (
        download_work_pdf(
            work,
            download_folder,
        )
    )

    if (
        not pdf_path
        and not IMPORT_METADATA_WITHOUT_PDF
    ):
        return {
            "status": "NoOA",
            "item": None,
            "pdf_path": "",
            "pdf_source": "",
        }

    # 创建文献条目
    try:
        template = openalex_to_zotero_template(
            zot,
            record,
        )

        created = zot.create_items(
            [template]
        )

        success = (
            created.get("success", {})
            if isinstance(created, dict)
            else {}
        )

        new_key = (
            success.get("0")
            if isinstance(success, dict)
            else None
        )

        if not new_key:
            return {
                "status": "ImportFailed",
                "item": None,
                "pdf_path": pdf_path,
                "pdf_source": pdf_source,
            }

        item = zot.item(new_key)

    except Exception as e:
        return {
            "status": f"ImportFailed:{e}",
            "item": None,
            "pdf_path": pdf_path,
            "pdf_source": pdf_source,
        }

    # 主文件夹 + 分类文件夹
    add_item_to_collection(
        zot,
        target_key,
        item,
    )

    if category_map.get(category):
        add_item_to_collection(
            zot,
            category_map[category],
            item,
        )

    # 上传 PDF
    if pdf_path and UPLOAD_PDF_TO_ZOTERO:
        try:
            zot.attachment_simple(
                [pdf_path],
                parentid=new_key,
            )
        except Exception as e:
            log(f"PDF upload failed: {work_title(work)[:60]} | {e}", "warn")

    # 更新去重索引
    if doi:
        doi_map[doi] = item

    if title_n:
        title_map[title_n] = item

    return {
        "status": (
            "ImportedPDF"
            if pdf_path
            else "ImportedMetadata"
        ),
        "item": item,
        "pdf_path": pdf_path,
        "pdf_source": pdf_source,
    }


def run_auto_discovery(
    zot,
    seed_papers,
    target_key,
    by_key,
    paths,
):
    if not AUTO_DISCOVER_RELATED:
        return []

    log("Discover / download / classify literature")

    candidates = discover_candidates(
        seed_papers
    )

    log(
        f"相关度筛选后候选：{len(candidates)} 篇"
    )

    doi_map, title_map = all_library_index(
        zot
    )

    category_map = ensure_category_collections(
        zot,
        target_key,
        by_key,
    )

    selected = candidates[
        :MAX_NEW_PAPERS
    ]

    results = []

    for record in progress_iter(
        selected,
        description="Import papers",
        unit="papers",
    ):
        imported = import_candidate(
            zot,
            record,
            target_key,
            category_map,
            doi_map,
            title_map,
            paths["download"],
        )

        work = record["work"]

        results.append({
            "title": work_title(work),
            "doi": work_doi(work),
            "year": work_year(work),
            "score": record["score"],
            "category": record["category"],
            "tags": record["tags"],
            "sources": record["sources"],
            "seed_titles": record["seed_titles"],
            "status": imported["status"],
            "zotero_key": (
                safe(imported["item"].get("key"))
                if imported.get("item")
                else ""
            ),
            "pdf_source": imported["pdf_source"],
        })

    paths["discovery"].write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log(
        f"自动扩展完成：处理 {len(results)} 篇候选。"
    )

    return results


# ============================================================
# 9. AI API
# ============================================================

def ai_headers():
    return {
        "Authorization": (
            f"Bearer {AI_API_KEY}"
        ),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_error(r):
    try:
        d = r.json()
        e = d.get("error")

        if isinstance(e, dict):
            return safe(e.get("message"))

        return safe(e or d.get("message"))
    except Exception:
        return safe(r.text)[:1000]


def normalize_models(data):
    out = []

    for x in (
        data.get("data", [])
        if isinstance(data, dict)
        else []
    ):
        if isinstance(x, str):
            out.append(x)

        elif isinstance(x, dict) and x.get("id"):
            out.append(
                safe(x["id"])
            )

    return out


def model_score(model):
    s = model.lower()

    if any(
        x in s
        for x in (
            "embedding",
            "whisper",
            "tts",
            "audio",
            "moderation",
            "realtime",
            "image-generation",
        )
    ):
        return -999999

    score = 0

    exact = {
        "gpt-5.6-sol": 120000,
        "gpt-5.6": 119000,
        "gpt-5.5": 110000,
        "o3-pro": 100000,
        "o3": 98000,
    }

    score += exact.get(s, 0)

    m = re.search(
        r"gpt[-_]?(\d+(?:\.\d+)?)",
        s,
    )

    if m:
        try:
            score += (
                70000
                + int(float(m.group(1)) * 1000)
            )
        except Exception:
            score += 70000

    for x, n in (
        ("sol", 8000),
        ("reasoning", 5000),
        ("pro", 3000),
        ("claude", 55000),
        ("gemini", 54000),
        ("deepseek", 50000),
        ("qwen", 47000),
        ("mini", -7000),
        ("nano", -10000),
        ("flash", -6000),
        ("lite", -6000),
    ):
        if x in s:
            score += n

    return score or 1000


def discover_ai_routes():
    routes = []

    for base in AI_BASE_URLS:
        try:
            r = SESSION.get(
                base.rstrip("/") + "/models",
                headers=ai_headers(),
                timeout=40,
            )

            models = (
                normalize_models(r.json())
                if r.status_code == 200
                else []
            )

        except Exception:
            models = []

        model = (
            AI_MODEL_OVERRIDE
            or (
                max(models, key=model_score)
                if models
                else None
            )
        )

        routes.append({
            "base": base,
            "model": model,
            "models": models,
        })

        log(
            f"AI route: {base} -> {model or 'API default'}",
            "debug",
        )

    return routes


def parse_responses(data):
    if not isinstance(data, dict):
        return ""

    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    out = []

    for item in data.get("output", []) or []:
        for part in (
            item.get("content", [])
            if isinstance(item, dict)
            else []
        ):
            text = (
                part.get("text")
                if isinstance(part, dict)
                else None
            )

            if isinstance(text, str):
                out.append(text)

    return "\n".join(out).strip()


def parse_chat(data):
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        return "\n".join(
            safe(x.get("text"))
            for x in content
            if isinstance(x, dict)
        ).strip()

    return ""


def post_json(url, payload):
    last = ""

    for attempt in range(NETWORK_RETRIES + 1):
        try:
            r = SESSION.post(
                url,
                headers=ai_headers(),
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if r.status_code >= 500:
                last = api_error(r)
                time.sleep(1.5 * (attempt + 1))
                continue

            return r, ""

        except Exception as e:
            last = str(e)
            time.sleep(1.5 * (attempt + 1))

    return None, last


def reasoning_options(model):
    s = (model or "").lower()

    if "gpt-5.6" in s:
        return [
            {"mode": "pro", "effort": "max"},
            {"mode": "pro", "effort": "xhigh"},
            {"mode": "pro", "effort": "high"},
            {"effort": "max"},
            {"effort": "high"},
            None,
        ]

    return [
        {"effort": "max"},
        {"effort": "xhigh"},
        {"effort": "high"},
        None,
    ]


def call_ai(
    routes,
    prompt,
    images=None,
    accept_text=None,
    max_output_tokens=None,
):
    """
    Call strong AI routes.

    With accept_text, non-empty but invalid responses are rejected and routing
    continues through reasoning variants, chat fallback, and backup routes.
    """
    images = images or []
    errors = []
    rejected = []
    best_rejected_meta = {}

    def accepted(value):
        if not value:
            return False
        if accept_text is None:
            return True
        try:
            return bool(accept_text(value))
        except Exception as e:
            errors.append("candidate validator error: " + safe(e))
            return False

    def remember(value, meta):
        nonlocal best_rejected_meta
        value = safe(value).strip()
        if not value:
            return
        best_rejected_meta = dict(meta)
        preview = re.sub(r"\s+", " ", value).strip()[:AI_REJECTED_PREVIEW_CHARS]
        rejected.append(
            f"{safe(meta.get('base'))} {safe(meta.get('api'))} "
            f"{safe(meta.get('reasoning'))}: {preview}"
        )

    for route in routes:
        base = route["base"]
        model = route["model"]

        # Responses API
        for imgset in ([images, []] if images else [[]]):
            for reasoning in reasoning_options(model):
                if imgset:
                    content = [{"type": "input_text", "text": prompt}]
                    for url in imgset:
                        content.append({
                            "type": "input_image",
                            "image_url": url,
                            "detail": "high",
                        })
                    inp = [{"role": "user", "content": content}]
                else:
                    inp = prompt

                payload = {"input": inp}
                if model:
                    payload["model"] = model
                if reasoning:
                    payload["reasoning"] = reasoning
                if max_output_tokens:
                    payload["max_output_tokens"] = int(max_output_tokens)

                r, err = post_json(base.rstrip("/") + "/responses", payload)

                if not r:
                    errors.append(err)
                    break

                if r.status_code == 200:
                    value = parse_responses(r.json())
                    meta = {
                        "model": model or "API default",
                        "base": base,
                        "api": "responses",
                        "reasoning": reasoning,
                        "vision": bool(imgset),
                    }
                    if value:
                        if accepted(value):
                            return value, None, meta
                        remember(value, meta)
                        continue

                elif r.status_code in (400, 422):
                    # Retry once without output-budget field for compatible proxies.
                    if max_output_tokens and "max_output_tokens" in payload:
                        fallback_payload = dict(payload)
                        fallback_payload.pop("max_output_tokens", None)
                        r2, err2 = post_json(
                            base.rstrip("/") + "/responses",
                            fallback_payload,
                        )
                        if r2 and r2.status_code == 200:
                            value = parse_responses(r2.json())
                            meta = {
                                "model": model or "API default",
                                "base": base,
                                "api": "responses-no-token-budget",
                                "reasoning": reasoning,
                                "vision": bool(imgset),
                            }
                            if value:
                                if accepted(value):
                                    return value, None, meta
                                remember(value, meta)
                                continue
                        if err2:
                            errors.append(err2)
                    continue

                else:
                    errors.append(
                        f"{base}/responses HTTP {r.status_code}: {api_error(r)}"
                    )
                    break

        # Chat fallback
        for imgset in ([images, []] if images else [[]]):
            for effort in ("max", "xhigh", "high", None):
                if imgset:
                    content = [{"type": "text", "text": prompt}]
                    for url in imgset:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": url},
                        })
                else:
                    content = prompt

                payload = {
                    "messages": [{"role": "user", "content": content}]
                }
                if model:
                    payload["model"] = model
                if effort:
                    payload["reasoning_effort"] = effort

                r, err = post_json(
                    base.rstrip("/") + "/chat/completions",
                    payload,
                )

                if not r:
                    errors.append(err)
                    break

                if r.status_code == 200:
                    value = parse_chat(r.json())
                    meta = {
                        "model": model or "API default",
                        "base": base,
                        "api": "chat/completions",
                        "reasoning": effort,
                        "vision": bool(imgset),
                    }
                    if value:
                        if accepted(value):
                            return value, None, meta
                        remember(value, meta)
                        continue

                elif r.status_code in (400, 422):
                    continue

                else:
                    errors.append(
                        f"{base}/chat HTTP {r.status_code}: {api_error(r)}"
                    )
                    break

    if rejected:
        errors.append(
            "Rejected non-empty AI candidates (preview):\n"
            + "\n".join(rejected[-6:])
        )

    return (
        None,
        "\n".join(x for x in errors[-12:] if x),
        best_rejected_meta,
    )

def choose_fast_model(route):
    """Prefer a small/fast model if the endpoint exposes one."""
    if FAST_AI_MODEL_OVERRIDE:
        return FAST_AI_MODEL_OVERRIDE

    models = route.get("models", []) or []

    priorities = (
        "nano",
        "mini",
        "flash",
        "fast",
        "small",
        "lite",
    )

    for token in priorities:
        matches = [
            model for model in models
            if token in safe(model).casefold()
        ]

        if matches:
            return max(matches, key=model_score)

    return route.get("model")


def call_ai_fast(routes, prompt):
    """Fast text-only classification call with no reasoning request."""
    errors = []

    for route in routes:
        base = route["base"]
        model = choose_fast_model(route)

        # Responses API: no reasoning field
        payload = {
            "input": prompt,
        }

        if model:
            payload["model"] = model

        try:
            r = SESSION.post(
                base.rstrip("/") + "/responses",
                headers=ai_headers(),
                json=payload,
                timeout=FAST_AI_TIMEOUT,
            )

            if r.status_code == 200:
                out = parse_responses(r.json())

                if out:
                    return out, None, {
                        "model": model or "API default",
                        "base": base,
                        "api": "responses-fast",
                        "reasoning": None,
                        "vision": False,
                    }

            elif r.status_code not in (400, 404, 405, 422):
                errors.append(
                    f"{base}/responses HTTP {r.status_code}: {api_error(r)}"
                )

        except Exception as e:
            errors.append(f"{base}/responses: {e}")

        # Chat fallback: also no reasoning_effort
        payload = {
            "messages": [{
                "role": "user",
                "content": prompt,
            }]
        }

        if model:
            payload["model"] = model

        try:
            r = SESSION.post(
                base.rstrip("/") + "/chat/completions",
                headers=ai_headers(),
                json=payload,
                timeout=FAST_AI_TIMEOUT,
            )

            if r.status_code == 200:
                out = parse_chat(r.json())

                if out:
                    return out, None, {
                        "model": model or "API default",
                        "base": base,
                        "api": "chat-fast",
                        "reasoning": None,
                        "vision": False,
                    }

            elif r.status_code not in (400, 404, 405, 422):
                errors.append(
                    f"{base}/chat HTTP {r.status_code}: {api_error(r)}"
                )

        except Exception as e:
            errors.append(f"{base}/chat: {e}")

    return None, "\n".join(errors[-6:]), {}


def pdf_attachments(zot, parent_key):
    try:
        children = zot.children(parent_key)
    except Exception:
        return []

    out = []

    for child in children:
        d = child.get("data", {})

        if d.get("itemType") != "attachment":
            continue

        ctype = safe(
            d.get("contentType")
        ).lower()

        name = safe(
            d.get("filename")
            or d.get("title")
            or d.get("path")
        ).lower()

        if (
            ctype == "application/pdf"
            or name.endswith(".pdf")
        ):
            out.append(child)

    return out


def storage_dirs():
    out = []

    if ZOTERO_LOCAL_STORAGE_DIR:
        out.append(
            Path(
                ZOTERO_LOCAL_STORAGE_DIR
            ).expanduser()
        )

    out.append(
        Path.home() / "Zotero" / "storage"
    )

    return out


def local_attachment_path(att):
    d = att.get("data", {})
    key = safe(att.get("key"))
    filename = safe(d.get("filename"))
    path = safe(d.get("path"))

    if path:
        p = Path(path).expanduser()

        if p.is_file():
            return str(p)

    for root in storage_dirs():
        folder = root / key

        if filename:
            p = folder / filename

            if p.is_file():
                return str(p)

        if folder.is_dir():
            pdfs = list(
                folder.glob("*.pdf")
            )

            if pdfs:
                return str(pdfs[0])

    return ""


def download_zotero_pdf(zot, att):
    key = safe(att.get("key"))

    if not key:
        return "", None

    holder = tempfile.TemporaryDirectory(
        prefix="zotero_pdf_"
    )

    filename = safe(
        att.get("data", {}).get("filename")
    )

    if not filename:
        filename = key + ".pdf"

    target = (
        Path(holder.name)
        / filename_safe(filename)
    )

    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")

    try:
        content = zot.file(key)

        if content:
            target.write_bytes(content)

            if target.read_bytes()[:4] == b"%PDF":
                return str(target), holder
    except Exception:
        pass

    holder.cleanup()
    return "", None


def resolve_pdf(zot, item_key):
    attachments = pdf_attachments(
        zot,
        item_key,
    )

    for att in attachments:
        local = local_attachment_path(att)

        if local:
            return (
                local,
                att,
                None,
                "LocalPDF",
            )

    for att in attachments:
        path, holder = download_zotero_pdf(
            zot,
            att,
        )

        if path:
            return (
                path,
                att,
                holder,
                "ZoteroAPI",
            )

    return (
        "",
        attachments[0] if attachments else None,
        None,
        "NoPDF",
    )


def page_score(text, idx, count):
    s = (text or "").casefold()
    score = 0.0

    groups = [
        (10, (
            "experimental setup",
            "apparatus",
            "schematic",
            "dilution refrigerator",
            "pulse tube",
            "mixing chamber",
            "实验装置",
        )),
        (9, (
            "vibration",
            "isolation",
            "mechanical noise",
            "microphonic",
            "隔振",
            "振动",
        )),
        (8, (
            "transfer function",
            "transmissibility",
            "resonance",
            "natural frequency",
            "damping",
            "stiffness",
            "共振",
            "阻尼",
        )),
        (8, (
            "power spectral density",
            "spectral density",
            "psd",
            "asd",
            "accelerometer",
            "displacement",
            "频谱",
        )),
        (7, (
            "figure",
            "fig.",
            "table",
        )),
        (6, (
            "equation",
            "eq.",
            "thermal link",
            "copper braid",
            "bolometer",
            "neutrinoless",
        )),
    ]

    for weight, words in groups:
        n = sum(
            s.count(x)
            for x in words
        )

        score += (
            weight
            * min(n, 6)
        )

    score += min(
        text.count("="),
        8,
    ) * 1.5

    if idx <= 2:
        score += 10

    if idx >= count - 2:
        score += 10

    return score


def scan_pdf(path):
    import pymupdf

    doc = pymupdf.open(path)
    count = doc.page_count
    pages = []
    total = 0

    for idx in range(
        min(count, MAX_SCAN_PAGES)
    ):
        page = doc.load_page(idx)

        try:
            text = (
                page.get_text(
                    "text",
                    sort=True,
                )
                or ""
            ).strip()
        except Exception:
            text = ""

        total += len(text)

        pages.append({
            "index": idx,
            "number": idx + 1,
            "text": text,
            "score": page_score(
                text,
                idx,
                count,
            ),
        })

    doc.close()

    return {
        "count": count,
        "pages": pages,
        "chars": total,
    }


def choose_text_pages(scan):
    pages = scan["pages"]

    if not pages:
        return []

    chosen = set(
        range(min(3, len(pages)))
    )

    chosen.update(
        range(
            max(0, len(pages) - 2),
            len(pages),
        )
    )

    ranked = sorted(
        pages,
        key=lambda x: (
            x["score"],
            len(x["text"]),
        ),
        reverse=True,
    )

    for x in ranked:
        if len(chosen) >= SELECTED_TEXT_PAGES:
            break

        chosen.add(x["index"])

    return [
        x
        for x in pages
        if x["index"] in chosen
    ]


def build_pdf_text(pages):
    out = []
    used = 0

    for x in pages:
        if not x["text"]:
            continue

        header = (
            f"\n\n===== "
            f"[PDF p.{x['number']}] "
            f"=====\n"
        )

        room = (
            MAX_INPUT_CHARS
            - used
            - len(header)
        )

        if room <= 0:
            break

        part = x["text"][:room]
        out.append(header + part)
        used += len(header) + len(part)

    return "".join(out)


def choose_image_pages(scan):
    ranked = sorted(
        scan["pages"],
        key=lambda x: (
            x["score"],
            len(x["text"]),
        ),
        reverse=True,
    )

    return sorted(
        x["index"]
        for x in ranked[
            :MAX_VISION_PAGES
        ]
    )


def render_images(path, indices):
    if not ENABLE_VISION:
        return [], []

    import pymupdf

    doc = pymupdf.open(path)
    urls = []
    nums = []

    for idx in indices:
        try:
            pix = doc.load_page(
                idx
            ).get_pixmap(
                dpi=VISION_DPI,
                alpha=False,
            )

            raw = pix.tobytes(
                "jpeg"
            )

            urls.append(
                "data:image/jpeg;base64,"
                + base64.b64encode(
                    raw
                ).decode("ascii")
            )

            nums.append(idx + 1)

        except Exception:
            pass

    doc.close()

    return urls, nums


def indexed_fulltext(zot, att):
    if not att:
        return ""

    try:
        d = zot.fulltext_item(
            safe(att.get("key"))
        )

        return safe(
            d.get("content")
            if isinstance(d, dict)
            else ""
        )[:MAX_INPUT_CHARS]
    except Exception:
        return ""


# ============================================================
# 11. 深度分析提示词
# ============================================================

def evidence_prompt(
    title,
    authors,
    year,
    doi,
    source,
    text_pages,
    image_pages,
):
    return f"""
你是一名低温实验、机械振动、精密测量与低温探测器专家。

论文：
标题：{title}
作者：{authors}
年份：{year}
DOI：{doi}

已读取文本页：{text_pages}
已读取图片页：{image_pages}

【论文证据】
{source[:MAX_INPUT_CHARS]}
【证据结束】

请生成一份严格、简洁的中文证据底稿。

要求：
- 论文事实尽量标注 [PDF p.N]。
- 看不清的图、公式、数字绝对不要猜。
- 区分作者实际搭建、实际测量和作者推断。
- 重点关注 pulse tube 的运行原理、regenerator / inertance / reservoir、
  pressure/mass-flow phase、rotary valve / compressor、cold-head 周期力、
  机械传播路径、隔振、PSD/ASD、传递函数、共振、热连接、线缆、软管、
  exchange gas、phase cancellation、结构旁路、mixing chamber 和 detector stage。

# 核心问题
# 振动来源与传播路径
# 实验装置
# 隔振方案
# 关键公式
# 关键图表
# 关键数据
# 热学与机械约束
# 局限性

最后写：
**证据可靠度：高 / 中 / 低**
""".strip()

def final_prompt(
    title,
    authors,
    year,
    doi,
    source,
    evidence,
):
    return rf"""
请用中文撰写技术性强、适合科研设计直接使用的深度分析。
目标读者正在设计用于敏感低温探测器和 0νββ 实验的
pulse-tube 干式稀释制冷机隔振系统。

论文：
标题：{title}
作者：{authors}
年份：{year}
DOI：{doi}

【证据底稿】
{evidence}

【选取的论文原文】
{source[:MAX_INPUT_CHARS]}

要求：
- 正文必须使用中文；论文题目、器件名、标准术语可保留英文。
- 技术上简洁、明确、可执行。
- 论文事实尽量标注 [PDF p.N]。
- 不得编造论文没有提供的数字或结论。
- 补充的通用理论必须标明：
  【通用理论补充，不是论文原文】
- 如果论文没有证明适用于 0νββ，不得写成已经验证。
- 所有数学变量、希腊字母和公式必须使用 KaTeX 兼容 LaTeX。
- 行内数学量必须写在 `$...$` 中，例如：
  `$f_n$`、`$\omega$`、`$\zeta$`、`$T(f)$`。
- 独立公式必须放在 `$$...$$` 块中。
- 单位在公式中尽量使用 `\mathrm{{}}`。
- 不使用普通 ASCII 公式替代数学公式。

目标长度：
{TARGET_ANALYSIS_CHARS}

# 一句话结论
用一小段说明论文做了什么、最值得借鉴什么。

# 问题定义
说明振动源、传播路径、限制因素和评价指标。
如果论文涉及 pulse tube，必须进一步说明：
- 制冷循环中压力/质量流振荡来自哪里；
- 哪些部件本身在运动，哪些冷端没有滑动机械件但仍产生周期力；
- 基频、谐波、cold-head/cold-stage 反作用力及结构共振如何形成；
- 明确区分“振动源”“传播路径”“敏感接收端”。

## Pulse Tube 运行原理与振动产生机制
若论文提供证据，解释 regenerator、pulse tube、orifice/inertance/reservoir、
rotary valve/compressor 和压力-质量流相位关系。
若论文不讲原理，可以给出【通用理论补充，不是论文原文】，但不能冒充论文结论。

# 实验装置
解释从振动源到敏感级的机械链路。
至少检查这些潜在路径是否存在：
compressor / motor -> helium hose -> rotary valve -> 300 K flange -> cold head ->
40 K / 4 K stage -> thermal strap -> still / mixing chamber -> detector。
同时检查独立的 floor/frame、vacuum bellows、pumping line、wiring/cable 旁路。

## 传播路径清单
按 Source -> Path -> Receiver 列出论文明确证明和仅推测的路径。

# 隔振方案
解释论文实际采用/研究的隔振方法及其物理机制。
把方法明确分成：
1. 源端减振：remote motor/valve、phase cancellation、自抵消；
2. 传播路径隔离：bellows/flexible hose、独立框架、软连接；
3. 冷端热-机械解耦：copper braid、flexible strap、exchange gas/non-contact link；
4. 负载端隔振：spring/pendulum/multi-stage/QZS/negative stiffness/active isolation；
5. 电学微音控制：cable clamping、低 triboelectric 线缆、避免线缆机械旁路。

如果论文没有隔振方案，明确写“本文未研究隔振”，然后只在
【通用理论补充，不是论文原文】中说明它对隔振设计的启示。

# 理论
必要时可补充：

【通用理论补充，不是论文原文】

$$
f_n = \frac{{1}}{{2\pi}}\sqrt{{\frac{{k}}{{m}}}}
$$

$$
\delta = \frac{{mg}}{{k}}
$$

$$
r = \frac{{f}}{{f_n}}
$$

$$
T =
\sqrt{{
\frac{{
1 + (2\zeta r)^2
}}{{
(1-r^2)^2 + (2\zeta r)^2
}}
}}
$$

# 关键公式
解释变量含义、单位、物理意义和设计用途。

# 关键图表
分析坐标轴、峰值、共振、衰减、有效频带和恶化区域。

# 关键数据

| 指标 | 数值 | 条件 | 页码 | 对设计的用途 |
|---|---:|---|---|---|

# 对低温系统的意义
重点评价：
- Pulse tube / rotary valve / cold head / mixing chamber / detector stage
- thermal strap / copper braid / exchange gas / non-contact thermal coupling
- cables / hoses / pumping lines
- mechanical bypass
- lateral / torsional modes
- cooldown / thermal contraction
- PT 基频及谐波是否撞上结构模态
- 机械噪声是否转化为 microphonic / triboelectric electrical noise

# 可行性
- 技术可行性：高 / 中 / 低
- 短期验证难度：高 / 中 / 低
- 直接照搬风险：高 / 中 / 低
- 对本课题价值：高 / 中 / 低

## 可直接借鉴
列出不依赖特定设备、最值得直接试的设计或测试方法。

## 必须重新验证
列出对质量、弹簧刚度、热负载、温区、尺寸、固有频率、材料和安装方式
高度敏感的参数，不能照抄论文数值。

## 推荐安装层级
明确该方法最适合 source-side、300 K、40 K、4 K、mixing chamber、
detector stage、cable/hose 还是 floor/frame。

# 下一步
按优先级给出 5–8 个可以真正执行的动作。
至少包含：
- 一个不用改结构就能做的诊断；
- 一个传递路径 A/B test；
- 一个可计算的隔振参数；
- 一个低温热学风险检查；
- 一个决定“是否值得加工/采购”的成功判据。

最后严格使用：

**等级：A / B / C / D**

**建议：** 用一句中文给出最优先的实际行动。
""".strip()


def fallback_analysis_source(item):
    """
    Recover source text for an item that has no local PDF/full text/abstract.

    Prefer an OpenAlex abstract. If even that is unavailable, return explicit
    bibliographic metadata so the model can create an evidence-limited analysis
    without inventing paper-specific results.
    """
    data = item.get(
        "data",
        {},
    )

    try:
        work = openalex_work_for_zotero_item(
            item
        )
    except Exception:
        work = None

    if work:
        abstract = work_abstract(
            work
        )

        if abstract:
            return (
                "[OpenAlex abstract]\n"
                + abstract,
                "OpenAlex abstract",
            )

    fields = [
        ("Title", safe(data.get("title"))),
        ("Authors", authors_from_item(item)),
        ("Year", year_from_item(item)),
        ("DOI", norm_doi(data.get("DOI"))),
        ("Publication", safe(data.get("publicationTitle"))),
        ("URL", safe(data.get("url"))),
        ("Extra", safe(data.get("extra"))),
    ]

    metadata = "\n".join(
        f"{name}: {value}"
        for name, value in fields
        if value
    )

    if metadata:
        return (
            "[Bibliographic metadata only]\n"
            "No PDF/full text/abstract was available. "
            "Do not infer paper-specific experiments, numbers, figures or conclusions.\n"
            + metadata,
            "Bibliographic metadata",
        )

    return "", ""


def acquire_analysis_material(
    zot,
    item,
):
    """Read the best available evidence for one bibliographic item."""
    data = item.get(
        "data",
        {},
    )

    item_key = safe(
        item.get("key")
    )

    abstract = safe(
        data.get(
            "abstractNote"
        )
    )

    pdf_path, att, holder, pdf_source = resolve_pdf(
        zot,
        item_key,
    )

    attachment_key = (
        safe(att.get("key"))
        if att
        else ""
    )

    source = ""
    text_source = ""
    text_pages = ""
    image_pages = ""
    images = []

    if pdf_path:
        try:
            scan = scan_pdf(
                pdf_path
            )

            pages = choose_text_pages(
                scan
            )

            text_pages = ", ".join(
                str(x["number"])
                for x in pages
                if x["text"]
            )

            pdf_text = build_pdf_text(
                pages
            )

            if (
                scan["chars"] >= MIN_PDF_TEXT_CHARS
                and pdf_text
            ):
                source = pdf_text
                text_source = "PDF"

                if abstract:
                    source = (
                        "[Abstract]\n"
                        + abstract
                        + "\n\n"
                        + source
                    )

            elif abstract:
                source = (
                    "[Abstract]\n"
                    + abstract
                )
                text_source = (
                    "Abstract + images"
                )

            idxs = choose_image_pages(
                scan
            )

            images, nums = render_images(
                pdf_path,
                idxs,
            )

            image_pages = ", ".join(
                str(x)
                for x in nums
            )

        except Exception:
            pass

    if (
        not source
        and att
    ):
        fulltext = indexed_fulltext(
            zot,
            att,
        )

        if fulltext:
            source = fulltext
            text_source = (
                "Zotero full text"
            )

    if (
        not source
        and abstract
    ):
        source = abstract
        text_source = "Abstract"

    if not source:
        source, text_source = (
            fallback_analysis_source(
                item
            )
        )

    return {
        "source": source,
        "text_source": text_source,
        "text_pages": text_pages,
        "image_pages": image_pages,
        "images": images,
        "attachment_key": attachment_key,
        "pdf_source": pdf_source,
        "holder": holder,
    }


def deep_analyze(
    routes,
    title,
    authors,
    year,
    doi,
    source,
    text_pages,
    images,
    image_pages,
    stage_callback=None,
):
    evidence = ""

    def stage(value):
        if stage_callback:
            try:
                stage_callback(value)
            except Exception:
                pass

    if DEEP_TWO_PASS:
        stage("Evidence analysis")
        evidence, evidence_error, _ = call_ai(
            routes,
            evidence_prompt(
                title,
                authors,
                year,
                doi,
                source,
                text_pages,
                image_pages,
            ),
            images,
            max_output_tokens=6000,
        )

        if not evidence:
            evidence = (
                "Evidence pass failed. Use the source text and images directly. "
                "Do not guess unreadable content."
            )
            if evidence_error:
                evidence += "\nEvidence API error: " + evidence_error[:1200]

    # Balanced one-pass mode: send only a few highest-value PDF pages
    # directly to the strong deep-analysis call.
    final_images = (
        images
        if (
            not DEEP_TWO_PASS
            and ENABLE_VISION
        )
        else []
    )

    stage("Deep analysis")

    analysis, error, meta = call_ai(
        routes,
        final_prompt(
            title,
            authors,
            year,
            doi,
            source,
            evidence,
        ),
        final_images,
        max_output_tokens=DEEP_MAX_OUTPUT_TOKENS,
    )

    require_pdf_citation = bool(text_pages)

    if analysis:
        report = deep_analysis_quality_report(
            analysis,
            require_pdf_citation=require_pdf_citation,
        )
        if report["valid"]:
            return analysis, error, meta, evidence
    else:
        report = {
            "issues": [
                error or "empty model response"
            ]
        }

    previous = analysis or ""
    combined_errors = []
    if error:
        combined_errors.append(error)

    for repair_no in range(1, DEEP_QUALITY_RETRIES + 1):
        stage(f"Quality regeneration {repair_no}")

        if previous:
            issues = deep_analysis_quality_report(
                previous,
                require_pdf_citation=require_pdf_citation,
            )["issues"]
        else:
            issues = report.get("issues", [])

        def accept_repaired(candidate):
            return deep_analysis_quality_report(
                candidate,
                require_pdf_citation=require_pdf_citation,
            )["valid"]

        repaired, repair_error, repair_meta = call_ai(
            routes,
            deep_quality_repair_prompt(
                title,
                authors,
                year,
                doi,
                source,
                evidence,
                previous,
                issues,
            ),
            [],
            accept_text=accept_repaired,
            max_output_tokens=DEEP_MAX_OUTPUT_TOKENS,
        )

        if repaired:
            return (
                repaired,
                repair_error,
                repair_meta or meta,
                evidence,
            )

        if repair_error:
            combined_errors.append(repair_error)

    final_report = deep_analysis_quality_report(
        previous,
        require_pdf_citation=require_pdf_citation,
    )

    failure = (
        "\n".join(x for x in combined_errors[-4:] if x)
        + "\nDeep analysis failed quality validation: "
        + "; ".join(final_report.get("issues", []))
    ).strip()

    return None, failure, meta, evidence

def authors_from_item(item):
    out = []

    for c in (
        item.get("data", {}).get("creators", [])
        or []
    ):
        name = safe(c.get("name"))

        if not name:
            name = " ".join(
                x
                for x in (
                    safe(c.get("firstName")),
                    safe(c.get("lastName")),
                )
                if x
            )

        if name:
            out.append(name)

    return "; ".join(out)


def year_from_item(item):
    date = safe(
        item.get("data", {}).get("date")
    )

    m = re.search(
        r"\b(?:19|20|21)\d{2}\b",
        date,
    )

    return (
        m.group(0)
        if m
        else date[:20]
    )


def pseudo_work_from_item(item):
    d = item.get("data", {})

    return {
        "title": safe(d.get("title")),
        "abstract_inverted_index": {},
        "primary_location": {
            "source": {
                "display_name": safe(
                    d.get("publicationTitle")
                )
            }
        },
        "_local_abstract": safe(
            d.get("abstractNote")
        ),
    }


def work_text_with_local(work):
    return (
        work_text(work)
        + " "
        + safe(work.get("_local_abstract"))
    ).casefold()


def classify_existing_item(item, oa_work=None):
    work = oa_work or pseudo_work_from_item(
        item
    )

    if not oa_work:
        # 让分类器看到 Zotero 摘要
        original = work_text
        text = work_text_with_local(work)
        scores = {}

        for category, words in CATEGORY_RULES.items():
            scores[category] = sum(
                1
                for word in words
                if word.casefold() in text
            )

        category = max(
            scores,
            key=scores.get,
        )

        if scores[category] == 0:
            category = "10_相关背景"

        tags = {
            "0νββ-文献库",
            category.split("_", 1)[-1],
        }

        return category, sorted(tags)

    category, tags = classify_work(
        oa_work
    )

    tags = set(tags)
    tags.discard("AI-自动发现")
    tags.add("0νββ-文献库")

    return category, sorted(tags)


def _legacy_classify_and_tag_collection(
    zot,
    papers,
    target_key,
    category_map,
):
    log("Classify and tag", "debug")

    for paper in progress_iter(
        papers,
        description="Classify papers",
        unit="papers",
    ):
        item = paper["item"]

        try:
            oa = openalex_work_for_zotero_item(
                item
            )
        except Exception:
            oa = None

        category, tags = (
            classify_existing_item(
                item,
                oa,
            )
        )

        if AUTO_ADD_TAGS:
            try:
                zot.add_tags(
                    item,
                    *tags,
                )
            except Exception:
                pass

        ckey = category_map.get(
            category
        )

        if ckey:
            add_item_to_collection(
                zot,
                ckey,
                item,
            )


def build_child_index(zot):
    """Fetch all items once and index child items by parentItem."""
    index = {}

    try:
        items = zot.everything(zot.items())
    except Exception:
        items = []

        for parent in zot.everything(zot.top()):
            pkey = safe(parent.get("key"))

            try:
                items.extend(
                    zot.children(pkey)
                )
            except Exception:
                pass

    for item in items:
        data = item.get("data", {})
        parent = safe(data.get("parentItem"))

        if parent:
            index.setdefault(
                parent,
                [],
            ).append(item)

    return index




def _is_zotero_conflict(error):
    """Detect Zotero write-version conflicts."""
    value = safe(error).casefold()

    return (
        "code: 412" in value
        or "code: 409" in value
        or "precondition" in value
        or "library has been modified" in value
        or (
            "if-unmodified-since-version" in value
            and "version" in value
        )
        or (
            "version" in value
            and "modified" in value
        )
    )


def _is_zotero_missing(error):
    value = safe(error).casefold()

    return (
        "code: 404" in value
        or "not found" in value
    )


def delete_item_latest(
    zot,
    item_key,
    retries=None,
):
    """Delete with the current library version and retry conflicts."""
    retries = (
        DUPLICATE_DELETE_RETRIES
        if retries is None
        else retries
    )

    last_error = None

    for attempt in range(max(1, retries)):
        try:
            fresh = zot.item(item_key)

            library_version = (
                zot.last_modified_version()
            )

            zot.delete_item(
                [fresh],
                last_modified=library_version,
            )

            return True, ""

        except Exception as e:
            last_error = e

            if _is_zotero_missing(e):
                return True, ""

            if (
                _is_zotero_conflict(e)
                and attempt + 1 < retries
            ):
                time.sleep(
                    DUPLICATE_RETRY_WAIT * (attempt + 1)
                )
                continue

            break

    return False, safe(last_error)


def _parse_invalid_item_keys(error):
    """Extract Pyzotero's local validation field names."""
    value = safe(error)

    match = re.search(
        r"Invalid keys present in item\s+\d+\s*:\s*(.+)",
        value,
        flags=re.I,
    )

    if not match:
        return set()

    tail = match.group(1).strip()

    # Usually this is "lastRead" or "lastRead, someOtherKey".
    parts = re.split(
        r"\s*,\s*|\s*;\s*",
        tail,
    )

    keys = set()

    for part in parts:
        key = part.strip().strip("'\"[](){} ")

        if key:
            keys.add(key)

    return keys


def _sanitize_item_for_patch(
    item,
    extra_keys=None,
):
    """Remove response-only fields while preserving item/version data."""
    data = item.get(
        "data",
        {},
    )

    remove = set(
        NONWRITABLE_ITEM_DATA_KEYS
    )

    if extra_keys:
        remove.update(
            extra_keys
        )

    for key in remove:
        data.pop(
            key,
            None,
        )

    # If an invalid response-only field ever appears at the top level,
    # remove it there as well. Keep key/version/library/links/meta/data.
    for key in remove:
        if key not in {
            "key",
            "version",
            "library",
            "links",
            "meta",
            "data",
        }:
            item.pop(
                key,
                None,
            )

    return item


def update_item_latest(
    zot,
    item_key,
    mutate,
    retries=None,
):
    """Refetch, sanitize and PATCH using the item's own current version."""
    retries = (
        DUPLICATE_WRITE_RETRIES
        if retries is None
        else retries
    )

    last_error = None
    dynamically_invalid = set()

    for attempt in range(
        max(1, retries)
    ):
        try:
            fresh = zot.item(
                item_key
            )

            mutate(
                fresh
            )

            _sanitize_item_for_patch(
                fresh,
                dynamically_invalid,
            )

            # Single-item PATCH:
            # Pyzotero uses fresh["version"] as the conditional version.
            ok = zot.update_item(
                fresh
            )

            if ok:
                return (
                    True,
                    zot.item(item_key),
                    "",
                )

            last_error = RuntimeError(
                "update_item returned False"
            )

        except Exception as e:
            last_error = e

            # Pyzotero can reject response-only fields before making an
            # HTTP request. Learn those fields and retry automatically.
            invalid_keys = (
                _parse_invalid_item_keys(
                    e
                )
            )

            new_invalid = (
                invalid_keys
                - dynamically_invalid
            )

            if new_invalid:
                dynamically_invalid.update(
                    new_invalid
                )

                log(
                    "Retrying item write after removing "
                    + ", ".join(
                        sorted(new_invalid)
                    ),
                    "debug",
                )

                if attempt + 1 < retries:
                    continue

            if (
                _is_zotero_conflict(e)
                and attempt + 1 < retries
            ):
                time.sleep(
                    DUPLICATE_RETRY_WAIT
                    * (attempt + 1)
                )
                continue

            break

    return (
        False,
        None,
        safe(last_error),
    )



def _dedupe_item_key(item):
    return safe(
        item.get("key")
        or item.get(
            "data",
            {},
        ).get("key")
    )


def _dedupe_paper_items(zot):
    """Top-level bibliographic items eligible for duplicate cleanup."""
    items = zot.everything(
        zot.top()
    )

    return [
        item
        for item in items
        if safe(
            item.get(
                "data",
                {},
            ).get("itemType")
        ) in PAPER_ITEM_TYPES
    ]


def _duplicate_groups(items):
    """Group items when DOI or normalized title matches exactly."""
    if not items:
        return []

    parent = list(
        range(len(items))
    )

    def find(x):
        while parent[x] != x:
            parent[x] = parent[
                parent[x]
            ]
            x = parent[x]
        return x

    def union(a, b):
        ra = find(a)
        rb = find(b)

        if ra != rb:
            parent[rb] = ra

    doi_map = {}
    title_map = {}

    for i, item in enumerate(items):
        data = item.get(
            "data",
            {},
        )

        doi = norm_doi(
            data.get("DOI")
        )

        title = norm_title(
            data.get("title")
        )

        if doi:
            if doi in doi_map:
                union(
                    i,
                    doi_map[doi],
                )
            else:
                doi_map[doi] = i

        if (
            title
            and len(title)
            >= DUPLICATE_TITLE_MIN_CHARS
        ):
            if title in title_map:
                union(
                    i,
                    title_map[title],
                )
            else:
                title_map[title] = i

    groups = {}

    for i, item in enumerate(items):
        root = find(i)

        groups.setdefault(
            root,
            [],
        ).append(item)

    return [
        group
        for group in groups.values()
        if len(group) > 1
    ]


def _child_kind_signature(child):
    """Signature used only to avoid moving an exact duplicate child."""
    data = child.get(
        "data",
        {},
    )

    item_type = safe(
        data.get("itemType")
    )

    if item_type == "note":
        plain = note_plain_text(
            data.get("note")
        )

        return (
            "note",
            re.sub(
                r"\s+",
                " ",
                plain,
            ).strip().casefold(),
        )

    if item_type == "attachment":
        md5 = safe(
            data.get("md5")
        )

        if md5:
            return (
                "attachment-md5",
                md5.casefold(),
            )

    return (
        item_type,
        _dedupe_item_key(child),
    )


def _item_quality_score(
    item,
    children,
):
    """Prefer the duplicate containing the richest useful data."""
    data = item.get(
        "data",
        {},
    )

    score = 0

    pdf_count = 0
    deep_count = 0
    summary_count = 0
    note_count = 0

    for child in children:
        cdata = child.get(
            "data",
            {},
        )

        ctype = safe(
            cdata.get("itemType")
        )

        if ctype == "attachment":
            content_type = safe(
                cdata.get("contentType")
            ).casefold()

            filename = safe(
                cdata.get("filename")
            ).casefold()

            if (
                "pdf" in content_type
                or filename.endswith(".pdf")
            ):
                pdf_count += 1

        elif ctype == "note":
            note_count += 1
            note_html = safe(
                cdata.get("note")
            )

            if is_deep_analysis_note(
                note_html
            ):
                deep_count += 1

            if is_ai_summary_note(
                note_html
            ):
                summary_count += 1

    score += pdf_count * 120
    score += deep_count * 100
    score += summary_count * 45
    score += note_count * 8

    important_fields = (
        "DOI",
        "abstractNote",
        "publicationTitle",
        "date",
        "url",
        "volume",
        "issue",
        "pages",
        "language",
    )

    for field in important_fields:
        if safe(
            data.get(field)
        ):
            score += 4

    creators = data.get(
        "creators",
        [],
    ) or []

    score += min(
        len(creators),
        8,
    ) * 2

    # Slight preference for an older/stable record when content is equal.
    try:
        score += max(
            0,
            10_000_000
            - int(
                item.get(
                    "version",
                    0,
                )
            )
        ) * 1e-9
    except Exception:
        pass

    return score


def _merge_parent_metadata(
    zot,
    keeper,
    duplicate,
):
    """Merge useful metadata/tags/Collections with conflict retries."""
    keeper_key = _dedupe_item_key(
        keeper
    )

    ddata = duplicate.get(
        "data",
        {},
    )

    def mutate(fresh):
        kdata = fresh.get(
            "data",
            {},
        )

        fields = (
            "DOI",
            "abstractNote",
            "publicationTitle",
            "date",
            "url",
            "volume",
            "issue",
            "pages",
            "language",
            "ISSN",
        )

        for field in fields:
            if (
                not safe(
                    kdata.get(field)
                )
                and safe(
                    ddata.get(field)
                )
            ):
                kdata[field] = ddata.get(
                    field
                )

        if (
            not kdata.get("creators")
            and ddata.get("creators")
        ):
            kdata["creators"] = ddata[
                "creators"
            ]

        keeper_collections = set(
            kdata.get(
                "collections",
                [],
            )
            or []
        )

        duplicate_collections = set(
            ddata.get(
                "collections",
                [],
            )
            or []
        )

        kdata["collections"] = sorted(
            keeper_collections
            | duplicate_collections
        )

        keeper_tags = {
            safe(tag.get("tag"))
            for tag in (
                kdata.get(
                    "tags",
                    [],
                )
                or []
            )
            if isinstance(
                tag,
                dict,
            )
            and safe(
                tag.get("tag")
            )
        }

        for tag in (
            ddata.get(
                "tags",
                [],
            )
            or []
        ):
            if not isinstance(
                tag,
                dict,
            ):
                continue

            value = safe(
                tag.get("tag")
            )

            if (
                value
                and value not in keeper_tags
            ):
                kdata.setdefault(
                    "tags",
                    [],
                ).append(
                    {"tag": value}
                )
                keeper_tags.add(
                    value
                )

    ok, updated, error = update_item_latest(
        zot,
        keeper_key,
        mutate,
    )

    if not ok:
        raise RuntimeError(
            error
            or "keeper update failed"
        )

    return updated

def _move_duplicate_children(
    zot,
    keeper_key,
    keeper_children,
    duplicate_children,
):
    """Move unique notes/PDFs; retry version conflicts automatically."""
    existing_signatures = {
        _child_kind_signature(
            child
        )
        for child in keeper_children
    }

    moved = 0
    deleted_exact = 0
    failed = 0

    for child in duplicate_children:
        child_key = _dedupe_item_key(
            child
        )

        if not child_key:
            continue

        signature = _child_kind_signature(
            child
        )

        # Exact duplicate child: safely remove the redundant child.
        if signature in existing_signatures:
            ok, error = delete_item_latest(
                zot,
                child_key,
            )

            if ok:
                deleted_exact += 1
            else:
                failed += 1
                log(
                    f"Duplicate child delete failed: "
                    f"{child_key} | {error}",
                    "warn",
                )

            continue

        if not MOVE_DUPLICATE_CHILDREN:
            failed += 1
            continue

        def mutate(fresh_child):
            fresh_child[
                "data"
            ][
                "parentItem"
            ] = keeper_key

        ok, _, error = update_item_latest(
            zot,
            child_key,
            mutate,
        )

        if ok:
            moved += 1
            existing_signatures.add(
                signature
            )
        else:
            failed += 1
            log(
                f"Duplicate child move failed: "
                f"{child_key} | {error}",
                "warn",
            )

    return moved, deleted_exact, failed

def deduplicate_library(zot):
    """Safely consolidate and delete duplicate top-level paper entries."""
    if not AUTO_DELETE_DUPLICATES:
        return {
            "groups": 0,
            "deleted": 0,
            "children_moved": 0,
            "children_deleted": 0,
            "failed": 0,
        }

    items = _dedupe_paper_items(
        zot
    )

    groups = _duplicate_groups(
        items
    )

    if not groups:
        return {
            "groups": 0,
            "deleted": 0,
            "children_moved": 0,
            "children_deleted": 0,
            "failed": 0,
        }

    console.print()
    console.rule(
        "Duplicate cleanup",
        style="dim",
    )

    child_index = build_child_index(
        zot
    )

    stats = {
        "groups": len(groups),
        "deleted": 0,
        "children_moved": 0,
        "children_deleted": 0,
        "failed": 0,
    }

    for group in progress_iter(
        groups,
        description="Merge duplicates",
        unit="groups",
    ):
        scored = sorted(
            group,
            key=lambda item: _item_quality_score(
                item,
                child_index.get(
                    _dedupe_item_key(
                        item
                    ),
                    [],
                ),
            ),
            reverse=True,
        )

        keeper = scored[0]
        keeper_key = _dedupe_item_key(
            keeper
        )

        keeper_children = list(
            child_index.get(
                keeper_key,
                [],
            )
        )

        for duplicate in scored[1:]:
            duplicate_key = _dedupe_item_key(
                duplicate
            )

            if not duplicate_key:
                continue

            try:
                keeper = _merge_parent_metadata(
                    zot,
                    keeper,
                    duplicate,
                )

                duplicate_children = list(
                    child_index.get(
                        duplicate_key,
                        [],
                    )
                )

                moved, deleted_exact, child_failed = (
                    _move_duplicate_children(
                        zot,
                        keeper_key,
                        keeper_children,
                        duplicate_children,
                    )
                )

                stats[
                    "children_moved"
                ] += moved
                stats[
                    "children_deleted"
                ] += deleted_exact

                if child_failed:
                    stats["failed"] += 1
                    log(
                        f"Duplicate kept because "
                        f"{child_failed} child item(s) could not be moved: "
                        f"{safe(duplicate.get('data', {}).get('title'))[:60]}",
                        "warn",
                    )
                    continue

                deleted_ok, delete_error = delete_item_latest(
                    zot,
                    duplicate_key,
                )

                if not deleted_ok:
                    stats["failed"] += 1

                    log(
                        f"Duplicate delete failed after retries: "
                        f"{safe(duplicate.get('data', {}).get('title'))[:60]} "
                        f"| {delete_error}",
                        "warn",
                    )
                    continue

                stats[
                    "deleted"
                ] += 1

                # Refresh keeper children for the next duplicate in this group.
                try:
                    keeper_children = zot.children(
                        keeper_key
                    )
                except Exception:
                    pass

            except Exception as e:
                stats["failed"] += 1

                log(
                    f"Duplicate cleanup failed: "
                    f"{safe(duplicate.get('data', {}).get('title'))[:60]} | {e}",
                    "warn",
                )

    if VERIFY_DUPLICATE_DELETE:
        remaining = _duplicate_groups(
            _dedupe_paper_items(
                zot
            )
        )

        if remaining:
            log(
                f"Duplicate groups remaining: {len(remaining)}",
                "warn",
            )
        else:
            log(
                "Duplicate check: clean",
                "ok",
            )

    return stats


def note_plain_text(note_html):
    """Convert Zotero note HTML to compact plain text."""
    value = safe(note_html)

    value = re.sub(
        r"<br\s*/?>",
        "\n",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"</(?:p|div|h1|h2|h3|li|pre)>",
        "\n",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )
    value = html.unescape(value)
    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )
    value = re.sub(
        r"\n\s*\n+",
        "\n",
        value,
    )

    return value.strip()


def _first_note_line(note_html):
    """Return the first meaningful plain-text line from a Zotero note."""
    plain = note_plain_text(
        note_html
    )

    for line in plain.splitlines():
        line = line.strip()

        if line:
            return line

    return ""


def generated_note_kind(note_html):
    """
    Recognize only current/legacy generated summary/deep notes.

    Marker-based notes are recognized even when the visible heading is missing.
    A nameless legacy deep note may also be recognized from several old
    generated metadata fields. Ordinary hand-written notes are left alone.
    """
    value = safe(
        note_html
    )

    if (
        DEEP_NOTE_MARKER in value
        or AI_NOTE_MARKER in value
    ):
        return "deep"

    if SUMMARY_NOTE_MARKER in value:
        return "summary"

    first = _first_note_line(
        value
    ).casefold()

    deep_titles = {
        safe(title).casefold()
        for title in (
            (DEEP_NOTE_TITLE,)
            + tuple(
                LEGACY_DEEP_NOTE_TITLES
            )
        )
    }

    summary_titles = {
        safe(title).casefold()
        for title in (
            (SUMMARY_NOTE_TITLE,)
            + tuple(
                LEGACY_SUMMARY_NOTE_TITLES
            )
        )
    }

    if first in deep_titles:
        return "deep"

    if first in summary_titles:
        return "summary"

    # Conservative fallback for old generated deep notes whose heading was
    # accidentally missing. Require several program-specific metadata labels.
    plain = note_plain_text(
        value
    ).casefold()

    deep_metadata_tokens = (
        "generated:",
        "source:",
        "text pages:",
        "image pages:",
        "model:",
        "api:",
        "生成时间：",
        "来源：",
        "文本页：",
        "图像页：",
        "模型：",
        "接口：",
    )

    metadata_hits = sum(
        token in plain
        for token in deep_metadata_tokens
    )

    if metadata_hits >= 3:
        return "deep"

    return ""

def is_deep_analysis_note(note_html):
    """Recognize current/legacy generated deep-analysis notes."""
    return generated_note_kind(
        note_html
    ) == "deep"


def is_ai_summary_note(note_html):
    """Recognize current/legacy generated summary notes."""
    return generated_note_kind(
        note_html
    ) == "summary"


def generated_note_has_title(
    note_html,
    expected_title,
):
    """Check whether the first visible note line is exactly the required title."""
    return (
        _first_note_line(
            note_html
        ).strip().casefold()
        == safe(
            expected_title
        ).strip().casefold()
    )


def ensure_generated_note_title_html(
    note_html,
    expected_title,
    marker,
):
    """Guarantee a visible h1 title and current generated-note marker."""
    value = replace_note_heading(
        note_html,
        expected_title,
        marker,
    )

    # replace_note_heading() handles missing/legacy h1 headings. This second
    # guard also handles malformed historical HTML whose first visible line is
    # still not the requested title.
    if not generated_note_has_title(
        value,
        expected_title,
    ):
        value = (
            f"<h1>{html.escape(expected_title)}</h1>\n"
            + value
        )

    return value


def replace_note_heading(note_html, title, marker):
    """Standardize generated note heading and marker."""
    value = safe(
        note_html
    )

    heading = (
        "<h1>"
        + html.escape(title)
        + "</h1>"
    )

    if re.search(
        r"<h1\b[^>]*>.*?</h1>",
        value,
        flags=re.I | re.S,
    ):
        value = re.sub(
            r"<h1\b[^>]*>.*?</h1>",
            heading,
            value,
            count=1,
            flags=re.I | re.S,
        )
    else:
        value = (
            heading
            + "\n"
            + value
        )

    if marker not in value:
        value = (
            f'<div data-ai-note-id="{marker}">'
            + value
            + "</div>"
        )

    return value


def _localize_deep_note_metadata(note_html):
    """Convert generated-note metadata labels/values to Chinese."""
    value = safe(
        note_html
    )

    replacements = (
        ("Generated:", "生成时间："),
        ("Source:", "来源："),
        ("Text pages:", "文本页："),
        ("Image pages:", "图像页："),
        ("Model:", "模型："),
        ("API:", "接口："),
        ("Abstract + images", "摘要 + 图像"),
        ("Zotero full text", "Zotero 全文"),
        (">Abstract<", ">摘要<"),
    )

    for old, new in replacements:
        value = value.replace(
            old,
            new,
        )

    return value


def _generated_note_body_text(note_html):
    """Extract generated-note body while dropping headings/metadata."""
    plain = note_plain_text(
        note_html
    )

    ignore_prefixes = (
        DEEP_NOTE_TITLE.casefold(),
        SUMMARY_NOTE_TITLE.casefold(),
        "ai总结",
        "ai 总结",
        "ai深度分析",
        "ai 深度分析",
        "ai review | cryogenic vibration",
        "ai deep analysis",
        "ai摘要",
        "ai 摘要",
        "ai summary",
        "generated:",
        "生成时间：",
        "生成时间:",
        "source:",
        "来源：",
        "来源:",
        "text pages:",
        "文本页：",
        "文本页:",
        "image pages:",
        "图像页：",
        "图像页:",
        "model:",
        "模型：",
        "模型:",
        "api:",
        "接口：",
        "接口:",
    )

    useful = []

    for line in plain.splitlines():
        line = line.strip()

        if not line:
            continue

        low = line.casefold()

        if any(
            low.startswith(prefix)
            for prefix in ignore_prefixes
        ):
            continue

        useful.append(
            line
        )

    return "\n".join(
        useful
    ).strip()


def _chinese_stats(value):
    """Count Han and Latin letters for language validation."""
    plain = note_plain_text(
        value
    )

    han = len(
        re.findall(
            r"[\u4e00-\u9fff]",
            plain,
        )
    )

    latin = len(
        re.findall(
            r"[A-Za-z]",
            plain,
        )
    )

    return han, latin


def _is_predominantly_chinese(
    value,
    minimum_han=60,
):
    """Require real Chinese prose, not just Chinese headings."""
    han, latin = _chinese_stats(
        value
    )

    if han < minimum_han:
        return False

    # Technical notes may legitimately contain English terminology, units,
    # model names and paper titles. This threshold still rejects English prose
    # with only a few Chinese headings.
    return han >= max(
        minimum_han,
        int(latin * 0.22),
    )


def _has_enough_chinese(
    value,
    minimum=8,
):
    """Backward-compatible helper with stronger Chinese validation."""
    return _is_predominantly_chinese(
        value,
        minimum_han=max(
            8,
            minimum,
        ),
    )


def _translate_generated_text_to_chinese(
    routes,
    value,
    kind="深度分析",
):
    """Translate an existing generated note without adding new facts."""
    source = safe(
        value
    ).strip()

    if not source:
        return ""

    minimum_han = (
        80
        if kind == "深度分析"
        else 40
    )

    if _is_predominantly_chinese(
        source,
        minimum_han=minimum_han,
    ):
        return source

    if not routes:
        return ""

    source = source[:24000]

    prompt = f"""
下面是已经生成完成的论文{kind}，但正文语言不符合要求。
请只做语言转换，不重新分析论文，不增加任何新事实。

要求：
- 所有叙述性正文改为中文。
- 论文题目、作者名、器件型号、标准术语、单位可以保留英文。
- 数字、结论、[PDF p.N] 引用必须原样保留。
- 所有 `$...$` 和 `$$...$$` LaTeX 公式必须保留，不得改变物理含义。
- 保留 Markdown 标题、列表和加粗结构。
- 不要写“AI”。
- 不要解释翻译过程。
- 只输出转换后的{kind}正文。

原内容：
{source}
""".strip()

    answer, _, _ = call_ai_fast(
        routes,
        prompt,
    )

    if (
        answer
        and _is_predominantly_chinese(
            answer,
            minimum_han=minimum_han,
        )
    ):
        return safe(
            answer
        ).strip()

    # Strong-model fallback only when the fast translation did not produce
    # genuine Chinese prose.
    answer, _, _ = call_ai(
        routes,
        prompt,
        [],
    )

    if (
        answer
        and _is_predominantly_chinese(
            answer,
            minimum_han=minimum_han,
        )
    ):
        return safe(
            answer
        ).strip()

    return ""


def ensure_chinese_deep_analysis(
    routes,
    analysis,
):
    """Guarantee that a newly generated deep analysis is Chinese."""
    value = safe(
        analysis
    ).strip()

    if not value:
        return ""

    if _is_predominantly_chinese(
        value,
        minimum_han=80,
    ):
        return value

    return _translate_generated_text_to_chinese(
        routes,
        value,
        kind="深度分析",
    )



def deep_analysis_quality_report(
    value,
    require_pdf_citation=False,
):
    """
    Validate the actual technical deep-analysis body.

    A note is not considered completed merely because it is Chinese.
    It must contain the requested engineering structure and final decision.
    """
    raw = safe(
        value
    )

    plain = (
        _generated_note_body_text(raw)
        if "<" in raw and ">" in raw
        else raw
    )

    issues = []

    if not _is_predominantly_chinese(
        plain,
        minimum_han=DEEP_MIN_CHINESE_CHARS,
    ):
        issues.append(
            "deep analysis is not sufficiently Chinese/detailed"
        )

    missing_sections = [
        section
        for section in REQUIRED_DEEP_SECTIONS
        if section not in plain
    ]

    if missing_sections:
        issues.append(
            "missing sections: "
            + ", ".join(
                missing_sections
            )
        )

    if not re.search(
        r"(?:等级|Grade)\s*[：:]\s*[ABCD]\b",
        plain,
        flags=re.I,
    ):
        issues.append(
            "missing final grade"
        )

    if not re.search(
        r"(?:建议|Recommendation)\s*[：:]",
        plain,
        flags=re.I,
    ):
        issues.append(
            "missing final recommendation"
        )

    # The requested deep-analysis format includes technical equations.
    if (
        "$" not in raw
        and "math" not in raw.casefold()
    ):
        issues.append(
            "missing LaTeX/math content"
        )

    technical_terms = (
        "振动",
        "隔振",
        "低温",
        "脉冲管",
        "pulse tube",
        "共振",
        "传递",
        "阻尼",
        "刚度",
        "热连接",
        "mixing chamber",
        "detector",
    )

    technical_hits = sum(
        term.casefold() in plain.casefold()
        for term in technical_terms
    )

    if technical_hits < 3:
        issues.append(
            "insufficient vibration/cryogenic engineering discussion"
        )

    if require_pdf_citation:
        citations = len(
            re.findall(
                r"\[PDF\s+p\.\s*\d+",
                plain,
                flags=re.I,
            )
        )

        if citations < 1:
            issues.append(
                "PDF source used but no [PDF p.N] citation found"
            )

    placeholder_terms = (
        "深度分析已完成，请查看",
        "please see the deep analysis",
        "无法提供深度分析",
        "不能进行深度分析",
    )

    if any(
        token.casefold() in plain.casefold()
        for token in placeholder_terms
    ):
        issues.append(
            "placeholder text detected"
        )

    return {
        "valid": not issues,
        "issues": issues,
        "chinese_chars": len(
            re.findall(
                r"[\u4e00-\u9fff]",
                plain,
            )
        ),
    }


def summary_quality_report(value):
    """Validate the actual 摘要 body."""
    raw = safe(
        value
    )

    plain = (
        _generated_note_body_text(raw)
        if "<" in raw and ">" in raw
        else raw
    )

    issues = []

    if not _is_predominantly_chinese(
        plain,
        minimum_han=SUMMARY_MIN_CHINESE_CHARS,
    ):
        issues.append(
            "summary is not sufficiently Chinese"
        )

    compact = re.sub(
        r"\s+",
        "",
        plain,
    )

    if len(compact) < 100:
        issues.append(
            "summary is too short"
        )

    if len(compact) > 1800:
        issues.append(
            "summary is too long"
        )

    forbidden = (
        "深度分析已完成，请查看",
        "AI Summary",
        "AI摘要",
        "AI 摘要",
    )

    if any(
        token.casefold() in plain.casefold()
        for token in forbidden
    ):
        issues.append(
            "summary contains placeholder/legacy AI wording"
        )

    return {
        "valid": not issues,
        "issues": issues,
    }


def deep_quality_repair_prompt(
    title,
    authors,
    year,
    doi,
    source,
    evidence,
    previous,
    issues,
):
    """Ask the strong model to regenerate an invalid deep analysis."""
    issue_text = "\n".join(
        "- " + safe(x)
        for x in issues
    )

    return rf"""
你上一版输出没有通过深度分析质量验收，请从论文证据重新生成完整版本。
不要只修改几句话；请重新组织成一份完整、中文、技术性强的深度分析。

未通过原因：
{issue_text}

论文：
标题：{title}
作者：{authors}
年份：{year}
DOI：{doi}

【证据底稿】
{evidence}

【选取的论文原文】
{source[:MAX_INPUT_CHARS]}

【上一版输出，仅供发现遗漏，不应被当作新证据】
{safe(previous)[:16000]}

强制要求：
- 正文必须是中文；专有名词、器件型号和标准术语可保留英文。
- 不得编造论文没有给出的实验、数字或结论。
- 如果只有摘要或书目信息，必须明确证据限制。
- 论文事实尽量标注 [PDF p.N]。
- 所有公式用 KaTeX 兼容 LaTeX。
- 必须包含并完整填写以下所有章节：
  # 一句话结论
  # 问题定义
  # 实验装置
  # 隔振方案
  # 理论
  # 关键公式
  # 关键图表
  # 关键数据
  # 对低温系统的意义
  # 可行性
  # 下一步
- “下一步”给出 5–8 个可执行动作。
- 如果论文没有某项数据/图/公式，在对应章节明确写“论文未提供”，不能删掉章节。
- 最后严格包含：
  **等级：A / B / C / D**
  **建议：** 一句中文行动建议。
- 目标长度：{TARGET_ANALYSIS_CHARS}
""".strip()


def extract_next_recommendation(analysis):
    """Extract the short Chinese or legacy recommendation."""
    m = re.search(
        r"\*\*(?:建议|Next)\s*[：:]\*\*\s*(.+)",
        safe(analysis),
        flags=re.I,
    )

    if m:
        return m.group(1).strip()[:500]

    return ""


def build_ai_summary_markdown(
    analysis,
    cls=None,
):
    """Deterministic Chinese-summary fallback from a Chinese deep analysis."""
    cls = cls or {}

    takeaway = extract_one_line(
        analysis
    )
    grade = extract_grade(
        analysis
    )
    next_step = extract_next_recommendation(
        analysis
    )

    source = ", ".join(
        SOURCE_TAGS.get(x, x)
        for x in cls.get("sources", [])
    )

    isolation = ", ".join(
        MEASURE_TAGS.get(x, x)
        for x in cls.get("measures", [])
    )

    lines = []

    if takeaway:
        lines.append(
            takeaway
        )

    if grade:
        lines.append(
            f"**等级：** {grade}"
        )

    if source:
        lines.append(
            f"**振动来源：** {source}"
        )

    if isolation:
        lines.append(
            f"**隔振措施：** {isolation}"
        )

    if next_step:
        lines.append(
            f"**建议：** {next_step}"
        )

    return "\n\n".join(
        lines
    ).strip()


def build_summary_from_existing_note(
    note_html,
):
    """Create a compact body from an existing generated note."""
    body = _generated_note_body_text(
        note_html
    )

    body = re.sub(
        r"\s+",
        " ",
        body,
    ).strip()

    return body[:1200]


def _extract_markdown_section(text, heading):
    """Extract one Markdown section without adding new facts."""
    value = safe(text)
    pattern = (
        r"(?ms)^#{1,6}\s*"
        + re.escape(heading)
        + r"\s*$\n"
        + r"(.*?)(?=^#{1,6}\s+|\Z)"
    )
    m = re.search(pattern, value)
    if not m:
        return ""

    useful = []
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("|"):
            continue
        if line == "$$":
            continue
        if re.fullmatch(r"[-:=\s]+", line):
            continue
        useful.append(line)

    return re.sub(r"\s+", " ", " ".join(useful)).strip()


def _trim_summary_piece(value, limit):
    """Trim near a sentence boundary when possible."""
    value = re.sub(r"\s+", " ", safe(value)).strip()
    if len(value) <= limit:
        return value

    short = value[:limit]
    cut = max(
        short.rfind("。"),
        short.rfind("；"),
        short.rfind(". "),
    )
    if cut >= int(limit * 0.55):
        short = short[:cut + 1]
    return short.strip()


def chinese_summary_from_analysis(routes, analysis, cls=None):
    """
    Build 摘要 locally from the validated Chinese 深度分析.

    Zero model requests are used. Only statements already present in the
    validated deep analysis are extracted/recombined.
    """
    source = safe(analysis).strip()
    if not source:
        return ""

    pieces = []

    conclusion = _extract_markdown_section(source, "一句话结论")
    if conclusion:
        pieces.append(_trim_summary_piece(conclusion, 300))

    isolation = _extract_markdown_section(source, "隔振方案")
    if isolation:
        pieces.append(
            "隔振/方法："
            + _trim_summary_piece(isolation, 260)
        )

    significance = _extract_markdown_section(
        source,
        "对低温系统的意义",
    )
    if significance:
        pieces.append(
            "对低温系统的意义："
            + _trim_summary_piece(significance, 260)
        )

    candidate = "\n\n".join(x for x in pieces if x).strip()

    if not summary_quality_report(candidate)["valid"]:
        clean = re.sub(r"(?m)^#{1,6}\s*", "", source)
        clean = re.sub(r"\$\$.*?\$\$", " ", clean, flags=re.S)
        clean = re.sub(r"\s+", " ", clean).strip()
        candidate = _trim_summary_piece(clean, 850)

    if summary_quality_report(candidate)["valid"]:
        return candidate

    return ""

def chinese_summary_from_existing_note(
    routes,
    note_html,
):
    """Create Chinese summary from an existing deep-analysis note."""
    deep_body = _generated_note_body_text(
        note_html
    )

    if not deep_body:
        return ""

    if not _is_predominantly_chinese(
        deep_body,
        minimum_han=80,
    ):
        deep_body = _translate_generated_text_to_chinese(
            routes,
            deep_body,
            kind="深度分析",
        )

    if not deep_body:
        return ""

    return chinese_summary_from_analysis(
        routes,
        deep_body,
    )


def write_summary_note_html(
    zot,
    item_key,
    summary_markdown,
    existing_note=None,
):
    """Create or update one Chinese per-paper 摘要 note."""
    summary_report = summary_quality_report(
        summary_markdown
    )

    if not summary_report["valid"]:
        raise ValueError(
            "Summary failed quality validation: "
            + "; ".join(
                summary_report["issues"]
            )
        )

    body = markdown_html(
        summary_markdown,
        "",
    )

    note_html = f"""
<div data-schema-version="8" data-ai-note-id="{SUMMARY_NOTE_MARKER}">
<h1>{html.escape(SUMMARY_NOTE_TITLE)}</h1>
{body}
</div>
""".strip()

    if existing_note:
        note_key = safe(
            existing_note.get("key")
            or existing_note.get(
                "data",
                {},
            ).get("key")
        )

        if not note_key:
            raise ValueError(
                "Existing summary note has no key."
            )

        ok, _, error = update_item_latest(
            zot,
            note_key,
            lambda fresh: fresh[
                "data"
            ].update({
                "note": note_html,
            }),
        )

        if not ok:
            raise RuntimeError(
                error
                or "Summary note update failed."
            )

        return "Updated"

    template = safe_item_template(
        zot,
        "note",
    )
    template["note"] = note_html
    template["parentItem"] = item_key

    result = zot.create_items(
        [template]
    )

    return (
        "Created"
        if result.get("success")
        else "CreateFailed"
    )


def _generated_note_score(
    child,
    kind,
):
    """Prefer Chinese, current-format, information-rich generated notes."""
    data = child.get(
        "data",
        {},
    )

    note = safe(
        data.get("note")
    )

    body = _generated_note_body_text(
        note
    )

    chinese = _is_predominantly_chinese(
        body,
        minimum_han=(
            80
            if kind == "deep"
            else 30
        ),
    )

    current_marker = (
        DEEP_NOTE_MARKER in note
        if kind == "deep"
        else SUMMARY_NOTE_MARKER in note
    )

    version = int(
        child.get(
            "version",
            0,
        )
        or data.get(
            "version",
            0,
        )
        or 0
    )

    return (
        1 if chinese else 0,
        1 if current_marker else 0,
        min(
            len(body),
            20000,
        ),
        version,
    )


def _delete_generated_note_duplicates(
    zot,
    candidates,
    keeper,
):
    """Delete only positively identified generated-note duplicates."""
    deleted = 0
    failed = 0

    keeper_key = safe(
        keeper.get("key")
        or keeper.get(
            "data",
            {},
        ).get("key")
    ) if keeper else ""

    for child in candidates:
        child_key = safe(
            child.get("key")
            or child.get(
                "data",
                {},
            ).get("key")
        )

        if (
            not child_key
            or child_key == keeper_key
        ):
            continue

        ok, error = delete_item_latest(
            zot,
            child_key,
        )

        if ok:
            deleted += 1
        else:
            failed += 1
            log(
                f"Generated note duplicate delete failed: "
                f"{child_key} | {error}",
                "warn",
            )

    return deleted, failed


def _first_pdf_child_key(children):
    for child in children:
        data = child.get(
            "data",
            {},
        )

        if data.get(
            "itemType"
        ) != "attachment":
            continue

        ctype = safe(
            data.get(
                "contentType"
            )
        ).casefold()

        filename = safe(
            data.get(
                "filename"
            )
        ).casefold()

        if (
            ctype == "application/pdf"
            or filename.endswith(
                ".pdf"
            )
        ):
            return safe(
                child.get("key")
            )

    return ""


def _fresh_note_html(
    zot,
    note_item,
):
    key = safe(
        note_item.get("key")
        or note_item.get(
            "data",
            {},
        ).get("key")
    )

    if not key:
        return safe(
            note_item.get(
                "data",
                {},
            ).get("note")
        )

    try:
        fresh = zot.item(
            key
        )

        return safe(
            fresh.get(
                "data",
                {},
            ).get("note")
        )
    except Exception:
        return safe(
            note_item.get(
                "data",
                {},
            ).get("note")
        )


def _update_generated_note_html(
    zot,
    note_item,
    note_html,
):
    key = safe(
        note_item.get("key")
        or note_item.get(
            "data",
            {},
        ).get("key")
    )

    if not key:
        return False, "Missing note key"

    ok, _, error = update_item_latest(
        zot,
        key,
        lambda fresh: fresh[
            "data"
        ].update({
            "note": note_html,
        }),
    )

    return ok, error


def standardize_existing_analysis_notes(
    zot,
    item_key,
    children,
    routes=None,
):
    """
    Enforce exactly one named Chinese 摘要 and one named, high-quality Chinese
    深度分析. Invalid deep notes are marked incomplete for source-based
    regeneration.
    """
    deep_candidates = []
    summary_candidates = []

    for child in children:
        data = child.get(
            "data",
            {},
        )

        if data.get(
            "itemType"
        ) != "note":
            continue

        kind = generated_note_kind(
            data.get(
                "note"
            )
        )

        if kind == "deep":
            deep_candidates.append(
                child
            )
        elif kind == "summary":
            summary_candidates.append(
                child
            )

    deep_note = (
        max(
            deep_candidates,
            key=lambda child: _generated_note_score(
                child,
                "deep",
            ),
        )
        if deep_candidates
        else None
    )

    summary_note = (
        max(
            summary_candidates,
            key=lambda child: _generated_note_score(
                child,
                "summary",
            ),
        )
        if summary_candidates
        else None
    )

    duplicate_deleted = 0
    duplicate_failed = 0
    deep_titles_fixed = 0
    summary_titles_fixed = 0
    deep_non_chinese = 0
    deep_quality_failed = 0
    summaries_regenerated = 0

    deleted, failed = _delete_generated_note_duplicates(
        zot,
        deep_candidates,
        deep_note,
    )
    duplicate_deleted += deleted
    duplicate_failed += failed

    deleted, failed = _delete_generated_note_duplicates(
        zot,
        summary_candidates,
        summary_note,
    )
    duplicate_deleted += deleted
    duplicate_failed += failed

    deep_valid = False
    deep_body = ""
    deep_issues = []

    if deep_note:
        old_html = _fresh_note_html(
            zot,
            deep_note,
        )

        had_correct_title = generated_note_has_title(
            old_html,
            DEEP_NOTE_TITLE,
        )

        standardized = ensure_generated_note_title_html(
            _localize_deep_note_metadata(
                old_html
            ),
            DEEP_NOTE_TITLE,
            DEEP_NOTE_MARKER,
        )

        if standardized != old_html:
            ok, error = _update_generated_note_html(
                zot,
                deep_note,
                standardized,
            )

            if ok:
                if not had_correct_title:
                    deep_titles_fixed += 1
                old_html = standardized
            else:
                log(
                    f"Deep note title standardization failed: "
                    f"{item_key} | {error}",
                    "warn",
                )

        deep_body = _generated_note_body_text(
            old_html
        )

        if not _is_predominantly_chinese(
            deep_body,
            minimum_han=DEEP_MIN_CHINESE_CHARS,
        ):
            deep_non_chinese += 1

        deep_report = deep_analysis_quality_report(
            old_html,
            require_pdf_citation=(
                "来源： PDF" in note_plain_text(
                    old_html
                )
            ),
        )

        deep_valid = bool(
            deep_report["valid"]
            and generated_note_has_title(
                old_html,
                DEEP_NOTE_TITLE,
            )
        )

        deep_issues = list(
            deep_report["issues"]
        )

        if not deep_valid:
            deep_quality_failed += 1

    summary_valid = False
    summary_issues = []

    if summary_note:
        old_summary_html = _fresh_note_html(
            zot,
            summary_note,
        )

        had_correct_title = generated_note_has_title(
            old_summary_html,
            SUMMARY_NOTE_TITLE,
        )

        standardized_summary = ensure_generated_note_title_html(
            old_summary_html,
            SUMMARY_NOTE_TITLE,
            SUMMARY_NOTE_MARKER,
        )

        if standardized_summary != old_summary_html:
            ok, error = _update_generated_note_html(
                zot,
                summary_note,
                standardized_summary,
            )

            if ok:
                if not had_correct_title:
                    summary_titles_fixed += 1
                old_summary_html = standardized_summary
            else:
                log(
                    f"Summary note title standardization failed: "
                    f"{item_key} | {error}",
                    "warn",
                )

        summary_report = summary_quality_report(
            old_summary_html
        )

        summary_valid = bool(
            summary_report["valid"]
            and generated_note_has_title(
                old_summary_html,
                SUMMARY_NOTE_TITLE,
            )
        )

        summary_issues = list(
            summary_report["issues"]
        )

        if (
            not summary_valid
            and deep_valid
        ):
            summary_text = chinese_summary_from_analysis(
                routes,
                deep_body,
            )

            if summary_text:
                try:
                    write_summary_note_html(
                        zot,
                        item_key,
                        summary_text,
                        existing_note=summary_note,
                    )

                    refreshed = _fresh_note_html(
                        zot,
                        summary_note,
                    )

                    summary_valid = (
                        summary_quality_report(
                            refreshed
                        )["valid"]
                        and generated_note_has_title(
                            refreshed,
                            SUMMARY_NOTE_TITLE,
                        )
                    )

                    if summary_valid:
                        summaries_regenerated += 1

                except Exception as e:
                    log(
                        f"Summary regeneration failed: "
                        f"{item_key} | {e}",
                        "warn",
                    )

    elif (
        deep_valid
        and CREATE_MISSING_AI_SUMMARY
    ):
        summary_text = chinese_summary_from_analysis(
            routes,
            deep_body,
        )

        if summary_text:
            try:
                status = write_summary_note_html(
                    zot,
                    item_key,
                    summary_text,
                )

                summary_valid = (
                    status
                    in {
                        "Created",
                        "Updated",
                    }
                )

                if summary_valid:
                    summaries_regenerated += 1

            except Exception as e:
                log(
                    f"Missing Chinese summary creation failed: "
                    f"{item_key} | {e}",
                    "warn",
                )

    return {
        "deep_exists": bool(
            deep_note
            and deep_valid
        ),
        "summary_exists": bool(
            summary_valid
        ),
        "deep_issues": deep_issues,
        "summary_issues": summary_issues,
        "duplicate_notes_deleted": duplicate_deleted,
        "duplicate_notes_failed": duplicate_failed,
        "deep_titles_fixed": deep_titles_fixed,
        "summary_titles_fixed": summary_titles_fixed,
        "deep_non_chinese": deep_non_chinese,
        "deep_quality_failed": deep_quality_failed,
        "summaries_regenerated": summaries_regenerated,
    }

def has_pdf_child(children):
    """Check whether a paper already has a child PDF."""
    for child in children:
        data = child.get(
            "data",
            {},
        )

        if data.get("itemType") != "attachment":
            continue

        content_type = safe(
            data.get("contentType")
        ).casefold()

        filename = safe(
            data.get("filename")
        ).casefold()

        if (
            "pdf" in content_type
            or filename.endswith(".pdf")
        ):
            return True

    return False



def _norm_match(value):
    value = safe(value).casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def _recent_institution_pdfs():
    """PDFs downloaded through the user's already authenticated school session."""
    if not USE_INSTITUTION_PDF_DIR:
        return []

    folder = Path(
        INSTITUTION_PDF_DIR
    ).expanduser()

    if not folder.exists():
        return []

    cutoff = (
        time.time()
        - INSTITUTION_PDF_LOOKBACK_DAYS * 86400
    )

    files = []

    for path in folder.glob("*.pdf"):
        try:
            if path.stat().st_mtime >= cutoff:
                files.append(path)
        except Exception:
            pass

    return sorted(
        files,
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )


def _pdf_head_text(path, chars=5000):
    try:
        import pymupdf

        doc = pymupdf.open(
            str(path)
        )

        parts = []

        for i in range(
            min(3, doc.page_count)
        ):
            parts.append(
                doc.load_page(i).get_text("text")
            )

        doc.close()
        return "\n".join(parts)[:chars]

    except Exception:
        return ""


def _match_local_pdf(title, doi=""):
    """Match a recently downloaded institution-access PDF by DOI/title."""
    title = safe(title)
    doi = norm_doi(doi)

    title_norm = _norm_match(
        title
    )
    doi_norm = _norm_match(
        doi
    )

    words = [
        w.casefold()
        for w in re.findall(
            r"[A-Za-z0-9]{4,}",
            title,
        )
    ][:10]

    for path in _recent_institution_pdfs():
        name_norm = _norm_match(
            path.stem
        )

        if (
            doi_norm
            and doi_norm in name_norm
        ):
            return str(path)

        if (
            title_norm
            and len(title_norm) >= 20
            and (
                title_norm in name_norm
                or name_norm in title_norm
            )
        ):
            return str(path)

        head = _pdf_head_text(
            path
        ).casefold()

        if (
            doi
            and doi.casefold() in head
        ):
            return str(path)

        if words:
            hits = sum(
                1
                for word in words
                if word in head
            )

            if hits >= max(
                4,
                int(len(words) * 0.65),
            ):
                return str(path)

    return ""


def find_institution_pdf_for_item(item):
    data = item.get("data", {})

    return _match_local_pdf(
        safe(data.get("title")),
        safe(data.get("DOI")),
    )


def find_institution_pdf_for_work(work):
    return _match_local_pdf(
        work_title(work),
        work_doi(work),
    )


def ensure_pdf_child_for_item(
    zot,
    item,
    children,
    download_folder,
):
    """Download an OA PDF only when the parent item has no child PDF."""
    if not ENSURE_PDF_CHILD:
        return has_pdf_child(
            children
        )

    if has_pdf_child(
        children
    ):
        return True

    try:
        work = openalex_work_for_zotero_item(
            item
        )

        if not work:
            return False

        pdf_path, _ = download_work_pdf(
            work,
            download_folder,
        )

        if not pdf_path:
            pdf_path = find_institution_pdf_for_item(
                item
            )

        if not pdf_path:
            return False

        result = zot.attachment_simple(
            [pdf_path],
            parentid=safe(
                item.get("key")
            ),
        )

        return bool(result)

    except Exception:
        return False


def has_ai_note(zot, item_key):
    """True only when deep analysis already exists."""
    try:
        children = zot.children(
            item_key
        )
    except Exception:
        return False

    return any(
        child.get(
            "data",
            {},
        ).get("itemType") == "note"
        and is_deep_analysis_note(
            safe(
                child.get(
                    "data",
                    {},
                ).get("note")
            )
        )
        for child in children
    )


def inline_html(text, attachment_key=""):
    """Render inline Markdown and Zotero-native inline math."""
    raw = safe(text)
    math_tokens = {}

    def save_math(match):
        token = f"@@MATH{len(math_tokens)}@@"
        latex = match.group(1).strip()

        math_tokens[token] = (
            '<span class="math">$'
            + html.escape(latex)
            + '$</span>'
        )

        return token

    # Inline math: $...$, but not $$...$$
    raw = re.sub(
        r"(?<!\$)\$([^$\n]+?)\$(?!\$)",
        save_math,
        raw,
    )

    s = html.escape(raw)

    s = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        s,
    )

    if attachment_key:
        def repl(m):
            page = m.group(1)

            return (
                '<a href="zotero://open-pdf/'
                f'library/items/{attachment_key}'
                f'?page={page}">'
                f'[PDF p.{page}]'
                '</a>'
            )

        s = re.sub(
            r"\[PDF p\.(\d+)\]",
            repl,
            s,
            flags=re.I,
        )

    for token, math_html in math_tokens.items():
        s = s.replace(
            html.escape(token),
            math_html,
        )

    return s

def markdown_html(md, attachment_key=""):
    """Convert Markdown to Zotero Note HTML with native math nodes."""
    out = []
    in_ul = False
    in_math = False
    math_lines = []

    def close_ul():
        nonlocal in_ul

        if in_ul:
            out.append("</ul>")
            in_ul = False

    def flush_math():
        nonlocal in_math, math_lines

        latex = "\n".join(
            math_lines
        ).strip()

        out.append(
            '<pre class="math">$$'
            + html.escape(latex)
            + '$$</pre>'
        )

        in_math = False
        math_lines = []

    for raw in safe(md).splitlines():
        line = raw.strip()

        if in_math:
            if line.endswith("$$"):
                before = line[:-2].strip()

                if before:
                    math_lines.append(before)

                flush_math()
            else:
                math_lines.append(raw)

            continue

        if line.startswith("$$"):
            close_ul()

            remainder = line[2:].strip()

            if remainder.endswith("$$"):
                latex = remainder[:-2].strip()

                out.append(
                    '<pre class="math">$$'
                    + html.escape(latex)
                    + '$$</pre>'
                )
            else:
                in_math = True

                if remainder:
                    math_lines.append(remainder)

            continue

        if not line:
            close_ul()
            continue

        if line.startswith("# "):
            close_ul()
            out.append(
                "<h2>"
                + inline_html(
                    line[2:],
                    attachment_key,
                )
                + "</h2>"
            )

        elif line.startswith("## "):
            close_ul()
            out.append(
                "<h3>"
                + inline_html(
                    line[3:],
                    attachment_key,
                )
                + "</h3>"
            )

        elif line.startswith("### "):
            close_ul()
            out.append(
                "<h4>"
                + inline_html(
                    line[4:],
                    attachment_key,
                )
                + "</h4>"
            )

        elif re.match(r"^[-*]\s+", line):
            if not in_ul:
                out.append("<ul>")
                in_ul = True

            out.append(
                "<li>"
                + inline_html(
                    re.sub(
                        r"^[-*]\s+",
                        "",
                        line,
                    ),
                    attachment_key,
                )
                + "</li>"
            )

        else:
            close_ul()

            out.append(
                "<p>"
                + inline_html(
                    line,
                    attachment_key,
                )
                + "</p>"
            )

    if in_math:
        flush_math()

    close_ul()

    return "\n".join(out)

def write_ai_note(
    zot,
    item_key,
    summary,
    meta,
    attachment_key,
    text_source,
    text_pages,
    image_pages,
):
    """Create/update exactly one Chinese per-paper 深度分析 note."""
    deep_report = deep_analysis_quality_report(
        summary,
        require_pdf_citation=bool(
            text_pages
        ),
    )

    if not deep_report["valid"]:
        raise ValueError(
            "Deep analysis failed quality validation: "
            + "; ".join(
                deep_report["issues"]
            )
        )

    source_labels = {
        "PDF": "PDF",
        "Abstract + images": "摘要 + 图像",
        "Zotero full text": "Zotero 全文",
        "Abstract": "摘要",
    }

    localized_source = source_labels.get(
        safe(text_source),
        safe(text_source),
    )

    note_html = f"""
<div data-schema-version="8" data-ai-note-id="{DEEP_NOTE_MARKER}">
<h1>{html.escape(DEEP_NOTE_TITLE)}</h1>
<p><strong>生成时间：</strong> {time.strftime("%Y-%m-%d %H:%M")}</p>
<p><strong>来源：</strong> {html.escape(localized_source)}</p>
<p><strong>文本页：</strong> {html.escape(text_pages)}</p>
<p><strong>图像页：</strong> {html.escape(image_pages)}</p>
<p><strong>模型：</strong> {html.escape(safe(meta.get("model")))}</p>
<p><strong>接口：</strong> {html.escape(safe(meta.get("api")))}</p>
<hr/>
{markdown_html(summary, attachment_key)}
</div>
""".strip()

    children = zot.children(
        item_key
    )

    candidates = []

    for child in children:
        data = child.get(
            "data",
            {},
        )

        if (
            data.get("itemType") == "note"
            and is_deep_analysis_note(
                data.get("note")
            )
        ):
            candidates.append(
                child
            )

    keeper = (
        max(
            candidates,
            key=lambda child: _generated_note_score(
                child,
                "deep",
            ),
        )
        if candidates
        else None
    )

    deleted, failed = _delete_generated_note_duplicates(
        zot,
        candidates,
        keeper,
    )

    if failed:
        log(
            f"Deep-note duplicate cleanup incomplete: "
            f"{failed} failed",
            "warn",
        )

    if keeper:
        ok, error = _update_generated_note_html(
            zot,
            keeper,
            note_html,
        )

        if not ok:
            raise RuntimeError(
                error
                or "Deep note update failed."
            )

        return (
            "Updated"
            + (
                f";RemovedDuplicates:{deleted}"
                if deleted
                else ""
            )
        )

    template = safe_item_template(
        zot,
        "note",
    )
    template["note"] = note_html
    template["parentItem"] = item_key

    result = zot.create_items(
        [template]
    )

    return (
        "Created"
        if result.get("success")
        else "CreateFailed"
    )

def write_ai_summary_note(
    zot,
    item_key,
    analysis,
    cls=None,
    routes=None,
):
    """Create/update exactly one concise Chinese 摘要 note."""
    summary_md = chinese_summary_from_analysis(
        routes,
        analysis,
        cls,
    )

    if not summary_md:
        raise ValueError(
            "Could not produce a Chinese summary."
        )

    children = zot.children(
        item_key
    )

    candidates = []

    for child in children:
        data = child.get(
            "data",
            {},
        )

        if (
            data.get("itemType") == "note"
            and is_ai_summary_note(
                data.get("note")
            )
        ):
            candidates.append(
                child
            )

    keeper = (
        max(
            candidates,
            key=lambda child: _generated_note_score(
                child,
                "summary",
            ),
        )
        if candidates
        else None
    )

    deleted, failed = _delete_generated_note_duplicates(
        zot,
        candidates,
        keeper,
    )

    if failed:
        log(
            f"Summary-note duplicate cleanup incomplete: "
            f"{failed} failed",
            "warn",
        )

    status = write_summary_note_html(
        zot,
        item_key,
        summary_md,
        existing_note=keeper,
    )

    if deleted:
        status += (
            f";RemovedDuplicates:{deleted}"
        )

    return status

def extract_grade(summary):
    m = re.search(
        r"(?:等级|Grade)\s*[：:]\s*([ABCD])",
        safe(summary),
        flags=re.I,
    )
    return m.group(1).upper() if m else ""

def extract_one_line(summary):
    lines = safe(summary).splitlines()

    for i, line in enumerate(lines):
        if line.strip().casefold() in {
            "# 一句话结论".casefold(),
            "# takeaway",
        }:
            for value in lines[i + 1:]:
                value = value.strip()
                if value and not value.startswith("#"):
                    return value[:500]

    clean = re.sub(r"[#*]+", "", safe(summary)).strip()
    return clean[:500]

def load_progress(paths, target_key):
    """Reuse local progress unless a rebuild has deleted it."""
    if not RESUME_FROM_PROGRESS:
        return []

    if not paths["progress"].exists():
        return []

    try:
        data = json.loads(
            paths["progress"].read_text(
                encoding="utf-8"
            )
        )

        scope = (
            data.get("scope")
            or data.get(
                "collection_key"
            )
        )

        if scope != target_key:
            return []

        return data.get(
            "results",
            [],
        )

    except Exception:
        return []

def upsert(results, row):
    key = row.get("ZoteroKey")

    for i, old in enumerate(results):
        if old.get("ZoteroKey") == key:
            results[i] = row
            return

    results.append(row)


def progress_row_for_item(
    results,
    item_key,
):
    """Return the most recent saved progress row for one Zotero item."""
    item_key = safe(
        item_key
    )

    for row in reversed(
        results
        or []
    ):
        if safe(
            row.get(
                "ZoteroKey"
            )
        ) == item_key:
            return row

    return None


def normalized_progress_title(value):
    value = safe(value).casefold()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def progress_row_for_paper(
    results,
    paper,
):
    """
    Find the newest progress row for a paper.

    Prefer Zotero key. Fall back to an exact normalized title only when the key
    is absent/missing from an older progress row.
    """
    item = paper.get("item", {})
    item_key = safe(item.get("key"))
    title = safe(item.get("data", {}).get("title"))
    norm_title = normalized_progress_title(title)

    if item_key:
        row = progress_row_for_item(
            results,
            item_key,
        )
        if row:
            return row

    if norm_title:
        for row in reversed(results or []):
            row_title = normalized_progress_title(
                row.get("Title")
                or row.get("title")
            )
            if row_title == norm_title:
                return row

    return None


def cached_analysis_for_paper(
    results,
    paper,
    require_pdf_citation=False,
):
    """Return a strict-valid saved Analysis for a paper, without any AI call."""
    row = progress_row_for_paper(
        results,
        paper,
    )

    if not row:
        return "", None, [
            "no matching progress row"
        ]

    analysis = safe(
        row.get("Analysis")
    ).strip()

    if not analysis:
        return "", row, [
            "progress row has no Analysis"
        ]

    report = deep_analysis_quality_report(
        analysis,
        require_pdf_citation=require_pdf_citation,
    )

    if not report["valid"]:
        return "", row, list(
            report.get("issues", [])
        )

    return analysis, row, []

def valid_cached_analysis(
    results,
    item_key,
    require_pdf_citation=False,
):
    """
    Reuse a previously paid-for deep analysis only if it still passes the
    current strict quality gate. This prevents Zotero write errors from causing
    unnecessary model re-analysis on the next run.
    """
    if not REUSE_VALID_PROGRESS_ANALYSIS_FOR_WRITE_REPAIR:
        return "", None

    row = progress_row_for_item(
        results,
        item_key,
    )

    if not row:
        return "", None

    analysis = safe(
        row.get(
            "Analysis"
        )
    ).strip()

    if not analysis:
        return "", row

    report = deep_analysis_quality_report(
        analysis,
        require_pdf_citation=(
            require_pdf_citation
        ),
    )

    if not report[
        "valid"
    ]:
        return "", row

    return analysis, row



def web_math_html(md):
    """HTML body for browser MathJax rendering."""
    body = markdown_html(
        md,
        attachment_key="",
    )

    # MathJax does not process <pre> by default.
    body = re.sub(
        r'<pre class="math">\$\$(.*?)\$\$</pre>',
        lambda m: (
            '<div class="math-display">$$'
            + m.group(1)
            + '$$</div>'
        ),
        body,
        flags=re.S,
    )

    return body


def rendered_html_document(title, markdown_text):
    """Standalone rendered deep-analysis document."""
    body = web_math_html(
        markdown_text
    )

    safe_title = html.escape(
        safe(title)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']]
  }},
  svg: {{fontCache: 'global'}}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
body {{
  max-width: 980px;
  margin: 42px auto;
  padding: 0 26px 80px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  line-height: 1.65;
}}
h1, h2, h3, h4 {{ line-height: 1.25; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #bbb; padding: 7px 9px; }}
.math-display {{
  overflow-x: auto;
  margin: 18px 0;
}}
code {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>{safe_title}</h1>
{body}
</body>
</html>"""


def save_all(
    paths,
    target_key,
    target_path,
    results,
    discovery,
):
    """Save resume state and HTML reading documents only."""
    data = {
        "scope": target_key,
        "root": target_path,
        "updated": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "results": results,
    }

    # Internal resume file.
    paths["progress"].write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Internal discovery record.
    paths["discovery"].write_text(
        json.dumps(
            discovery,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    sections = []

    for r in results:
        analysis = safe(
            r.get("Analysis")
        )

        if not analysis:
            continue

        no = int(
            r.get("No") or 0
        )
        title = safe(
            r.get("Title")
        )

        base = (
            f"{no:03d}_"
            + filename_safe(
                title
            )
        )

        deep_name = (
            base
            + "_深度分析.html"
        )

        summary_text = build_ai_summary_markdown(
            analysis,
            {},
        )

        summary_name = (
            base
            + "_摘要.html"
        )

        (paths["one"] / deep_name).write_text(
            rendered_html_document(
                f"{title}｜深度分析",
                analysis,
            ),
            encoding="utf-8",
        )

        (paths["one"] / summary_name).write_text(
            rendered_html_document(
                f"{title}｜摘要",
                summary_text,
            ),
            encoding="utf-8",
        )

        sections.append(
            "# "
            + str(no)
            + ". "
            + title
            + "\n\n"
            + analysis
            + "\n\n---\n"
        )

    paths["html"].write_text(
        rendered_html_document(
            "低温振动文献深度分析",
            "\n".join(sections),
        ),
        encoding="utf-8",
    )

def collection_depth(key, by_key):
    """Return Collection depth."""
    depth = 0
    seen = set()

    while key and key not in seen:
        seen.add(key)
        c = by_key.get(key)

        if not c:
            break

        parent = collection_parent(c)

        if not parent:
            break

        depth += 1
        key = parent

    return depth


def delete_all_collections(zot):
    """Delete every Collection; keep all library items and attachments."""
    if not DELETE_ALL_COLLECTIONS_BEFORE_REBUILD:
        return 0

    _, by_key, _ = collection_index(zot)

    if not by_key:
        return 0

    ordered = sorted(
        by_key.keys(),
        key=lambda k: collection_depth(k, by_key),
        reverse=True,
    )

    deleted = 0
    failed = []

    for key in progress_iter(
        ordered,
        description="Remove old folders",
        unit="folders",
    ):
        collection = by_key.get(key)

        if not collection:
            continue

        try:
            zot.delete_collection(collection)
            deleted += 1
        except Exception as e:
            failed.append(
                f"{collection_name(collection)}: {e}"
            )

    if failed:
        log(
            f"{len(failed)} folders could not be removed.",
            "warn",
        )

        for msg in failed[:8]:
            log(msg, "debug")

    return deleted


def reset_all_item_tags(zot):
    """Remove ALL tags from every top-level Zotero item."""
    if not RESET_ALL_PAPER_TAGS:
        return 0

    items = zot.everything(zot.top())
    changed = 0

    for item in progress_iter(
        items,
        description="Remove old tags",
        unit="items",
    ):
        data = item.get("data", {})

        if not data.get("tags"):
            continue

        try:
            fresh = zot.item(safe(item.get("key")))
            fresh["data"]["tags"] = []

            if zot.update_item(fresh):
                changed += 1

        except Exception as e:
            log(
                f"Cannot clear tags: {safe(data.get('title'))[:55]} | {e}",
                "warn",
            )

    return changed


def reset_local_output(paths):
    """Clear only this script's local output directory."""
    if not RESET_LOCAL_OUTPUT:
        return

    root = paths["root"]

    if not root.exists():
        return

    for child in root.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except Exception as e:
            log(
                f"Cannot remove old output: {child.name} | {e}",
                "warn",
            )

    paths["one"].mkdir(parents=True, exist_ok=True)
    paths["download"].mkdir(parents=True, exist_ok=True)


# ============================================================
# Smart state + hard reset
# ============================================================

def generated_tag_set():
    """Return generated tags after module initialization."""
    return set(SIMPLE_TAG_VOCAB) | {"Manual"}



def all_items_for_reset(zot):
    """Read all items, including child attachments and notes."""
    try:
        return zot.everything(zot.items())
    except Exception:
        items = []
        seen = set()

        for item in zot.everything(zot.top()):
            key = safe(item.get("key"))

            if key and key not in seen:
                seen.add(key)
                items.append(item)

            try:
                for child in zot.children(key):
                    ckey = safe(child.get("key"))

                    if ckey and ckey not in seen:
                        seen.add(ckey)
                        items.append(child)
            except Exception:
                pass

        return items


def hard_clear_all_tags(zot):
    """Remove tags from every Zotero item."""
    changed = 0
    failed = 0

    for item in progress_iter(
        all_items_for_reset(zot),
        description="Clear old tags",
        unit="items",
    ):
        data = item.get("data", {})

        if not data.get("tags"):
            continue

        key = safe(item.get("key"))

        if not key:
            continue

        try:
            fresh = zot.item(key)
            fresh["data"]["tags"] = []

            if zot.update_item(fresh):
                changed += 1
            else:
                failed += 1

        except Exception as e:
            failed += 1
            log(
                f"Tag clear failed: {key} | {e}",
                "warn",
            )

    return changed, failed


def hard_delete_all_collections(zot):
    """Delete all Collections, deepest first; keep items/PDFs."""
    _, by_key, _ = collection_index(zot)

    ordered = sorted(
        by_key.keys(),
        key=lambda key: collection_depth(key, by_key),
        reverse=True,
    )

    deleted = 0
    failed = 0

    for key in progress_iter(
        ordered,
        description="Delete old folders",
        unit="folders",
    ):
        collection = by_key.get(key)

        if not collection:
            continue

        try:
            zot.delete_collection(collection)
            deleted += 1

        except Exception as e:
            failed += 1
            log(
                f"Folder delete failed: "
                f"{collection_name(collection)} | {e}",
                "warn",
            )

    return deleted, failed


def verify_empty_organization(zot):
    """Verify old Collections and tags are gone."""
    _, by_key, _ = collection_index(zot)
    tagged = 0

    for item in all_items_for_reset(zot):
        if item.get("data", {}).get("tags"):
            tagged += 1

    if by_key:
        raise RuntimeError(
            f"Reset failed: {len(by_key)} Collections remain."
        )

    if tagged:
        raise RuntimeError(
            f"Reset failed: {tagged} tagged items remain."
        )


def hard_reset_before_rebuild(zot, paths):
    """Run only when the library is not already organized."""
    console.print()
    console.rule("Hard reset", style="dim")

    reset_local_output(paths)

    tags_cleared, tag_failed = hard_clear_all_tags(zot)
    folders_deleted, folder_failed = hard_delete_all_collections(zot)

    log(
        f"Tags cleared: {tags_cleared} | Failed: {tag_failed}",
        "ok" if tag_failed == 0 else "warn",
    )
    log(
        f"Folders deleted: {folders_deleted} | Failed: {folder_failed}",
        "ok" if folder_failed == 0 else "warn",
    )

    verify_empty_organization(zot)

    log("Reset verified", "ok")


def _top_collection_key(by_key, name):
    for key, collection in by_key.items():
        if (
            not collection_parent(collection)
            and collection_name(collection) == name
        ):
            return key

    return ""


def _children_by_name(by_key, parent_key):
    result = {}

    for key, collection in by_key.items():
        if collection_parent(collection) == parent_key:
            result[collection_name(collection)] = key

    return result


def organization_status(zot):
    """Detect whether the current English organization is already usable."""
    _, by_key, _ = collection_index(zot)

    manuals_key = _top_collection_key(
        by_key,
        MANUALS_FOLDER_NAME,
    )
    sources_key = _top_collection_key(
        by_key,
        SOURCE_ROOT_NAME,
    )
    isolation_key = _top_collection_key(
        by_key,
        MEASURE_ROOT_NAME,
    )

    roots_ok = bool(
        manuals_key
        and sources_key
        and isolation_key
    )

    source_children = (
        _children_by_name(
            by_key,
            sources_key,
        )
        if sources_key
        else {}
    )

    isolation_children = (
        _children_by_name(
            by_key,
            isolation_key,
        )
        if isolation_key
        else {}
    )

    pulse_ok = (
        SOURCE_FOLDERS["PulseTube"]
        in source_children
    )

    expected_measures = {
        folder_name
        for measure, folder_name in MEASURE_FOLDERS.items()
        if measure not in OPTIONAL_EXPANSION_MEASURES
    }

    measure_ratio = (
        len(
            expected_measures
            & set(isolation_children)
        )
        / max(1, len(expected_measures))
    )

    generated_collection_keys = {
        key
        for key, collection in by_key.items()
        if (
            key == manuals_key
            or key == sources_key
            or key == isolation_key
            or collection_parent(collection)
            in {sources_key, isolation_key}
        )
    }

    paper_items = []

    for item in zot.everything(zot.top()):
        data = item.get("data", {})

        if safe(data.get("itemType")) in PAPER_ITEM_TYPES:
            paper_items.append(item)

    organized_count = 0
    tagged_count = 0
    collection_count = 0

    for item in paper_items:
        data = item.get("data", {})

        tags = {
            safe(t.get("tag"))
            for t in data.get("tags", [])
            if isinstance(t, dict)
        }

        has_generated_tag = bool(
            tags & generated_tag_set()
        )

        collections = set(
            data.get("collections", [])
            or []
        )

        has_generated_collection = bool(
            collections
            & generated_collection_keys
        )

        if has_generated_tag:
            tagged_count += 1

        if has_generated_collection:
            collection_count += 1

        if (
            has_generated_tag
            or has_generated_collection
        ):
            organized_count += 1

    total = len(paper_items)

    organized_ratio = (
        organized_count / total
        if total
        else 0.0
    )

    ready = bool(
        roots_ok
        and pulse_ok
        and measure_ratio >= 0.95
        and organized_ratio >= ORGANIZED_MIN_RATIO
    )

    return {
        "ready": ready,
        "papers": total,
        "organized": organized_count,
        "tagged": tagged_count,
        "in_folders": collection_count,
        "ratio": organized_ratio,
        "roots_ok": roots_ok,
        "pulse_ok": pulse_ok,
        "measure_ratio": measure_ratio,
    }


def show_organization_status(status):
    """Compact startup status."""
    console.print()
    console.rule("Organization check", style="dim")

    state = (
        "READY"
        if status["ready"]
        else "REBUILD"
    )

    log(
        f"Folders: "
        f"{'OK' if status['roots_ok'] else 'Missing'}",
        "ok" if status["roots_ok"] else "warn",
    )

    log(
        f"Organized papers: "
        f"{status['organized']}/{status['papers']} "
        f"({status['ratio']:.0%})",
        "ok" if status["ready"] else "warn",
    )

    log(
        f"Status: {state}",
        "ok" if status["ready"] else "warn",
    )


# ============================================================
# Whole library helpers
# ============================================================

PAPER_ITEM_TYPES = {
    "journalArticle",
    "conferencePaper",
    "preprint",
    "report",
    "thesis",
    "bookSection",
    "document",
    "book",
}


def collect_whole_library_papers(zot, paths=None, manual_keys=None):
    """Read all paper-like top-level items, excluding detected manuals."""
    manual_keys = set(manual_keys or [])

    items = zot.everything(zot.top())
    found = []

    for item in progress_iter(
        items,
        description="Read library",
        unit="items",
    ):
        item_key = safe(item.get("key"))

        if item_key in manual_keys:
            continue

        data = item.get("data", {})
        item_type = safe(data.get("itemType"))

        if item_type not in PAPER_ITEM_TYPES:
            continue

        collection_names = []

        for key in data.get("collections", []) or []:
            if paths:
                collection_names.append(paths.get(key, key))
            else:
                collection_names.append(key)

        found.append({
            "item": item,
            "collections": collection_names,
        })

    return found



def item_text_for_manual_detection(zot, item):
    """Use title, abstract and indexed full text for manual detection."""
    data = item.get("data", {})

    parts = [
        safe(data.get("title")),
        safe(data.get("abstractNote")),
        safe(data.get("publicationTitle")),
    ]

    item_type = safe(data.get("itemType"))

    # Standalone PDF attachment
    if item_type == "attachment":
        try:
            indexed = zot.fulltext_item(
                safe(item.get("key"))
            )
            if isinstance(indexed, dict):
                parts.append(
                    safe(indexed.get("content"))[:5000]
                )
        except Exception:
            pass

    # Bibliographic item with PDF child
    else:
        for att in pdf_attachments(
            zot,
            safe(item.get("key")),
        )[:1]:
            full = indexed_fulltext(zot, att)
            if full:
                parts.append(full[:5000])
                break

    return "\n".join(x for x in parts if x)


def collect_manual_items(zot):
    """Find manuals quickly; read full text only for ambiguous document-like items."""
    items = zot.everything(zot.top())
    manuals = []

    deep_types = {
        "attachment",
        "document",
        "book",
        "report",
    }

    for item in progress_iter(
        items,
        description="Find manuals",
        unit="items",
    ):
        data = item.get("data", {})
        item_type = safe(data.get("itemType"))

        if item_type in {"note", "annotation"}:
            continue

        quick = "\n".join([
            safe(data.get("title")),
            safe(data.get("publicationTitle")),
            safe(data.get("url")),
            safe(data.get("filename")),
        ])

        if is_manual_text(quick):
            manuals.append(item)
            continue

        # Full-text fallback only for document-like items
        if item_type not in deep_types:
            continue

        # Avoid a full-text API call unless the metadata looks technical
        low = quick.casefold()

        if not any(
            token in low
            for token in (
                "model ",
                "controller",
                "amplifier",
                "cryostat",
                "cryogenic",
                "sensor",
                "instrument",
                "system",
                "device",
                "lakeshore",
                "lake shore",
                "bluefors",
                "oxford",
                "janis",
            )
        ):
            continue

        detailed = item_text_for_manual_detection(
            zot,
            item,
        )

        if is_manual_text(detailed):
            manuals.append(item)

    return manuals

def add_manuals_to_folder(zot, mapping, manuals):
    """Put manuals in Manuals and tag them in one update."""
    key = mapping.get("manuals")

    if not key:
        return 0

    added = 0

    for item in progress_iter(
        manuals,
        description="Classify manuals",
        unit="items",
    ):
        item_key = safe(item.get("key"))

        if not item_key:
            continue

        try:
            fresh = zot.item(item_key)
            fresh["data"]["tags"] = [{"tag": "Manual"}]
            fresh["data"]["collections"] = [key]

            if zot.update_item(fresh):
                added += 1

        except Exception as e:
            log(
                f"Manual write failed: "
                f"{safe(item.get('data', {}).get('title'))[:55]} | {e}",
                "warn",
            )

    return added



def collect_standalone_pdfs(zot, manual_keys=None):
    """Find top-level PDF attachments that have no parent item."""
    manual_keys = set(manual_keys or [])
    items = zot.everything(zot.top())
    pdfs = []

    for item in items:
        item_key = safe(item.get("key"))

        if item_key in manual_keys:
            continue

        data = item.get("data", {})

        if data.get("itemType") != "attachment":
            continue

        content_type = safe(
            data.get("contentType")
        ).casefold()

        filename = safe(
            data.get("filename")
        ).casefold()

        if (
            "pdf" in content_type
            or filename.endswith(".pdf")
        ):
            pdfs.append(item)

    return pdfs


def standalone_pdf_text(zot, item):
    """Read a small indexed-text sample from a standalone PDF."""
    data = item.get("data", {})
    parts = [
        "Title: " + safe(data.get("title")),
        "File: " + safe(data.get("filename")),
    ]

    try:
        full = zot.fulltext_item(
            safe(item.get("key"))
        )

        if isinstance(full, dict):
            content = safe(
                full.get("content")
            )

            if content:
                parts.append(
                    "Full text: "
                    + content[:CLASSIFY_TEXT_CHARS]
                )

    except Exception:
        pass

    return "\n".join(
        x for x in parts
        if x.strip()
    )


def classify_standalone_pdfs(
    zot,
    pdfs,
    category_map,
    routes,
):
    """Classify standalone PDFs directly into the new Collections."""
    if not pdfs:
        return 0

    entries = []

    for item in pdfs:
        entries.append({
            "id": safe(item.get("key")),
            "title": safe(
                item.get("data", {}).get("title")
                or item.get("data", {}).get("filename")
            ),
            "text": standalone_pdf_text(
                zot,
                item,
            ),
            "item": item,
        })

    classifications = classify_entries_fast(
        routes,
        entries,
    )

    moved = 0

    for entry in progress_iter(
        entries,
        description="Move standalone PDFs",
        unit="PDFs",
    ):
        cls = classifications.get(
            entry["id"],
            rule_content_classification(
                entry["text"]
            ),
        )

        ok, error = write_item_classification(
            zot,
            entry["item"],
            category_map,
            cls,
        )

        if ok:
            moved += 1
        else:
            log(
                f"Standalone PDF move failed: "
                f"{entry['title'][:55]} | {error}",
                "warn",
            )

    return moved


def ensure_root_collection(zot, name):
    """Create or reuse a top-level Collection."""
    _, by_key, _ = collection_index(zot)

    for key, c in by_key.items():
        if not collection_parent(c) and collection_name(c) == name:
            return key

    result = zot.create_collections([{"name": name}])

    if isinstance(result, dict):
        success = result.get("success", {})

        if isinstance(success, dict):
            key = success.get("0") or next(iter(success.values()), "")
            if key:
                return key

    _, by_key, _ = collection_index(zot)

    for key, c in by_key.items():
        if not collection_parent(c) and collection_name(c) == name:
            return key

    raise RuntimeError(f"Cannot create root collection: {name}")


def _ensure_child(
    zot,
    parent_key,
    name,
):
    """
    Create or reuse one direct child Collection under parent_key.

    This helper is intentionally idempotent:
    - reuse an existing child with the same name under the same parent;
    - otherwise create it once;
    - then re-read Zotero Collections and verify the result before returning.
    """
    parent_key = safe(
        parent_key
    )

    name = safe(
        name
    ).strip()

    if not parent_key:
        raise ValueError(
            "Cannot create child collection without a parent key."
        )

    if not name:
        raise ValueError(
            "Cannot create child collection without a name."
        )

    _, by_key, _ = collection_index(
        zot
    )

    for key, collection in by_key.items():
        if (
            collection_parent(
                collection
            ) == parent_key
            and collection_name(
                collection
            ) == name
        ):
            return key

    result = zot.create_collections([
        {
            "name": name,
            "parentCollection": parent_key,
        }
    ])

    if isinstance(
        result,
        dict,
    ):
        success = result.get(
            "success",
            {},
        )

        if isinstance(
            success,
            dict,
        ):
            key = (
                success.get("0")
                or next(
                    iter(
                        success.values()
                    ),
                    "",
                )
            )

            if key:
                return safe(
                    key
                )

    # Some Zotero-compatible responses do not expose the key in the exact
    # pyzotero success shape. Re-read the collection tree before failing.
    _, by_key, _ = collection_index(
        zot
    )

    for key, collection in by_key.items():
        if (
            collection_parent(
                collection
            ) == parent_key
            and collection_name(
                collection
            ) == name
        ):
            return key

    raise RuntimeError(
        f"Cannot create child collection: {name} "
        f"under parent {parent_key}"
    )


def ensure_library_classification_tree(zot):
    """Create top-level Manuals / Sources / Isolation Collections."""
    sources_root = ensure_root_collection(
        zot,
        SOURCE_ROOT_NAME,
    )

    isolation_root = ensure_root_collection(
        zot,
        MEASURE_ROOT_NAME,
    )

    manuals_root = ensure_root_collection(
        zot,
        MANUALS_FOLDER_NAME,
    )

    mapping = {
        "root": "",
        "manuals": manuals_root,
        "source_root": sources_root,
        "measure_root": isolation_root,
        "source": {},
        "measure": {},
    }

    for key, name in SOURCE_FOLDERS.items():
        mapping["source"][key] = _ensure_child(
            zot,
            sources_root,
            name,
        )

    for key, name in MEASURE_FOLDERS.items():
        mapping["measure"][key] = _ensure_child(
            zot,
            isolation_root,
            name,
        )

    return mapping

# ============================================================
# 14. 按内容整理振动来源与隔振措施
# ============================================================

# 简短标签
SOURCE_TAGS = {
    "PulseTube": "PulseTube",
}

MEASURE_TAGS = {
    "SpringSuspension": "Spring",
    "Pendulum": "Pendulum",
    "MultiStage": "MultiStage",
    "NegativeStiffness": "NegStiffness",
    "Elastomer": "Elastomer",
    "AirIsolation": "AirSpring",
    "ActiveIsolation": "Active",
    "TunedMassDamper": "TMD",
    "MagneticEddy": "MagDamping",
    "FlexibleConnection": "FlexCoupling",
    "SoftThermalLink": "ThermalLink",
    "StructuralDecoupling": "Decoupling",
    "InertialMass": "InertialMass",
    "DampingMaterial": "ViscoDamping",
    "IsolationPlatform": "IsoPlatform",
    "PhaseCancellation": "PhaseCancel",
    "ExchangeGas": "ExchangeGas",
    "CableIsolation": "CableControl",
    "OtherIsolation": "OtherIsolation",
}

# 规则只做兜底；最终优先使用文章内容的 AI 判断
SOURCE_RULES = {
    "PulseTube": [
        "pulse tube", "pulse-tube", "pulse tube cryocooler",
        "pulse tube refrigerator", "pt cryocooler",
        "pulse-tube-induced vibration", "pulse tube vibration",
    ],
}

MANUAL_RULES = [
    "user manual",
    "instruction manual",
    "service manual",
    "technical manual",
    "operating manual",
    "operation manual",
    "installation manual",
    "installation guide",
    "user guide",
    "reference guide",
    "programming guide",
    "datasheet",
    "data sheet",
    "specification sheet",
    "technical specification",
    "product specification",
    "operating instructions",
    "instruction handbook",
    "hardware manual",
    "software manual",
    "manufacturer manual",
]


def is_manual_text(text):
    """Detect manuals, datasheets and equipment guides."""
    low = safe(text).casefold()

    if any(word in low for word in MANUAL_RULES):
        return True

    # Strong title-like patterns
    return bool(
        re.search(
            r"\b(manual|datasheet|user guide|installation guide|"
            r"operating instructions|technical specifications?)\b",
            low,
        )
    )


MEASURE_RULES = {
    "SpringSuspension": [
        "spring suspension", "spring isolator", "coil spring",
        "suspended by springs", "spring-mounted",
    ],
    "Pendulum": [
        "pendulum isolation", "pendulum suspension",
        "pendulum stage", "simple pendulum",
    ],
    "MultiStage": [
        "multi-stage isolation", "multistage isolation",
        "multi-stage suspension", "multistage suspension",
        "mechanical filter", "cascaded isolation",
    ],
    "NegativeStiffness": [
        "negative stiffness", "quasi-zero stiffness",
        "zero stiffness", "geometric anti-spring",
    ],
    "Elastomer": [
        "elastomer isolator", "elastomeric isolator",
        "rubber isolator", "sorbothane", "neoprene isolator",
    ],
    "AirIsolation": [
        "air spring", "pneumatic isolator", "pneumatic isolation",
        "air bearing isolation", "air table", "air suspension",
    ],
    "ActiveIsolation": [
        "active vibration isolation", "active isolation",
        "active vibration control", "feedback vibration",
        "feedforward vibration", "piezo actuator",
    ],
    "TunedMassDamper": [
        "tuned mass damper", "tmd vibration",
        "dynamic vibration absorber", "tuned vibration absorber",
    ],
    "MagneticEddy": [
        "eddy current damper", "eddy-current damper",
        "magnetic damping", "magnetic damper",
    ],
    "FlexibleConnection": [
        "flexible hose", "flexible bellows", "bellows decoupling",
        "flexible connection", "flexible tube",
        "vibration decoupling hose",
    ],
    "SoftThermalLink": [
        "copper braid", "braided copper", "flexible thermal link",
        "flexible heat strap", "thermal strap",
        "soft thermal link",
    ],
    "StructuralDecoupling": [
        "structural decoupling", "mechanical decoupling",
        "remote compressor", "remote motor", "separate support frame",
        "decoupled cryostat", "remote pulse tube",
    ],
    "InertialMass": [
        "inertial mass", "inertia block", "mass-loaded isolation",
        "heavy base", "granite table", "massive platform",
    ],
    "DampingMaterial": [
        "viscoelastic damping", "constrained layer damping",
        "damping layer", "damping material",
        "particle damping", "granular damping",
    ],
    "IsolationPlatform": [
        "vibration isolation platform", "isolation table",
        "optical table vibration isolation",
        "commercial vibration isolation",
    ],
    "PhaseCancellation": [
        "phase cancellation", "phase-controlled pulse tube",
        "relative phase", "phase shift cryocooler",
        "self-cancellation of cold stage vibration",
        "active noise cancellation pulse tube",
    ],
    "ExchangeGas": [
        "exchange gas", "helium exchange gas",
        "non-contact heat exchanger", "noncontact heat exchanger",
        "gas thermal coupling", "gas-liquid helium damping",
    ],
    "CableIsolation": [
        "cable microphonics", "microphonic cable",
        "triboelectric noise", "vibration-induced electrical noise",
        "vacuum insulated cable", "cable clamping",
    ],
}

# 用于主动扩展每个措施文件夹
MEASURE_SEARCH_QUERIES = {
    "SpringSuspension": [
        '"spring suspension" vibration isolation precision instrument',
        '"spring isolator" vibration isolation laboratory',
    ],
    "Pendulum": [
        '"pendulum suspension" vibration isolation precision',
        '"pendulum isolation" vibration laboratory',
    ],
    "MultiStage": [
        '"multi-stage suspension" vibration isolation',
        '"mechanical filter" vibration isolation precision',
    ],
    "NegativeStiffness": [
        '"negative stiffness" vibration isolation',
        '"quasi-zero stiffness" vibration isolation precision',
    ],
    "Elastomer": [
        '"elastomeric isolator" vibration precision instrument',
        '"rubber isolator" vibration isolation laboratory',
    ],
    "AirIsolation": [
        '"air spring" vibration isolation optical table',
        '"pneumatic vibration isolation" precision instrument',
    ],
    "ActiveIsolation": [
        '"active vibration isolation" precision instrument',
        '"active vibration control" optical table',
    ],
    "TunedMassDamper": [
        '"tuned mass damper" precision vibration isolation',
        '"dynamic vibration absorber" precision instrument',
    ],
    "MagneticEddy": [
        '"eddy current damper" vibration isolation',
        '"magnetic damping" precision vibration',
    ],
    "FlexibleConnection": [
        '"flexible bellows" vibration isolation vacuum',
        '"flexible hose" vibration decoupling cryogenic',
    ],
    "SoftThermalLink": [
        '"copper braid" vibration cryogenic',
        '"flexible thermal link" vibration cryostat',
    ],
    "StructuralDecoupling": [
        '"mechanical decoupling" vibration cryostat',
        '"remote compressor" vibration cryogenic',
        '"remote pulse tube" vibration',
    ],
    "InertialMass": [
        '"inertia block" vibration isolation laboratory',
        '"massive platform" vibration isolation precision',
    ],
    "DampingMaterial": [
        '"viscoelastic damping" precision vibration',
        '"constrained layer damping" vibration instrument',
        '"particle damping" precision vibration',
    ],
    "IsolationPlatform": [
        '"vibration isolation platform" precision measurement',
        '"optical table" vibration isolation',
    ],
    "PhaseCancellation": [
        '"pulse tube" phase cancellation vibration',
        '"active noise cancellation" pulse tube cryocooler',
        '"self-cancellation" cold stage vibration cryocooler',
    ],
    "ExchangeGas": [
        '"helium exchange gas" vibration isolation cryostat',
        '"non-contact heat exchanger" vibration cryostat',
        '"exchange gas" mechanical decoupling cryogenic',
    ],
    "CableIsolation": [
        '"vibration-induced electrical noise" dilution refrigerator cable',
        '"cryogenic cable" microphonic vibration pulse tube',
        '"vacuum insulated cable" cryogenic vibration noise',
    ],
}

SIMPLE_TAG_VOCAB = [
    "PulseTube",
    "Spring", "Pendulum", "MultiStage", "NegStiffness",
    "Elastomer", "AirSpring", "Active", "TMD",
    "MagDamping", "FlexCoupling", "ThermalLink",
    "Decoupling", "InertialMass", "ViscoDamping",
    "IsoPlatform", "PhaseCancel", "ExchangeGas", "CableControl",
    "OtherIsolation",
    "Manual", "Cryogenic", "0vbb", "Bolometer",
    "PTPrinciple", "PressureOsc", "RotaryValve", "ColdHead",
    "TransferPath", "Microphonics",
    "PSD", "ASD", "Accel", "Interferometer",
    "Transfer", "Resonance",
]

OLD_AUTO_TAGS = {
    "AI-自动发现", "0νββ-文献扩展", "0νββ-文献库",
    "0νββ与低温探测器", "干式稀释制冷机", "PulseTube振动源",
    "被动隔振", "主动隔振", "低温热连接", "振动测量与PSD",
    "机械噪声与微音", "基础隔振理论", "相关背景",
}

CLASSIFICATION_CACHE = {}


def _contains_any(text, words):
    t = text.casefold()
    return any(w.casefold() in t for w in words)


def rule_content_classification(text):
    """Rule fallback supporting both engineering and background papers."""
    text = safe(text)
    low = text.casefold()

    sources = [
        key
        for key, words in SOURCE_RULES.items()
        if _contains_any(text, words)
    ]

    measures = [
        key
        for key, words in MEASURE_RULES.items()
        if _contains_any(text, words)
    ]

    tags = []

    # --------------------------------------------------------
    # Background/topic tags
    # --------------------------------------------------------

    # 0vbb: tolerate hyphens and spelling variants.
    if (
        re.search(
            r"neutrinoless\s+double[-\s]?beta",
            low,
        )
        or "0νββ" in low
        or "0vbb" in low
        or "0nu2beta" in low
    ):
        tags.append(
            "0vbb"
        )

    if any(
        token in low
        for token in (
            "bolometer",
            "bolometric",
            "cryogenic calorimeter",
            "thermal detector",
        )
    ):
        tags.append(
            "Bolometer"
        )

    if any(
        token in low
        for token in (
            "cryostat",
            "cryogenic",
            "cryocooler",
            "cryocoolers",
            "dilution refrigerator",
            "dilution fridge",
            "millikelvin",
            "milli-kelvin",
            "low-temperature refrigerator",
            "low temperature refrigerator",
        )
    ):
        tags.append(
            "Cryogenic"
        )

    # --------------------------------------------------------
    # Pulse-tube mechanism / transfer-path tags
    # --------------------------------------------------------
    if (
        "pulse tube" in low
        or "pulse-tube" in low
        or "pt cryocooler" in low
    ):
        if any(
            token in low
            for token in (
                "regenerator",
                "inertance tube",
                "orifice",
                "reservoir",
                "phase shift",
                "mass flow",
                "acoustic impedance",
                "thermoacoustic",
            )
        ):
            tags.append("PTPrinciple")

        if any(
            token in low
            for token in (
                "pressure oscillation",
                "pressure wave",
                "oscillating pressure",
                "periodic pressure",
            )
        ):
            tags.append("PressureOsc")

        if any(
            token in low
            for token in (
                "rotary valve",
                "valve unit",
                "remote motor",
                "stepper motor",
            )
        ):
            tags.append("RotaryValve")

        if any(
            token in low
            for token in (
                "cold head",
                "cold-head",
                "cold stage",
                "cold-stage",
            )
        ):
            tags.append("ColdHead")

    if any(
        token in low
        for token in (
            "transfer path",
            "transmission path",
            "mechanical path",
            "mechanical bypass",
            "vibration transmission",
        )
    ):
        tags.append("TransferPath")

    if (
        "microphonic" in low
        or "triboelectric" in low
        or "vibration-induced electrical noise" in low
    ):
        tags.append("Microphonics")

    # --------------------------------------------------------
    # Source/isolation tags
    # --------------------------------------------------------
    tags.extend(
        SOURCE_TAGS[x]
        for x in sources
        if x in SOURCE_TAGS
    )

    tags.extend(
        MEASURE_TAGS[x]
        for x in measures
        if x in MEASURE_TAGS
    )

    # --------------------------------------------------------
    # Measurement tags
    # --------------------------------------------------------
    if (
        "power spectral density" in low
        or re.search(r"\bpsd\b", low)
    ):
        tags.append(
            "PSD"
        )

    if (
        "amplitude spectral density" in low
        or re.search(r"\basd\b", low)
    ):
        tags.append(
            "ASD"
        )

    if "accelerometer" in low:
        tags.append(
            "Accel"
        )

    if (
        "interferometer" in low
        or "interferometric" in low
    ):
        tags.append(
            "Interferometer"
        )

    if (
        "transfer function" in low
        or "transmissibility" in low
    ):
        tags.append(
            "Transfer"
        )

    if (
        "resonance" in low
        or "resonant" in low
    ):
        tags.append(
            "Resonance"
        )

    tags = list(
        dict.fromkeys(tags)
    )[:MAX_SIMPLE_TAGS]

    return {
        "sources": sources,
        "measures": measures,
        "tags": tags,
        "confidence": (
            0.65
            if (
                sources
                or measures
                or tags
            )
            else 0.20
        ),
        "reason": "Rule match",
    }

def is_relevant_for_ai(text):
    """Only send potentially relevant papers to AI classification."""
    low = safe(text).casefold()

    return any(
        token in low
        for token in (
            "vibration",
            "isolation",
            "isolator",
            "cryostat",
            "cryogenic",
            "pulse tube",
            "pulse-tube",
            "dilution refrigerator",
            "bolometer",
            "microphonic",
            "mechanical noise",
            "thermal link",
            "copper braid",
            "suspension",
            "damper",
            "damping",
            "resonance",
        )
    )


def _extract_json_array(text):
    """解析模型 JSON。"""
    if not text:
        return []

    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
    s = re.sub(r"\s*```$", "", s)

    left = s.find("[")
    right = s.rfind("]")

    if left < 0 or right <= left:
        return []

    try:
        data = json.loads(s[left:right + 1])
        return data if isinstance(data, list) else []
    except Exception:
        return []

def classification_collection_keys(mapping, cls):
    """Return all target Collection keys for one classification."""
    keys = []

    for source in cls.get("sources", []):
        key = mapping.get("source", {}).get(source)
        if key and key not in keys:
            keys.append(key)

    for measure in cls.get("measures", []):
        key = mapping.get("measure", {}).get(measure)
        if key and key not in keys:
            keys.append(key)

    return keys

def item_classification_text(zot, item, use_fulltext=None):
    """Use title/abstract first; full text is optional."""
    if use_fulltext is None:
        use_fulltext = FAST_CLASSIFY_USE_FULLTEXT

    d = item.get("data", {})

    parts = [
        "Title: " + safe(d.get("title")),
        "Abstract: " + safe(d.get("abstractNote")),
        "Journal: " + safe(d.get("publicationTitle")),
    ]

    if use_fulltext:
        for att in pdf_attachments(
            zot,
            safe(item.get("key")),
        )[:1]:
            full = indexed_fulltext(zot, att)

            if full:
                parts.append(
                    "Full text: "
                    + full[:CLASSIFY_TEXT_CHARS]
                )
                break

    return "\n".join(
        x for x in parts
        if x.strip()
    )

def work_classification_text(work):
    """新发现论文使用 OpenAlex 元数据。"""
    topics = []

    for t in work.get("topics", []) or []:
        if isinstance(t, dict):
            name = safe(t.get("display_name"))
            if name:
                topics.append(name)

    return "\n".join([
        "Title: " + work_title(work),
        "Abstract: " + work_abstract(work),
        "Journal: " + work_venue(work),
        "Topics: " + "; ".join(topics[:5]),
    ])

def ai_classify_batch(routes, entries):
    """Classify documents by actual content."""
    if not USE_AI_CONTENT_CLASSIFIER or not routes or not entries:
        return {}

    source_keys = list(SOURCE_FOLDERS)
    measure_keys = list(MEASURE_FOLDERS)

    payload = [
        {
            "id": e["id"],
            "title": e["title"],
            "content": e["text"][:CLASSIFY_TEXT_CHARS],
        }
        for e in entries
    ]

    prompt = f"""
Classify research documents conservatively from their actual content.

Tasks:
1. Mark PulseTube only when pulse-tube vibration is a real source or focus.
2. Select only isolation methods actually studied, used, designed, or tested.
3. Give at most {MAX_SIMPLE_TAGS} short representative English tags.

Allowed source keys:
{source_keys}

Allowed isolation keys:
{measure_keys}

Allowed tags:
{SIMPLE_TAG_VOCAB}

Rules:
- Do not infer PulseTube from cryogenic context alone.
- A paper may use multiple isolation methods.
- Mentioning a method is not enough; it must matter to the work.
- Prefer fewer accurate labels.
- Tags must be short and representative.
- confidence: 0 to 1.
- reason: at most 12 English words.
- Return JSON only.

Format:
[
  {{
    "id": "item_id",
    "sources": ["PulseTube"],
    "measures": ["SpringSuspension", "SoftThermalLink"],
    "tags": ["PulseTube", "Spring", "ThermalLink", "PSD"],
    "confidence": 0.93,
    "reason": "Pulse-tube source with spring suspension and flexible heat link"
  }}
]

Documents:
{json.dumps(payload, ensure_ascii=False)}
""".strip()

    answer, error, _ = call_ai_fast(routes, prompt)

    if error or not answer:
        return {}

    rows = _extract_json_array(answer)
    result = {}

    valid_sources = set(SOURCE_FOLDERS)
    valid_measures = set(MEASURE_FOLDERS)
    valid_tags = set(SIMPLE_TAG_VOCAB)

    for row in rows:
        if not isinstance(row, dict):
            continue

        rid = safe(row.get("id"))
        if not rid:
            continue

        sources = [
            x for x in row.get("sources", [])
            if x in valid_sources
        ]
        measures = [
            x for x in row.get("measures", [])
            if x in valid_measures
        ]
        tags = [
            x for x in row.get("tags", [])
            if x in valid_tags
        ]

        for x in sources:
            tag = SOURCE_TAGS.get(x)
            if tag and tag not in tags:
                tags.insert(0, tag)

        for x in measures:
            tag = MEASURE_TAGS.get(x)
            if tag and tag not in tags:
                tags.append(tag)

        tags = list(dict.fromkeys(tags))[:MAX_SIMPLE_TAGS]

        try:
            confidence = float(row.get("confidence", 0.7))
        except Exception:
            confidence = 0.7

        result[rid] = {
            "sources": sources,
            "measures": measures,
            "tags": tags,
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": safe(row.get("reason"))[:100],
        }

    return result

def verify_collection_counts(zot, mapping):
    """Read actual Collection counts back from Zotero."""
    rows = []

    if mapping.get("manuals"):
        rows.append(("Manuals", mapping["manuals"]))

    for name, key in [
        ("Pulse Tube", mapping.get("source", {}).get("PulseTube")),
    ]:
        if key:
            rows.append((name, key))

    for code, folder_name in MEASURE_FOLDERS.items():
        key = mapping.get("measure", {}).get(code)
        if key:
            rows.append((folder_name, key))

    counts = {}

    for name, key in rows:
        try:
            if hasattr(zot, "num_collectionitems"):
                value = zot.num_collectionitems(key)
                try:
                    count = int(value)
                except Exception:
                    count = 0
            else:
                count = len(
                    zot.everything(
                        zot.collection_items_top(key)
                    )
                )

            counts[name] = count

        except Exception as e:
            counts[name] = -1
            log(
                f"Cannot verify {name}: {e}",
                "warn",
            )

    nonempty = {
        name: count
        for name, count in counts.items()
        if count > 0
    }

    empty = sum(
        1 for count in counts.values()
        if count == 0
    )

    console.print()
    console.rule("Collection check", style="dim")

    if nonempty:
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
        )
        table.add_column(style="dim")
        table.add_column(justify="right")

        for name, count in nonempty.items():
            table.add_row(name, str(count))

        console.print(table)

    log(
        f"Non-empty folders: {len(nonempty)} | Empty folders: {empty}",
        "ok" if nonempty else "warn",
    )

    if not nonempty:
        raise RuntimeError(
            "Classification write failed: all generated Collections are empty."
        )

    return counts

def write_item_classification(
    zot,
    item,
    mapping,
    cls,
    extra_collections=None,
):
    """
    Replace only pipeline-managed classification metadata.

    Ordinary user tags and unrelated Collection memberships are preserved.
    """
    item_key = safe(
        item.get("key")
        or item.get("data", {}).get("key")
    )

    if not item_key:
        return False, "Missing item key"

    desired_tags = []

    for tag in (cls.get("tags", []) or [])[:MAX_SIMPLE_TAGS]:
        tag = safe(tag).strip()

        if tag and tag not in desired_tags:
            desired_tags.append(tag)

    desired_collections = classification_collection_keys(
        mapping,
        cls,
    )

    for key in extra_collections or []:
        key = safe(key)

        if key and key not in desired_collections:
            desired_collections.append(key)

    managed_tags = (
        set(SIMPLE_TAG_VOCAB)
        | set(SOURCE_TAGS.values())
        | set(MEASURE_TAGS.values())
        | set(OLD_AUTO_TAGS)
        | {"Manual"}
    )

    managed_collections = set()

    for field in (
        "manuals",
        "source_root",
        "measure_root",
    ):
        key = safe(mapping.get(field))

        if key:
            managed_collections.add(key)

    managed_collections.update(
        key
        for key in (mapping.get("source", {}) or {}).values()
        if key
    )

    managed_collections.update(
        key
        for key in (mapping.get("measure", {}) or {}).values()
        if key
    )

    def mutate(fresh):
        data = fresh["data"]

        preserved_tags = []

        for tag_obj in data.get("tags", []) or []:
            if isinstance(tag_obj, dict):
                value = safe(tag_obj.get("tag")).strip()
            else:
                value = safe(tag_obj).strip()

            if (
                value
                and value not in managed_tags
                and value not in preserved_tags
            ):
                preserved_tags.append(value)

        final_tags = preserved_tags + [
            tag
            for tag in desired_tags
            if tag not in preserved_tags
        ]

        data["tags"] = [
            {"tag": tag}
            for tag in final_tags
        ]

        preserved_collections = []

        for key in data.get("collections", []) or []:
            key = safe(key)

            if (
                key
                and key not in managed_collections
                and key not in desired_collections
                and key not in preserved_collections
            ):
                preserved_collections.append(key)

        data["collections"] = list(
            dict.fromkeys(
                preserved_collections
                + desired_collections
            )
        )

    ok, fresh, error = update_item_latest(
        zot,
        item_key,
        mutate,
    )

    if not ok:
        return False, (
            error
            or "Classification update failed"
        )

    if fresh:
        item["data"]["tags"] = [
            dict(tag)
            for tag in (
                fresh.get("data", {}).get("tags", [])
                or []
            )
            if isinstance(tag, dict)
        ]

        item["data"]["collections"] = list(
            fresh.get("data", {}).get("collections", [])
            or []
        )

    return True, ""


def classify_entries_fast(routes, entries):
    """Rule-first classification; AI only for unresolved relevant documents."""
    result = {}
    pending = []

    for entry in entries:
        rule = rule_content_classification(
            entry["text"]
        )

        has_engineering_class = bool(
            rule.get("sources")
            or rule.get("measures")
        )

        if (
            FAST_RULE_ONLY_IF_CLEAR
            and has_engineering_class
        ):
            result[entry["id"]] = rule
            continue

        if not is_relevant_for_ai(entry["text"]):
            result[entry["id"]] = rule
            continue

        pending.append(entry)

    if not pending:
        return result

    for start in range(
        0,
        len(pending),
        CLASSIFY_BATCH_SIZE,
    ):
        batch = pending[
            start:start + CLASSIFY_BATCH_SIZE
        ]

        ai_result = ai_classify_batch(
            routes,
            batch,
        )

        for entry in batch:
            cls = ai_result.get(entry["id"])

            if not cls:
                cls = rule_content_classification(
                    entry["text"]
                )

            result[entry["id"]] = cls

    return result


def classify_and_tag_collection(
    zot,
    papers,
    target_key,
    category_map,
    routes=None,
):
    """Classify and immediately move items into the new Collections."""
    entries = []

    for paper in progress_iter(
        papers,
        description="Prepare classification",
        unit="papers",
    ):
        item = paper["item"]
        ikey = safe(item.get("key"))

        entries.append({
            "id": ikey,
            "title": safe(
                item.get("data", {}).get("title")
            ),
            "text": item_classification_text(
                zot,
                item,
                use_fulltext=False,
            ),
            "item": item,
        })

    write_ok = 0
    write_fail = 0

    # Rule-first + fast AI only when needed
    classifications = classify_entries_fast(
        routes,
        entries,
    )

    for entry in progress_iter(
        entries,
        description="Move to folders",
        unit="papers",
    ):
        cls = classifications.get(
            entry["id"],
            rule_content_classification(
                entry["text"]
            ),
        )

        CLASSIFICATION_CACHE[
            entry["id"]
        ] = cls

        ok, error = write_item_classification(
            zot,
            entry["item"],
            category_map,
            cls,
        )

        if ok:
            write_ok += 1
        else:
            write_fail += 1
            log(
                f"Classification write failed: "
                f"{entry['title'][:55]} | {error}",
                "warn",
            )

    log(
        f"Moved: {write_ok} | Failed: {write_fail}",
        "ok" if write_fail == 0 else "warn",
    )

    if VERIFY_COLLECTION_WRITES:
        verify_collection_counts(
            zot,
            category_map,
        )

def merge_candidate(
    store,
    work,
    source,
    seed_title="",
    forced_measure="",
):
    if not work or not work_title(work):
        return

    key = candidate_key(work)

    if key not in store:
        store[key] = {
            "work": work,
            "sources": [],
            "seed_titles": [],
            "forced_measures": [],
        }

    if source not in store[key]["sources"]:
        store[key]["sources"].append(source)

    if seed_title and seed_title not in store[key]["seed_titles"]:
        store[key]["seed_titles"].append(seed_title)

    if (
        forced_measure
        and forced_measure not in store[key]["forced_measures"]
    ):
        store[key]["forced_measures"].append(forced_measure)


def discover_candidates(seed_papers):
    """参考网络 + 领域搜索 + 每种措施搜索。"""
    candidates = {}
    seeds = choose_discovery_seeds(seed_papers)

    # 参考网络
    for paper in progress_iter(
        seeds,
        description="Reference network",
        unit="papers",
    ):
        item = paper["item"]
        seed_title = safe(item.get("data", {}).get("title"))
        work = openalex_work_for_zotero_item(item)

        if not work:
            continue

        if DISCOVER_FROM_REFERENCES:
            refs = openalex_batch_ids(
                (work.get("referenced_works", []) or [])[
                    :MAX_REFERENCES_PER_SEED
                ]
            )
            for ref in refs:
                merge_candidate(
                    candidates, ref, "reference", seed_title
                )

        if DISCOVER_FROM_RELATED:
            rels = openalex_batch_ids(
                (work.get("related_works", []) or [])[
                    :MAX_RELATED_PER_SEED
                ]
            )
            for rel in rels:
                merge_candidate(
                    candidates, rel, "related", seed_title
                )

        if DISCOVER_FROM_CITING:
            for citing in openalex_citing(
                work.get("id"),
                MAX_CITING_PER_SEED,
            ):
                merge_candidate(
                    candidates, citing, "citing", seed_title
                )

    # Pulse Tube / 低温领域
    if DISCOVER_FROM_TOPIC_SEARCH:
        for query in progress_iter(
            DOMAIN_SEARCH_QUERIES,
            description="Pulse-tube search",
            unit="queries",
        ):
            for work in openalex_search(
                query, SEARCH_RESULTS_PER_QUERY
            ):
                merge_candidate(
                    candidates, work, "domain_search", query
                )

    # 每种隔振措施单独扩展
    if DISCOVER_GENERIC_ISOLATION_METHODS:
        tasks = [
            (measure, query)
            for measure, queries in MEASURE_SEARCH_QUERIES.items()
            for query in queries
        ]

        for measure, query in progress_iter(
            tasks,
            description="Isolation search",
            unit="queries",
        ):
            for work in openalex_search(
                query, METHOD_SEARCH_RESULTS_PER_QUERY
            ):
                merge_candidate(
                    candidates,
                    work,
                    "measure_search",
                    query,
                    forced_measure=measure,
                )

    return list(candidates.values())


def _measure_match_score(work, measure):
    text = work_classification_text(work).casefold()
    words = MEASURE_RULES.get(measure, [])

    score = sum(
        3.0 for word in words
        if word.casefold() in text
    )

    if "vibration" in text:
        score += 1.5
    if "isolation" in text or "isolator" in text:
        score += 2.0

    cited = work.get("cited_by_count") or 0
    try:
        score += min(math.log10(int(cited) + 1), 2.0)
    except Exception:
        pass

    return round(score, 2)


def _select_discovery_shortlist(candidates):
    """保证每种措施都有机会补文献。"""
    # 普通领域候选
    domain = []

    for record in candidates:
        record["score"] = relevance_score(
            record["work"],
            record["sources"],
        )

        if any(
            x in record["sources"]
            for x in ("reference", "related", "citing", "domain_search")
        ):
            if record["score"] >= MIN_RELEVANCE_SCORE:
                domain.append(record)

    domain.sort(
        key=lambda r: (
            r["score"],
            r["work"].get("cited_by_count", 0) or 0,
        ),
        reverse=True,
    )

    chosen = domain[:MAX_NEW_PAPERS]
    used = {candidate_key(x["work"]) for x in chosen}

    # 文库里已经出现的措施优先多补
    observed_measures = {
        measure
        for cls in CLASSIFICATION_CACHE.values()
        for measure in cls.get("measures", [])
    }

    # 每种措施补充
    for measure in MEASURE_FOLDERS:
        target_count = MAX_METHOD_PAPERS_PER_MEASURE

        if measure in observed_measures:
            target_count += EXTRA_METHOD_PAPERS_FOR_LIBRARY_MATCH

        pool = [
            r for r in candidates
            if measure in r.get("forced_measures", [])
        ]

        for r in pool:
            r["measure_score"] = _measure_match_score(
                r["work"], measure
            )

        pool.sort(
            key=lambda r: (
                r.get("measure_score", 0),
                r["work"].get("cited_by_count", 0) or 0,
            ),
            reverse=True,
        )

        added = 0

        for r in pool:
            key = candidate_key(r["work"])

            if key in used:
                continue

            # 规则预筛，减少无关民用/结构工程文献
            rule = rule_content_classification(
                work_classification_text(r["work"])
            )

            if measure not in rule.get("measures", []):
                continue

            chosen.append(r)
            used.add(key)
            added += 1

            if added >= target_count:
                break

            if len(chosen) >= MAX_TOTAL_NEW_PAPERS:
                break

        if len(chosen) >= MAX_TOTAL_NEW_PAPERS:
            break

    return chosen[:MAX_TOTAL_NEW_PAPERS]


def _classify_discovery_records(routes, records):
    """Rule-first verification for discovered literature."""
    entries = []

    for i, record in enumerate(records):
        entries.append({
            "id": str(i),
            "title": work_title(
                record["work"]
            ),
            "text": work_classification_text(
                record["work"]
            ),
        })

    result = {}

    if not entries:
        return result

    classifications = classify_entries_fast(
        routes,
        entries,
    )

    for entry in entries:
        result[int(entry["id"])] = classifications.get(
            entry["id"],
            rule_content_classification(
                entry["text"]
            ),
        )

    return result

def openalex_to_zotero_template(zot, record):
    """只写简单内容标签。"""
    work = record["work"]
    template = safe_item_template(zot, "journalArticle")

    template["title"] = work_title(work)

    creators = []

    for name in work_authors(work):
        parts = name.split()

        if len(parts) >= 2:
            creators.append({
                "creatorType": "author",
                "firstName": " ".join(parts[:-1]),
                "lastName": parts[-1],
            })
        else:
            creators.append({
                "creatorType": "author",
                "name": name,
            })

    template["creators"] = creators
    template["abstractNote"] = work_abstract(work)
    template["publicationTitle"] = work_venue(work)
    template["date"] = safe(
        work.get("publication_date")
        or work.get("publication_year")
    )
    template["DOI"] = work_doi(work)
    template["url"] = work_landing_url(work)

    biblio = work.get("biblio") or {}
    template["volume"] = safe(biblio.get("volume"))
    template["issue"] = safe(biblio.get("issue"))

    first = safe(biblio.get("first_page"))
    last = safe(biblio.get("last_page"))

    if first and last:
        template["pages"] = first + "-" + last
    elif first:
        template["pages"] = first

    cls = record.get("classification", {})
    template["tags"] = [
        {"tag": x}
        for x in cls.get("tags", [])[:MAX_SIMPLE_TAGS]
    ]

    return template



def candidate_exists(record, doi_map, title_map):
    """Check whether a discovered paper already exists."""
    work = record["work"]
    doi = work_doi(work)

    if doi and doi in doi_map:
        return True

    title_n = norm_title(
        work_title(work)
    )

    return bool(
        title_n
        and title_n in title_map
    )


def prefetch_candidate_pdfs(
    records,
    doi_map,
    title_map,
    download_folder,
):
    """Optionally download OA PDFs; v21 defaults to metadata-only discovery."""
    if not DISCOVERY_DOWNLOAD_PDFS:
        return

    todo = [
        record
        for record in records
        if not candidate_exists(
            record,
            doi_map,
            title_map,
        )
    ]

    if not todo:
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(
            bar_width=26,
            complete_style="green",
            finished_style="green",
        ),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("[dim]papers[/dim]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=not KEEP_FINISHED_PROGRESS,
        expand=False,
    ) as progress:
        task = progress.add_task(
            "Download PDFs",
            total=len(todo),
        )

        with ThreadPoolExecutor(
            max_workers=PDF_DOWNLOAD_WORKERS
        ) as pool:
            future_map = {
                pool.submit(
                    download_work_pdf,
                    record["work"],
                    download_folder,
                ): record
                for record in todo
            }

            for future in as_completed(
                future_map
            ):
                record = future_map[future]

                try:
                    pdf_path, pdf_source = (
                        future.result()
                    )
                except Exception:
                    pdf_path, pdf_source = "", ""

                record["_pdf_path"] = pdf_path
                record["_pdf_source"] = pdf_source
                progress.advance(task)


def count_child_pdfs(zot, item_key):
    """Count child PDF attachments under one parent item."""
    try:
        count = 0

        for child in zot.children(
            item_key
        ):
            data = child.get("data", {})

            if data.get("itemType") != "attachment":
                continue

            content_type = safe(
                data.get("contentType")
            ).casefold()

            filename = safe(
                data.get("filename")
            ).casefold()

            if (
                "pdf" in content_type
                or filename.endswith(".pdf")
            ):
                count += 1

        return count

    except Exception:
        return 0


def import_candidate(
    zot,
    record,
    target_key,
    category_map,
    doi_map,
    title_map,
    download_folder,
):
    """Import metadata, classify it, and attach its OA PDF."""
    work = record["work"]
    cls = record.get(
        "classification",
        {},
    )

    doi = work_doi(work)
    title_n = norm_title(
        work_title(work)
    )

    existing = (
        doi_map.get(doi)
        if doi
        else None
    )

    if not existing and title_n:
        existing = title_map.get(
            title_n
        )

    extra = [
        target_key
    ] if target_key else []

    if existing:
        ok, error = write_item_classification(
            zot,
            existing,
            category_map,
            cls,
            extra_collections=extra,
        )

        if not ok:
            log(
                f"Existing item move failed: "
                f"{work_title(work)[:55]} | {error}",
                "warn",
            )

        item_key = safe(
            existing.get("key")
        )

        return {
            "status": "Existing",
            "item": zot.item(item_key),
            "pdf_path": "",
            "pdf_source": "",
            "pdf_attached": (
                count_child_pdfs(
                    zot,
                    item_key,
                ) > 0
            ),
        }

    # Use a prefetched PDF only when discovery PDF acquisition is enabled.
    pdf_path = ""
    pdf_source = ""

    if DISCOVERY_DOWNLOAD_PDFS:
        pdf_path = safe(
            record.get("_pdf_path")
        )
        pdf_source = safe(
            record.get("_pdf_source")
        )

        if not pdf_path:
            pdf_path, pdf_source = (
                download_work_pdf(
                    work,
                    download_folder,
                )
            )

        if not pdf_path:
            institution_pdf = find_institution_pdf_for_work(
                work
            )

            if institution_pdf:
                pdf_path = institution_pdf
                pdf_source = "InstitutionLocal"

    if (
        not pdf_path
        and not IMPORT_METADATA_WITHOUT_PDF
    ):
        return {
            "status": "NoOA",
            "item": None,
            "pdf_path": "",
            "pdf_source": "",
            "pdf_attached": False,
        }

    try:
        template = openalex_to_zotero_template(
            zot,
            record,
        )

        desired = classification_collection_keys(
            category_map,
            cls,
        )

        for key in extra:
            if key and key not in desired:
                desired.append(key)

        # One metadata write: item already lands in the new folders
        template["collections"] = desired
        template["tags"] = [
            {"tag": tag}
            for tag in cls.get(
                "tags",
                [],
            )[:MAX_SIMPLE_TAGS]
        ]

        created = zot.create_items(
            [template]
        )

        success = (
            created.get("success", {})
            if isinstance(created, dict)
            else {}
        )

        new_key = (
            success.get("0")
            if isinstance(success, dict)
            else ""
        )

        if not new_key:
            return {
                "status": "ImportFailed",
                "item": None,
                "pdf_path": pdf_path,
                "pdf_source": pdf_source,
                "pdf_attached": False,
            }

        item = zot.item(new_key)

    except Exception as e:
        return {
            "status": f"ImportFailed:{e}",
            "item": None,
            "pdf_path": pdf_path,
            "pdf_source": pdf_source,
            "pdf_attached": False,
        }

    pdf_attached = False

    # Child attachment: visible under the parent paper in its Collection
    if (
        pdf_path
        and UPLOAD_PDF_TO_ZOTERO
    ):
        try:
            result = zot.attachment_simple(
                [pdf_path],
                parentid=new_key,
            )

            pdf_attached = bool(result)

            # Verify once if the return value is unclear
            if not pdf_attached:
                pdf_attached = (
                    count_child_pdfs(
                        zot,
                        new_key,
                    ) > 0
                )

        except Exception as e:
            log(
                f"PDF upload failed: "
                f"{work_title(work)[:55]} | {e}",
                "warn",
            )

    if doi:
        doi_map[doi] = item

    if title_n:
        title_map[title_n] = item

    return {
        "status": (
            "ImportedPDF"
            if pdf_attached
            else (
                "ImportedMetadata"
                if not pdf_path
                else "ImportedPDFPending"
            )
        ),
        "item": item,
        "pdf_path": pdf_path,
        "pdf_source": pdf_source,
        "pdf_attached": pdf_attached,
    }

def run_auto_discovery(
    zot,
    seed_papers,
    target_key,
    by_key,
    paths,
    routes=None,
):
    """Discover, download, classify and import related literature."""
    if not AUTO_DISCOVER_RELATED:
        return []

    console.print()
    console.rule(
        "Literature discovery",
        style="dim",
    )

    candidates = discover_candidates(
        seed_papers
    )

    selected = _select_discovery_shortlist(
        candidates
    )

    log(
        f"Candidates: {len(candidates)} | "
        f"Review: {len(selected)}",
        "info",
    )

    # Rule-first; only ambiguous candidates use fast AI
    classifications = (
        _classify_discovery_records(
            routes,
            selected,
        )
    )

    verified = []

    for i, record in enumerate(
        selected
    ):
        cls = classifications.get(
            i,
            rule_content_classification(
                work_classification_text(
                    record["work"]
                )
            ),
        )

        record["classification"] = cls
        forced = record.get(
            "forced_measures",
            [],
        )

        if forced and not any(
            measure in cls.get(
                "measures",
                [],
            )
            for measure in forced
        ):
            if not any(
                source in record["sources"]
                for source in (
                    "reference",
                    "related",
                    "citing",
                    "domain_search",
                )
            ):
                continue

        if (
            not cls.get("sources")
            and not cls.get("measures")
            and record.get(
                "score",
                0,
            ) < MIN_RELEVANCE_SCORE + 2
        ):
            continue

        verified.append(record)

    doi_map, title_map = (
        all_library_index(zot)
    )

    # Use the already-created flat tree when target_key is empty
    if target_key:
        category_map = (
            ensure_category_collections(
                zot,
                target_key,
                by_key,
            )
        )
    else:
        category_map = (
            ensure_library_classification_tree(
                zot
            )
        )

    # Download new OA PDFs in parallel
    prefetch_candidate_pdfs(
        verified,
        doi_map,
        title_map,
        paths["download"],
    )

    results = []
    attached_count = 0

    for record in progress_iter(
        verified,
        description="Import + attach",
        unit="papers",
    ):
        imported = import_candidate(
            zot,
            record,
            target_key,
            category_map,
            doi_map,
            title_map,
            paths["download"],
        )

        work = record["work"]
        cls = record[
            "classification"
        ]

        if imported.get(
            "pdf_attached"
        ):
            attached_count += 1

        results.append({
            "Title": work_title(work),
            "DOI": work_doi(work),
            "Year": work_year(work),
            "Score": record.get(
                "score",
                0,
            ),
            "Source": ", ".join(
                SOURCE_TAGS.get(x, x)
                for x in cls.get(
                    "sources",
                    [],
                )
            ),
            "Isolation": ", ".join(
                MEASURE_TAGS.get(x, x)
                for x in cls.get(
                    "measures",
                    [],
                )
            ),
            "Tags": ", ".join(
                cls.get("tags", [])
            ),
            "Confidence": cls.get(
                "confidence",
                "",
            ),
            "Reason": cls.get(
                "reason",
                "",
            ),
            "FoundBy": ", ".join(
                record.get(
                    "sources",
                    [],
                )
            ),
            "Seed": " | ".join(
                record.get(
                    "seed_titles",
                    [],
                )[:3]
            ),
            "Status": imported[
                "status"
            ],
            "ZoteroKey": (
                safe(
                    imported["item"].get(
                        "key"
                    )
                )
                if imported.get("item")
                else ""
            ),
            "PDFSource": imported[
                "pdf_source"
            ],
            "PDFAttached": bool(
                imported.get(
                    "pdf_attached"
                )
            ),
        })

    paths["discovery"].write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log(
        f"Imported/updated: {len(results)} | "
        f"PDF attached: {attached_count}",
        "ok",
    )

    if VERIFY_COLLECTION_WRITES:
        verify_collection_counts(
            zot,
            category_map,
        )

    return results


def generated_classification_collection_keys(
    zot,
):
    """Return Sources/Isolation child Collection keys."""
    _, by_key, _ = collection_index(
        zot
    )

    sources_root = _top_collection_key(
        by_key,
        SOURCE_ROOT_NAME,
    )

    isolation_root = _top_collection_key(
        by_key,
        MEASURE_ROOT_NAME,
    )

    keys = set()

    for key, collection in by_key.items():
        if collection_parent(
            collection
        ) in {
            sources_root,
            isolation_root,
        }:
            keys.add(
                key
            )

    return keys


def classification_tag_set():
    """Tags that directly imply a Sources/Isolation classification."""
    return (
        set(
            SOURCE_TAGS.values()
        )
        | set(
            MEASURE_TAGS.values()
        )
    )


def papers_needing_organization(
    zot,
    papers,
):
    """Find unclassified or partially broken paper organization."""
    collection_keys = (
        generated_classification_collection_keys(
            zot
        )
    )

    class_tags = classification_tag_set()
    generated_tags = generated_tag_set()

    needs = []

    for paper in papers:
        item = paper["item"]
        data = item.get(
            "data",
            {},
        )

        tags = {
            safe(tag.get("tag"))
            for tag in (
                data.get(
                    "tags",
                    [],
                )
                or []
            )
            if isinstance(
                tag,
                dict,
            )
            and safe(
                tag.get("tag")
            )
        }

        collections = set(
            data.get(
                "collections",
                [],
            )
            or []
        )

        has_any_generated_tag = bool(
            tags
            & generated_tags
        )

        has_class_tag = bool(
            tags
            & class_tags
        )

        has_class_collection = bool(
            collections
            & collection_keys
        )

        # Main case requested by the user:
        # no generated tags AND no Sources/Isolation classification.
        completely_missing = (
            not has_any_generated_tag
            and not has_class_collection
        )

        # Repair partial write failures without reclassifying normal
        # background papers that only carry Cryogenic/Bolometer tags.
        partial_missing = (
            has_class_collection
            and not has_any_generated_tag
        ) or (
            has_class_tag
            and not has_class_collection
        )

        if (
            completely_missing
            or partial_missing
        ):
            needs.append(
                paper
            )

    return needs



def organization_gap_details(
    zot,
    papers,
):
    """Return actual missing classification fields for each paper."""
    collection_keys = (
        generated_classification_collection_keys(
            zot
        )
    )

    class_tags = classification_tag_set()
    generated_tags = generated_tag_set()

    details = []

    for paper in papers:
        item = paper["item"]
        data = item.get(
            "data",
            {},
        )

        title = safe(
            data.get("title")
        ) or "Untitled"

        tags = {
            safe(tag.get("tag"))
            for tag in (
                data.get(
                    "tags",
                    [],
                )
                or []
            )
            if isinstance(
                tag,
                dict,
            )
            and safe(
                tag.get("tag")
            )
        }

        collections = set(
            data.get(
                "collections",
                [],
            )
            or []
        )

        generated_present = sorted(
            tags
            & generated_tags
        )

        class_tag_present = sorted(
            tags
            & class_tags
        )

        class_collection_present = sorted(
            collections
            & collection_keys
        )

        # Background-only tags such as Cryogenic/0vbb/Bolometer count as a
        # complete classification without forcing an Isolation folder.
        has_generated_tag = bool(
            generated_present
        )

        has_engineering_tag = bool(
            class_tag_present
        )

        has_engineering_folder = bool(
            class_collection_present
        )

        completely_missing = (
            not has_generated_tag
            and not has_engineering_folder
        )

        broken_engineering_mapping = (
            has_engineering_tag
            and not has_engineering_folder
        )

        folder_without_tag = (
            has_engineering_folder
            and not has_generated_tag
        )

        if not (
            completely_missing
            or broken_engineering_mapping
            or folder_without_tag
        ):
            continue

        missing = []

        if not has_generated_tag:
            missing.append(
                "generated tag"
            )

        if (
            has_engineering_tag
            and not has_engineering_folder
        ):
            missing.append(
                "Sources/Isolation folder"
            )

        if (
            completely_missing
            and not missing
        ):
            missing.append(
                "classification"
            )

        details.append({
            "paper": paper,
            "key": safe(
                item.get("key")
            ),
            "title": title,
            "missing": missing,
            "tags": generated_present,
            "class_tags": class_tag_present,
            "collections": class_collection_present,
        })

    return details

def show_organization_gaps(
    details,
    heading="Organization gaps",
):
    """Print exact papers and the missing organization fields."""
    if not details:
        return

    console.print()
    console.rule(
        heading,
        style="dim",
    )

    for index, detail in enumerate(
        details,
        start=1,
    ):
        title = detail["title"]

        if len(title) > 88:
            title = title[:87] + "…"

        missing = ", ".join(
            detail["missing"]
        ) or "unknown"

        log(
            f"[{index}] {title}",
            "warn",
        )

        console.print(
            f"    Missing: {missing}",
            style="dim",
        )


def force_repair_remaining_organization(
    zot,
    details,
    category_map,
    routes,
):
    """Use fuller text and a forced second classification pass."""
    if not details:
        return 0, 0

    console.print()
    console.rule(
        "Targeted classification repair",
        style="dim",
    )

    entries = []

    for detail in progress_iter(
        details,
        description="Read unresolved papers",
        unit="papers",
    ):
        paper = detail["paper"]
        item = paper["item"]
        item_key = safe(
            item.get("key")
        )

        text_value = item_classification_text(
            zot,
            item,
            use_fulltext=True,
        )

        entries.append({
            "id": item_key,
            "title": safe(
                item.get(
                    "data",
                    {},
                ).get("title")
            ),
            "text": text_value,
            "item": item,
        })

    ai_result = {}

    if entries and routes:
        try:
            ai_result = ai_classify_batch(
                routes,
                entries,
            )
        except Exception as e:
            log(
                f"Targeted classification model failed: {e}",
                "warn",
            )

    fixed = 0
    failed = 0

    for entry in progress_iter(
        entries,
        description="Write targeted classification",
        unit="papers",
    ):
        item_key = entry["id"]

        # Always compute rules too, because the AI may omit obvious
        # background tags such as Cryogenic or 0vbb.
        rule_cls = rule_content_classification(
            entry["text"]
        )

        cls = ai_result.get(
            item_key
        ) or {
            "sources": [],
            "measures": [],
            "tags": [],
        }

        # Merge rule evidence into the AI result.
        sources = list(
            dict.fromkeys(
                list(
                    cls.get(
                        "sources",
                        [],
                    )
                )
                + list(
                    rule_cls.get(
                        "sources",
                        [],
                    )
                )
            )
        )

        measures = list(
            dict.fromkeys(
                list(
                    cls.get(
                        "measures",
                        [],
                    )
                )
                + list(
                    rule_cls.get(
                        "measures",
                        [],
                    )
                )
            )
        )

        tags = list(
            dict.fromkeys(
                list(
                    cls.get(
                        "tags",
                        [],
                    )
                )
                + list(
                    rule_cls.get(
                        "tags",
                        [],
                    )
                )
            )
        )[:MAX_SIMPLE_TAGS]

        cls = {
            **cls,
            "sources": sources,
            "measures": measures,
            "tags": tags,
        }

        # A background paper with a valid generated topic tag is already
        # classified. Do NOT force it into Other Methods.
        background_tags = {
            "Cryogenic",
            "0vbb",
            "Bolometer",
        }

        has_background_class = bool(
            set(tags)
            & background_tags
        )

        has_engineering_class = bool(
            sources
            or measures
        )

        if (
            not has_background_class
            and not has_engineering_class
            and not tags
        ):
            # Only use OtherIsolation when the paper actually discusses
            # vibration/isolation/mechanical behavior.
            low = entry[
                "text"
            ].casefold()

            engineering_terms = (
                "vibration",
                "vibrational",
                "isolation",
                "isolator",
                "mechanical noise",
                "microphonic",
                "damping",
                "resonance",
                "stiffness",
                "suspension",
            )

            if any(
                term in low
                for term in engineering_terms
            ):
                cls = {
                    "sources": [],
                    "measures": [
                        "OtherIsolation"
                    ],
                    "tags": [
                        MEASURE_TAGS[
                            "OtherIsolation"
                        ]
                    ],
                }

        CLASSIFICATION_CACHE[
            item_key
        ] = cls

        ok, error = write_item_classification(
            zot,
            entry["item"],
            category_map,
            cls,
        )

        if ok:
            fixed += 1
        else:
            failed += 1

            log(
                f"Targeted classification write failed: "
                f"{entry['title'][:65]} | {error}",
                "warn",
            )

    return fixed, failed

def repair_missing_organization(
    zot,
    papers,
    routes,
):
    """Repair only missing papers, then verify and force unresolved items."""
    if not REPAIR_INCOMPLETE_ORGANIZATION:
        return papers, 0

    missing = papers_needing_organization(
        zot,
        papers,
    )

    if not missing:
        log(
            "Organization gaps: 0",
            "ok",
        )
        return papers, 0

    console.print()
    console.rule(
        "Classification repair",
        style="dim",
    )

    log(
        f"Papers needing classification: {len(missing)}",
        "info",
    )

    category_map = (
        ensure_library_classification_tree(
            zot
        )
    )

    classify_and_tag_collection(
        zot,
        missing,
        "",
        category_map,
        routes,
    )

    # Refresh from Zotero after the first pass.
    _, _, cpaths = collection_index(
        zot
    )

    manual_items = collect_manual_items(
        zot
    )

    manual_keys = {
        safe(
            item.get("key")
        )
        for item in manual_items
    }

    refreshed = collect_whole_library_papers(
        zot,
        cpaths,
        manual_keys=manual_keys,
    )

    details = organization_gap_details(
        zot,
        refreshed,
    )

    if details:
        show_organization_gaps(
            details,
            heading="Unresolved classification",
        )

        fixed, failed = (
            force_repair_remaining_organization(
                zot,
                details,
                category_map,
                routes,
            )
        )

        log(
            f"Targeted repair: {fixed} fixed | {failed} failed",
            "ok" if failed == 0 else "warn",
        )

        # Final verification from a fresh Zotero read.
        _, _, cpaths = collection_index(
            zot
        )

        refreshed = collect_whole_library_papers(
            zot,
            cpaths,
            manual_keys=manual_keys,
        )

        final_details = organization_gap_details(
            zot,
            refreshed,
        )

        if final_details:
            show_organization_gaps(
                final_details,
                heading="Organization gaps remaining",
            )
        else:
            log(
                "Organization repair complete",
                "ok",
            )

    else:
        log(
            "Organization repair complete",
            "ok",
        )

    return refreshed, len(
        missing
    )


def paper_note_contract_report(
    zot,
    paper,
):
    """Fresh server-side verification of one bibliographic item's note contract."""
    item = paper[
        "item"
    ]

    item_key = safe(
        item.get("key")
    )

    title = safe(
        item.get(
            "data",
            {},
        ).get("title")
    ) or "Untitled"

    try:
        children = zot.children(
            item_key
        )
    except Exception as e:
        return {
            "valid": False,
            "paper": paper,
            "key": item_key,
            "title": title,
            "issues": [
                "cannot read children: "
                + safe(e)
            ],
        }

    deep_notes = []
    summary_notes = []

    for child in children:
        data = child.get(
            "data",
            {},
        )

        if data.get(
            "itemType"
        ) != "note":
            continue

        kind = generated_note_kind(
            data.get("note")
        )

        if kind == "deep":
            deep_notes.append(
                child
            )
        elif kind == "summary":
            summary_notes.append(
                child
            )

    issues = []

    if len(deep_notes) != 1:
        issues.append(
            f"deep-note count={len(deep_notes)}"
        )

    if len(summary_notes) != 1:
        issues.append(
            f"summary-note count={len(summary_notes)}"
        )

    if len(deep_notes) == 1:
        deep_html = safe(
            deep_notes[0].get(
                "data",
                {},
            ).get("note")
        )

        if not generated_note_has_title(
            deep_html,
            DEEP_NOTE_TITLE,
        ):
            issues.append(
                "deep note title is not 深度分析"
            )

        report = deep_analysis_quality_report(
            deep_html,
            require_pdf_citation=(
                "来源： PDF"
                in note_plain_text(
                    deep_html
                )
            ),
        )

        issues.extend(
            "deep: " + x
            for x in report["issues"]
        )

    if len(summary_notes) == 1:
        summary_html = safe(
            summary_notes[0].get(
                "data",
                {},
            ).get("note")
        )

        if not generated_note_has_title(
            summary_html,
            SUMMARY_NOTE_TITLE,
        ):
            issues.append(
                "summary note title is not 摘要"
            )

        report = summary_quality_report(
            summary_html
        )

        issues.extend(
            "summary: " + x
            for x in report["issues"]
        )

    return {
        "valid": not issues,
        "paper": paper,
        "key": item_key,
        "title": title,
        "issues": issues,
    }


def write_only_repair_one_paper_contract(
    zot,
    paper,
    results,
):
    """
    Repair 摘要/深度分析 using ONLY an already-saved valid Analysis.

    Zero AI calls. Zero PDF downloads. Zero /items/new calls.
    """
    item = paper["item"]
    item_key = safe(item.get("key"))
    title = safe(item.get("data", {}).get("title")) or "Untitled"

    children = zot.children(item_key)

    attachment_key = ""
    text_source = "Saved analysis"
    text_pages = ""
    image_pages = ""

    pdfs = [
        child
        for child in children
        if child.get("data", {}).get("itemType") == "attachment"
        and (
            safe(child.get("data", {}).get("contentType")).casefold()
            == "application/pdf"
            or safe(child.get("data", {}).get("filename")).casefold().endswith(".pdf")
        )
    ]

    if pdfs:
        attachment_key = safe(pdfs[0].get("key"))

    cached, row, issues = cached_analysis_for_paper(
        results,
        paper,
        require_pdf_citation=False,
    )

    if not cached:
        return False, (
            "No reusable saved Analysis: "
            + "; ".join(issues)
        )

    text_source = (
        safe(
            (row or {}).get(
                "TextSource"
            )
        )
        or "Saved analysis"
    )

    meta = {
        "model": safe((row or {}).get("Model")) or "Saved analysis",
        "api": safe((row or {}).get("API")) or "progress-cache",
    }

    # Write deep note first, then summary generated locally from the same text.
    write_ai_note(
        zot,
        item_key,
        cached,
        meta,
        attachment_key,
        text_source,
        text_pages,
        image_pages,
    )

    write_ai_summary_note(
        zot,
        item_key,
        cached,
        CLASSIFICATION_CACHE.get(item_key, {}),
        routes=[],
    )

    # Normalize/deduplicate fresh server-side children.
    children = zot.children(item_key)
    standardize_existing_analysis_notes(
        zot,
        item_key,
        children,
        routes=[],
    )

    report = paper_note_contract_report(
        zot,
        paper,
    )

    if report["valid"]:
        return True, ""

    return False, "; ".join(
        report["issues"]
    )


def write_repair_unresolved_from_progress(
    zot,
    unresolved,
    results,
):
    """
    First repair pass for unresolved note contracts.

    This pass is intentionally incapable of calling AI. If any paper cannot be
    repaired from saved progress, it is returned for later AI analysis.
    """
    repaired = 0
    remaining = []

    if not unresolved:
        return repaired, remaining

    console.print()
    console.rule(
        "Write-only repair from saved analysis",
        style="dim",
    )

    for report in progress_iter(
        unresolved,
        description="Restore saved analyses",
        unit="papers",
    ):
        paper = report["paper"]
        title = report["title"]

        try:
            ok, error = write_only_repair_one_paper_contract(
                zot,
                paper,
                results,
            )
        except Exception as e:
            ok = False
            error = safe(e)

        if ok:
            repaired += 1
            log(
                f"Restored without AI: {title[:70]}",
                "ok",
            )
        else:
            clean_error = re.sub(
                r"\s+",
                " ",
                safe(error),
            ).strip()

            log(
                f"Write-only repair failed: {title[:65]} | "
                f"{clean_error[:700]}",
                "warn",
            )

            remaining.append(
                report
            )

    return repaired, remaining

def regenerate_one_paper_contract(
    zot,
    paper,
    routes,
    paths,
    cached_row=None,
):
    """Re-read source evidence and overwrite/create the two required notes."""
    item = paper[
        "item"
    ]

    item_key = safe(
        item.get("key")
    )

    title = safe(
        item.get(
            "data",
            {},
        ).get("title")
    ) or "Untitled"

    # Give the PDF acquisition logic another chance before falling back.
    try:
        current_children = zot.children(
            item_key
        )

        if (
            ENSURE_PDF_CHILD
            and not has_pdf_child(
                current_children
            )
        ):
            ensure_pdf_child_for_item(
                zot,
                item,
                current_children,
                paths["download"],
            )
    except Exception:
        pass

    material = acquire_analysis_material(
        zot,
        item,
    )

    holder = material.get(
        "holder"
    )

    try:
        source = safe(
            material.get(
                "source"
            )
        )

        if not source:
            return False, (
                "No source or bibliographic metadata available"
            )

        require_pdf_citation = bool(
            safe(
                material.get(
                    "text_pages"
                )
            )
        )

        analysis = safe(
            (
                cached_row
                or {}
            ).get(
                "Analysis"
            )
        ).strip()

        meta = {
            "model": safe(
                (
                    cached_row
                    or {}
                ).get(
                    "Model"
                )
            )
            or "Saved analysis",
            "api": safe(
                (
                    cached_row
                    or {}
                ).get(
                    "API"
                )
            )
            or "progress-cache",
        }

        if analysis:
            cache_report = deep_analysis_quality_report(
                analysis,
                require_pdf_citation=(
                    require_pdf_citation
                ),
            )

            if not cache_report[
                "valid"
            ]:
                analysis = ""

        if analysis:
            log(
                f"Reuse saved analysis: {title[:70]}",
                "ok",
            )
        else:
            analysis, error, meta, _ = deep_analyze(
                routes,
                title,
                authors_from_item(
                    item
                ),
                year_from_item(
                    item
                ),
                norm_doi(
                    item.get(
                        "data",
                        {},
                    ).get("DOI")
                ),
                source,
                safe(
                    material.get(
                        "text_pages"
                    )
                ),
                material.get(
                    "images",
                    [],
                ),
                safe(
                    material.get(
                        "image_pages"
                    )
                ),
            )

            if not analysis:
                return False, (
                    error
                    or "Deep analysis failed"
                )

        write_ai_note(
            zot,
            item_key,
            analysis,
            meta,
            safe(
                material.get(
                    "attachment_key"
                )
            ),
            safe(
                material.get(
                    "text_source"
                )
            ),
            safe(
                material.get(
                    "text_pages"
                )
            ),
            safe(
                material.get(
                    "image_pages"
                )
            ),
        )

        write_ai_summary_note(
            zot,
            item_key,
            analysis,
            CLASSIFICATION_CACHE.get(
                item_key,
                {},
            ),
            routes=routes,
        )

        # Fresh cleanup/normalization after writes.
        children = zot.children(
            item_key
        )

        standardize_existing_analysis_notes(
            zot,
            item_key,
            children,
            routes=routes,
        )

        report = paper_note_contract_report(
            zot,
            paper,
        )

        if report["valid"]:
            return True, ""

        return False, "; ".join(
            report["issues"]
        )

    except Exception as e:
        return False, safe(
            e
        )

    finally:
        if holder:
            try:
                holder.cleanup()
            except Exception:
                pass


def enforce_final_note_contract(
    zot,
    papers,
    routes,
    paths,
    results=None,
):
    """
    Final server-side audit with a strict write-repair-first policy.

    Pass 1:
      - audit all papers;
      - try to restore unresolved notes from saved progress with ZERO AI calls.

    Only papers that have no reusable saved Analysis may proceed to AI
    regeneration, and only after the write-only path has been proven healthy.
    """
    results = results or []
    unresolved = []

    console.print()
    console.rule(
        "Final note audit 1/2",
        style="dim",
    )

    for paper in progress_iter(
        papers,
        description="Verify note contract",
        unit="papers",
    ):
        item_key = safe(
            paper["item"].get("key")
        )

        try:
            children = zot.children(item_key)
            standardize_existing_analysis_notes(
                zot,
                item_key,
                children,
                routes=[],
            )
        except Exception:
            pass

        report = paper_note_contract_report(
            zot,
            paper,
        )

        if not report["valid"]:
            unresolved.append(report)

    if not unresolved:
        log(
            f"Note contract complete: {len(papers)}/{len(papers)}",
            "ok",
        )
        return []

    log(
        f"Unresolved note contracts: {len(unresolved)}",
        "warn",
    )

    for report in unresolved:
        shown = report["title"]
        if len(shown) > 85:
            shown = shown[:84] + "…"

        console.print(
            f"[yellow]![/yellow] {shown}"
        )

        for issue in report["issues"]:
            console.print(
                f"    [dim]- {issue}[/dim]"
            )

    # --------------------------------------------------------
    # ZERO-AI write-only rescue.
    # --------------------------------------------------------
    repaired, remaining = write_repair_unresolved_from_progress(
        zot,
        unresolved,
        results,
    )

    if repaired:
        log(
            f"Write-only repairs completed: {repaired}",
            "ok",
        )

    # Re-audit immediately after write-only repair.
    second_unresolved = []

    console.print()
    console.rule(
        "Final note audit 2/2",
        style="dim",
    )

    for paper in progress_iter(
        papers,
        description="Verify note contract",
        unit="papers",
    ):
        report = paper_note_contract_report(
            zot,
            paper,
        )

        if not report["valid"]:
            second_unresolved.append(
                report
            )

    if not second_unresolved:
        log(
            f"Note contract complete: {len(papers)}/{len(papers)}",
            "ok",
        )
        return []

    # If write-only restoration itself produced a Zotero write failure,
    # STOP. Do not spend tokens proving the same write path is still broken.
    write_path_failures = []

    for report in second_unresolved:
        cached, row, cache_issues = cached_analysis_for_paper(
            results,
            report["paper"],
            require_pdf_citation=False,
        )

        if cached:
            write_path_failures.append(
                report
            )

    if (
        STOP_BEFORE_AI_IF_WRITE_REPAIR_STILL_FAILS
        and write_path_failures
    ):
        console.print()
        console.rule(
            "Write path still failing",
            style="red",
        )

        log(
            f"{len(write_path_failures)} paper(s) have valid saved analyses "
            "but still cannot be written to Zotero. AI regeneration is "
            "intentionally blocked to avoid wasting tokens.",
            "warn",
        )

        for report in write_path_failures:
            console.print(
                f"[yellow]![/yellow] {report['title']}"
            )
            for issue in report["issues"]:
                console.print(
                    f"    [dim]- {issue}[/dim]"
                )

        return second_unresolved

    # --------------------------------------------------------
    # Only genuinely uncached papers are allowed to use AI.
    # --------------------------------------------------------
    if WRITE_REPAIR_NEVER_CALL_AI:
        return second_unresolved

    console.print()
    console.rule(
        "AI regeneration for uncached papers only",
        style="dim",
    )

    for report in progress_iter(
        second_unresolved,
        description="Regenerate uncached notes",
        unit="papers",
    ):
        cached, _, _ = cached_analysis_for_paper(
            results,
            report["paper"],
            require_pdf_citation=False,
        )

        if cached:
            continue

        ok, error = regenerate_one_paper_contract(
            zot,
            report["paper"],
            routes,
            paths,
            cached_row=None,
        )

        if not ok:
            clean_error = re.sub(
                r"\s+",
                " ",
                safe(error),
            ).strip()

            log(
                f"Regeneration failed: {report['title'][:60]} | "
                f"{clean_error[:900]}",
                "warn",
            )

    final_unresolved = []

    for paper in papers:
        report = paper_note_contract_report(
            zot,
            paper,
        )

        if not report["valid"]:
            final_unresolved.append(
                report
            )

    return final_unresolved

def _standalone_pdf_parent_title(item):
    """Choose a useful parent title without inventing bibliographic metadata."""
    data = item.get(
        "data",
        {},
    )

    title = safe(
        data.get("title")
    ).strip()

    filename = safe(
        data.get("filename")
    ).strip()

    generic_titles = {
        "",
        "full text pdf",
        "pdf",
        "attachment",
        "document",
        "accepted manuscript",
    }

    if (
        title
        and title.casefold()
        not in generic_titles
    ):
        return title

    if filename:
        stem = Path(
            filename
        ).stem

        stem = re.sub(
            r"[_\-]+",
            " ",
            stem,
        )

        stem = re.sub(
            r"\s+",
            " ",
            stem,
        ).strip()

        if stem:
            return stem

    return (
        "Standalone PDF "
        + safe(
            item.get("key")
        )
    )


def promote_standalone_pdfs_to_documents(
    zot,
    pdfs,
):
    """
    Convert top-level standalone PDF attachments into document parents.

    The original PDF item is preserved and moved beneath the newly created
    document. Its current Collections/tags are copied to the parent. If the
    attachment move fails, the new parent is rolled back.
    """
    promoted = 0
    failed = 0

    if not pdfs:
        return promoted, failed

    console.print()
    console.rule(
        "Standalone PDF parent repair",
        style="dim",
    )

    for pdf in progress_iter(
        pdfs,
        description="Create PDF parents",
        unit="PDFs",
    ):
        pdf_key = safe(
            pdf.get("key")
        )

        if not pdf_key:
            failed += 1
            continue

        try:
            fresh_pdf = zot.item(
                pdf_key
            )

            pdata = fresh_pdf.get(
                "data",
                {},
            )

            if safe(
                pdata.get(
                    "parentItem"
                )
            ):
                continue

            template = safe_item_template(zot, 
                "document"
            )

            template[
                "title"
            ] = _standalone_pdf_parent_title(
                fresh_pdf
            )

            # Preserve useful top-level organization on the new parent.
            template[
                "collections"
            ] = list(
                pdata.get(
                    "collections",
                    [],
                )
                or []
            )

            template[
                "tags"
            ] = [
                {
                    "tag": safe(
                        tag.get("tag")
                    )
                }
                for tag in (
                    pdata.get(
                        "tags",
                        [],
                    )
                    or []
                )
                if isinstance(
                    tag,
                    dict,
                )
                and safe(
                    tag.get("tag")
                )
            ]

            if safe(
                pdata.get("url")
            ):
                template[
                    "url"
                ] = safe(
                    pdata.get("url")
                )

            created = zot.create_items(
                [template]
            )

            success = (
                created.get(
                    "success",
                    {},
                )
                if isinstance(
                    created,
                    dict,
                )
                else {}
            )

            parent_key = (
                success.get("0")
                if isinstance(
                    success,
                    dict,
                )
                else ""
            )

            if not parent_key:
                failed += 1
                log(
                    f"Standalone PDF parent creation failed: "
                    f"{_standalone_pdf_parent_title(fresh_pdf)[:60]}",
                    "warn",
                )
                continue

            def mutate_attachment(
                attachment,
            ):
                attachment[
                    "data"
                ][
                    "parentItem"
                ] = parent_key

                # Child attachments should inherit organization from their
                # bibliographic parent rather than remain top-level members.
                attachment[
                    "data"
                ][
                    "collections"
                ] = []

            ok, _, error = update_item_latest(
                zot,
                pdf_key,
                mutate_attachment,
            )

            if not ok:
                delete_item_latest(
                    zot,
                    parent_key,
                )

                failed += 1

                log(
                    f"Standalone PDF parent move failed: "
                    f"{pdf_key} | {error}",
                    "warn",
                )
                continue

            promoted += 1

        except Exception as e:
            failed += 1

            log(
                f"Standalone PDF promotion failed: "
                f"{pdf_key} | {e}",
                "warn",
            )

    log(
        f"Standalone PDFs promoted: {promoted} | Failed: {failed}",
        "ok" if failed == 0 else "warn",
    )

    return promoted, failed


def main():
    validate_config()

    ui_title(
        "Zotero Vibration Library",
        "Skip completed · Summary · Deep analysis · PDF",
    )

    zot = zotero_client()
    paths = output_paths()

    # Load resumable paid-for analysis state before any branch can use it.
    results = load_progress(
        paths,
        "WHOLE_LIBRARY",
    )

    if not isinstance(
        results,
        list,
    ):
        results = []

    results = [
        row
        for row in results
        if isinstance(
            row,
            dict,
        )
    ]

    duplicate_stats = deduplicate_library(
        zot
    )

    if duplicate_stats["groups"]:
        log(
            f"Duplicate groups: {duplicate_stats['groups']} | "
            f"Entries deleted: {duplicate_stats['deleted']} | "
            f"Children moved: {duplicate_stats['children_moved']}",
            "ok" if duplicate_stats["failed"] == 0 else "warn",
        )

    status = organization_status(zot)
    show_organization_status(status)

    already_organized = bool(
        SMART_ORGANIZATION_CHECK
        and status["ready"]
        and not FORCE_REBUILD_LIBRARY
    )

    routes = discover_ai_routes()
    discovery = []

    if BALANCED_MODE:
        console.print()
        console.rule("Balanced analysis mode", style="dim")
        log("PDF auto-download: OFF", "ok")
        log(
            "Deep analysis: one strong pass + max 1 quality retry",
            "ok",
        )
        log(
            f"PDF text: up to {SELECTED_TEXT_PAGES} selected pages / "
            f"{MAX_INPUT_CHARS} chars",
            "ok",
        )
        log(
            f"Vision: up to {MAX_VISION_PAGES} selected pages",
            "ok",
        )
        log(
            "Summary: local extraction from validated deep analysis (0 AI calls)",
            "ok",
        )
        if PULSE_TUBE_EXPANSION_ENABLED:
            log(
                "Focused PT literature expansion: ON (metadata/abstracts only; no PDF download)",
                "ok",
            )

    # Always initialize summary/state variables before branching.
    # This prevents final-report crashes when the library takes the
    # "already organized" resume path.
    manuals = []
    manual_keys = set()
    papers = []
    standalone_pdfs = []

    if already_organized:
        console.print()
        console.rule("Resume", style="dim")
        log(
            "Library already organized -> Deep analysis",
            "ok",
        )

        _, _, cpaths = collection_index(zot)

        manuals = collect_manual_items(zot)
        manual_keys = {
            safe(item.get("key"))
            for item in manuals
        }

        standalone_pdfs = collect_standalone_pdfs(
            zot,
            manual_keys,
        )

        papers = collect_whole_library_papers(
            zot,
            cpaths,
            manual_keys=manual_keys,
        )

        if RUN_DISCOVERY_IF_ALREADY_ORGANIZED:
            discovery = run_auto_discovery(
                zot,
                papers,
                "",
                {},
                paths,
                routes,
            )

            _, _, cpaths = collection_index(zot)

            papers = collect_whole_library_papers(
                zot,
                cpaths,
                manual_keys=manual_keys,
            )

    else:
        hard_reset_before_rebuild(
            zot,
            paths,
        )

        _, by_key, cpaths = collection_index(zot)

        manuals = collect_manual_items(zot)
        manual_keys = {
            safe(item.get("key"))
            for item in manuals
        }

        standalone_pdfs = collect_standalone_pdfs(
            zot,
            manual_keys,
        )

        papers = collect_whole_library_papers(
            zot,
            cpaths,
            manual_keys=manual_keys,
        )

        log(
            f"Papers: {len(papers)}",
            "ok",
        )
        log(
            f"Manuals: {len(manuals)}",
            "ok",
        )
        log(
            f"Standalone PDFs: {len(standalone_pdfs)}",
            "ok",
        )

        if not papers and not manuals and not standalone_pdfs:
            log(
                "No library items found.",
                "warn",
            )
            return

        category_map = ensure_library_classification_tree(
            zot
        )

        manuals_added = add_manuals_to_folder(
            zot,
            category_map,
            manuals,
        )

        log(
            f"Manuals classified: {manuals_added}",
            "ok",
        )

        standalone_moved = classify_standalone_pdfs(
            zot,
            standalone_pdfs,
            category_map,
            routes,
        )

        if standalone_pdfs:
            log(
                f"Standalone PDFs moved: {standalone_moved}",
                "ok",
            )

        console.print()
        console.rule(
            "Fast classification",
            style="dim",
        )

        classify_and_tag_collection(
            zot,
            papers,
            "",
            category_map,
            routes,
        )

        if RUN_DISCOVERY_AFTER_REBUILD:
            discovery = run_auto_discovery(
                zot,
                papers,
                "",
                by_key,
                paths,
                routes,
            )

        _, _, cpaths2 = collection_index(zot)

        papers = collect_whole_library_papers(
            zot,
            cpaths2,
            manual_keys=manual_keys,
        )

        final_status = organization_status(zot)

        if not final_status["ready"]:
            log(
                "Organization completed but readiness threshold was not met.",
                "warn",
            )
        else:
            log(
                "Library organization complete",
                "ok",
            )

    # READY means no full rebuild is needed.
    # Still repair only papers that have no tags/classification.
    papers, repaired_count = repair_missing_organization(
        zot,
        papers,
        routes,
    )

    if repaired_count:
        log(
            f"Newly classified/repaired: {repaired_count}",
            "ok",
        )

    if (
        ENFORCE_NOTE_CONTRACT_FOR_ALL_BIBLIOGRAPHIC_ITEMS
        and PROMOTE_STANDALONE_PDFS_FOR_NOTE_CONTRACT
    ):
        # A standalone attachment cannot satisfy the requested
        # Paper -> 摘要 / 深度分析 / PDF contract as a normal bibliographic
        # record. Promote it to a document parent while preserving the PDF.
        current_standalone_pdfs = collect_standalone_pdfs(
            zot,
            manual_keys=set(),
        )

        promoted_count, promotion_failures = (
            promote_standalone_pdfs_to_documents(
                zot,
                current_standalone_pdfs,
            )
        )

        if promotion_failures:
            log(
                f"Standalone PDF parent failures: "
                f"{promotion_failures}",
                "warn",
            )

    if ENFORCE_NOTE_CONTRACT_FOR_ALL_BIBLIOGRAPHIC_ITEMS:
        # Notes are required for every paper-like bibliographic item,
        # including items placed in Manuals and newly promoted PDF parents.
        _, _, analysis_cpaths = collection_index(
            zot
        )

        papers = collect_whole_library_papers(
            zot,
            analysis_cpaths,
            manual_keys=set(),
        )

        log(
            f"Analysis/note-contract targets: {len(papers)}",
            "ok",
        )

    # Build child index once: notes + PDFs for every analysis target.
    child_index = build_child_index(
        zot
    )

    analysis_state = {}
    already_analyzed = 0
    summary_ready = 0
    pdf_ready = 0

    duplicate_notes_deleted = 0
    duplicate_notes_failed = 0
    deep_titles_fixed = 0
    summary_titles_fixed = 0
    deep_non_chinese = 0
    deep_quality_failed = 0
    summaries_regenerated = 0

    for paper in progress_iter(
        papers,
        description="Check paper children",
        unit="papers",
    ):
        item = paper["item"]
        item_key = safe(
            item.get("key")
        )

        children = child_index.get(
            item_key,
            [],
        )

        state = standardize_existing_analysis_notes(
            zot,
            item_key,
            children,
            routes=routes,
        )

        analysis_state[
            item_key
        ] = state

        duplicate_notes_deleted += int(
            state.get(
                "duplicate_notes_deleted",
                0,
            )
            or 0
        )

        duplicate_notes_failed += int(
            state.get(
                "duplicate_notes_failed",
                0,
            )
            or 0
        )

        deep_titles_fixed += int(
            state.get(
                "deep_titles_fixed",
                0,
            )
            or 0
        )

        summary_titles_fixed += int(
            state.get(
                "summary_titles_fixed",
                0,
            )
            or 0
        )

        deep_non_chinese += int(
            state.get(
                "deep_non_chinese",
                0,
            )
            or 0
        )

        deep_quality_failed += int(
            state.get(
                "deep_quality_failed",
                0,
            )
            or 0
        )

        summaries_regenerated += int(
            state.get(
                "summaries_regenerated",
                0,
            )
            or 0
        )

        if state["deep_exists"]:
            already_analyzed += 1

        if state["summary_exists"]:
            summary_ready += 1

        if has_pdf_child(
            children
        ):
            pdf_ready += 1
        elif ENSURE_PDF_CHILD:
            if ensure_pdf_child_for_item(
                zot,
                item,
                children,
                paths["download"],
            ):
                pdf_ready += 1

    console.print()
    console.rule(
        "Generated note audit",
        style="dim",
    )

    log(
        f"Duplicate generated notes deleted: {duplicate_notes_deleted}",
        "ok",
    )

    if duplicate_notes_failed:
        log(
            f"Duplicate generated notes not deleted: {duplicate_notes_failed}",
            "warn",
        )
    else:
        log(
            "Duplicate generated note delete failures: 0",
            "ok",
        )

    log(
        f"Deep note titles fixed: {deep_titles_fixed}",
        "ok",
    )

    log(
        f"Summary note titles fixed: {summary_titles_fixed}",
        "ok",
    )

    if deep_non_chinese:
        log(
            f"Non-Chinese deep notes queued for regeneration: "
            f"{deep_non_chinese}",
            "warn",
        )
    else:
        log(
            "Non-Chinese deep notes queued for regeneration: 0",
            "ok",
        )

    if deep_quality_failed:
        log(
            f"Deep notes failing content-quality audit: "
            f"{deep_quality_failed}",
            "warn",
        )
    else:
        log(
            "Deep notes failing content-quality audit: 0",
            "ok",
        )

    log(
        f"Chinese summaries created/regenerated: "
        f"{summaries_regenerated}",
        "ok",
    )

    log(
        f"Progress rows loaded for resume: {len(results)}",
        "ok" if results else "info",
    )

    # ========================================================
    # PRE-AI WRITE-ONLY RESCUE
    # ========================================================
    # Before spending a single new model token, try to restore every missing
    # deep note whose already-paid Analysis exists in progress.json.
    #
    # If such a cached analysis cannot be written to Zotero, STOP immediately:
    # there is no reason to regenerate text while the write path is broken.
    pre_ai_candidates = [
        paper
        for paper in papers
        if not analysis_state.get(
            safe(
                paper["item"].get(
                    "key"
                )
            ),
            {},
        ).get(
            "deep_exists",
            False,
        )
    ]

    cached_restore_reports = []

    for paper in pre_ai_candidates:
        cached_analysis, cached_row, cache_issues = cached_analysis_for_paper(
            results,
            paper,
            require_pdf_citation=False,
        )

        if cached_analysis:
            cached_restore_reports.append({
                "valid": False,
                "paper": paper,
                "key": safe(
                    paper["item"].get("key")
                ),
                "title": safe(
                    paper["item"].get(
                        "data",
                        {},
                    ).get("title")
                ) or "Untitled",
                "issues": [
                    "deep note missing in Zotero; valid Analysis exists in progress"
                ],
            })
        else:
            # No reusable saved analysis: this paper may enter the normal
            # deep-analysis queue only after the write path is proven healthy.
            pass

    if cached_restore_reports:
        console.print()
        console.rule(
            "Pre-AI write-only recovery",
            style="dim",
        )

        log(
            f"Saved analyses ready for zero-AI restore: "
            f"{len(cached_restore_reports)}",
            "ok",
        )

        repaired, still_failed = write_repair_unresolved_from_progress(
            zot,
            cached_restore_reports,
            results,
        )

        log(
            f"Restored before AI: {repaired}/"
            f"{len(cached_restore_reports)}",
            "ok" if not still_failed else "warn",
        )

        if still_failed:
            console.print()
            console.rule(
                "Zotero write repair failed",
                style="red",
            )

            log(
                "AI analysis is blocked because valid saved Analysis text "
                "already exists for these papers but Zotero still cannot "
                "accept the notes. This protects your token balance.",
                "warn",
            )

            for report in still_failed:
                console.print(
                    f"[yellow]![/yellow] {report['title']}"
                )

            save_all(
                paths,
                "WHOLE_LIBRARY",
                "My Library",
                results,
                discovery,
            )

            raise RuntimeError(
                "Pre-AI Zotero write-only recovery failed. "
                "No new deep-analysis calls were allowed after this failure."
            )

        # Refresh children and state after successful restore so those papers
        # disappear from the AI queue immediately.
        child_index = build_child_index(
            zot
        )

        for paper in papers:
            item_key = safe(
                paper["item"].get("key")
            )

            children = child_index.get(
                item_key,
                [],
            )

            analysis_state[item_key] = standardize_existing_analysis_notes(
                zot,
                item_key,
                children,
                routes=[],
            )

        already_analyzed = sum(
            1
            for state in analysis_state.values()
            if state.get(
                "deep_exists",
                False,
            )
        )

        summary_ready = sum(
            1
            for state in analysis_state.values()
            if state.get(
                "summary_exists",
                False,
            )
        )

        pdf_ready = sum(
            1
            for paper in papers
            if has_pdf_child(
                child_index.get(
                    safe(
                        paper["item"].get(
                            "key"
                        )
                    ),
                    [],
                )
            )
        )

    # ========================================================
    # FOCUSED PULSE-TUBE RESEARCH EXPANSION
    # ========================================================
    # This runs only after the old-library write-only recovery path has passed.
    # Therefore we do not spend discovery/deep-analysis tokens while a known
    # Zotero note-write problem is unresolved.
    if (
        PULSE_TUBE_EXPANSION_ENABLED
        and pulse_tube_expansion_due(
            paths
        )
    ):
        console.print()
        console.rule(
            "Pulse-tube research expansion",
            style="dim",
        )

        log(
            "Searching: PT principle -> vibration generation -> "
            "transfer paths -> isolation -> transferable methods",
            "info",
        )

        discovery = run_auto_discovery(
            zot,
            papers,
            "",
            {},
            paths,
            routes,
        )

        mark_pulse_tube_expansion_done(
            paths,
            len(
                discovery
                or []
            ),
        )

        # Refresh the entire analysis target after metadata imports.
        _, _, expansion_cpaths = collection_index(
            zot
        )

        papers = collect_whole_library_papers(
            zot,
            expansion_cpaths,
            manual_keys=set(),
        )

        child_index = build_child_index(
            zot
        )

        analysis_state = {}

        for paper in progress_iter(
            papers,
            description="Refresh expanded library",
            unit="papers",
        ):
            item_key = safe(
                paper["item"].get(
                    "key"
                )
            )

            children = child_index.get(
                item_key,
                [],
            )

            analysis_state[
                item_key
            ] = standardize_existing_analysis_notes(
                zot,
                item_key,
                children,
                routes=[],
            )

        already_analyzed = sum(
            1
            for state in analysis_state.values()
            if state.get(
                "deep_exists",
                False,
            )
        )

        summary_ready = sum(
            1
            for state in analysis_state.values()
            if state.get(
                "summary_exists",
                False,
            )
        )

        pdf_ready = sum(
            1
            for paper in papers
            if has_pdf_child(
                child_index.get(
                    safe(
                        paper["item"].get(
                            "key"
                        )
                    ),
                    [],
                )
            )
        )

        log(
            f"Expanded analysis targets: {len(papers)}",
            "ok",
        )

    pending_papers = [
        paper
        for paper in papers
        if not analysis_state.get(
            safe(
                paper["item"].get(
                    "key"
                )
            ),
            {},
        ).get(
            "deep_exists",
            False,
        )
    ]

    if MAX_ANALYSIS_PAPERS > 0:
        pending_papers = pending_papers[
            :MAX_ANALYSIS_PAPERS
        ]

    console.print()
    console.rule(
        "Analysis status",
        style="dim",
    )

    log(
        f"Already analyzed: {already_analyzed}",
        "ok",
    )
    log(
        f"Need analysis: {len(pending_papers)}",
        "info",
    )
    log(
        f"Summaries ready: {summary_ready}/{len(papers)}",
        "ok" if summary_ready else "info",
    )
    log(
        f"PDF children ready: {pdf_ready}/{len(papers)}",
        "ok" if pdf_ready else "warn",
    )

    # results was loaded at startup before the Pre-AI recovery pass.
    completed = {
        r.get("ZoteroKey")
        for r in results
        if r.get("Status") == "Done"
    }

    number_map = {
        r.get("ZoteroKey"): r.get("No")
        for r in results
        if r.get("ZoteroKey")
    }

    next_num = max(
        [
            x
            for x in number_map.values()
            if isinstance(x, int)
        ],
        default=0,
    ) + 1

    console.print()
    console.rule("Deep analysis", style="dim")
    log(
        f"To process: {len(pending_papers)}",
        "info",
    )

    for current_no, total_count, paper, set_stage in analysis_progress_iter(
        pending_papers
    ):
        item = paper["item"]
        data = item.get("data", {})
        item_key = safe(item.get("key"))

        number = number_map.get(item_key)

        if not number:
            number = next_num
            next_num += 1
            number_map[item_key] = number

        title = safe(
            data.get("title")
        ) or "Untitled"

        if SHOW_CURRENT_PAPER:
            log(
                f"Current paper [{current_no}/{total_count}]: "
                f"{title}",
                "debug",
            )

        authors = authors_from_item(item)
        year = year_from_item(item)
        doi = norm_doi(data.get("DOI"))
        abstract = safe(data.get("abstractNote"))

        collections_text = " | ".join(
            paper.get("collections", [])
        )

        set_stage(
            "Reading PDF"
        )

        pdf_path, att, holder, pdf_source = resolve_pdf(
            zot,
            item_key,
        )

        attachment_key = (
            safe(att.get("key"))
            if att
            else ""
        )

        source = ""
        text_source = ""
        text_pages = ""
        image_pages = ""
        images = []

        if pdf_path:
            try:
                set_stage(
                    "Selecting pages"
                )

                scan = scan_pdf(pdf_path)
                pages = choose_text_pages(scan)

                text_pages = ", ".join(
                    str(x["number"])
                    for x in pages
                    if x["text"]
                )

                pdf_text = build_pdf_text(pages)

                if (
                    scan["chars"] >= MIN_PDF_TEXT_CHARS
                    and pdf_text
                ):
                    source = pdf_text
                    text_source = "PDF"

                    if abstract:
                        source = (
                            "[Abstract]\n"
                            + abstract
                            + "\n\n"
                            + source
                        )

                elif abstract:
                    source = "[Abstract]\n" + abstract
                    text_source = "Abstract + images"

                idxs = choose_image_pages(scan)

                set_stage(
                    "Rendering figures"
                )

                images, nums = render_images(
                    pdf_path,
                    idxs,
                )

                image_pages = ", ".join(
                    str(x)
                    for x in nums
                )

            except Exception as e:
                log(
                    f"PDF parse failed: {title[:55]} | {e}",
                    "warn",
                )

        if not source and att:
            fulltext = indexed_fulltext(
                zot,
                att,
            )

            if fulltext:
                source = fulltext
                text_source = "Zotero full text"

        if not source and abstract:
            source = abstract
            text_source = "Abstract"

        if not source:
            source, text_source = fallback_analysis_source(
                item
            )

        cls = CLASSIFICATION_CACHE.get(
            item_key,
            {},
        )

        row = {
            "No": number,
            "ZoteroKey": item_key,
            "Title": title,
            "Authors": authors,
            "Year": year,
            "DOI": doi,
            "Collections": collections_text,
            "Source": ", ".join(
                SOURCE_TAGS.get(x, x)
                for x in cls.get("sources", [])
            ),
            "Isolation": ", ".join(
                MEASURE_TAGS.get(x, x)
                for x in cls.get("measures", [])
            ),
            "Tags": ", ".join(
                cls.get("tags", [])
            ),
            "Status": "",
            "Grade": "",
            "Summary": "",
            "PDF": pdf_source,
            "TextSource": text_source,
            "Zotero": "",
            "Model": "",
            "API": "",
            "Evidence": "",
            "Analysis": "",
            "Error": "",
        }

        if not source:
            set_stage(
                "No usable content"
            )

            row["Status"] = "NoContent"
            row["Error"] = "No PDF, full text, or abstract"

            set_stage(
                "Saving HTML"
            )

            upsert(results, row)

            if SAVE_AFTER_EACH_PAPER:
                save_all(
                    paths,
                    "WHOLE_LIBRARY",
                    "My Library",
                    results,
                    discovery,
                )

            if holder:
                holder.cleanup()

            continue

        cached_analysis, cached_row, _ = cached_analysis_for_paper(
            results,
            paper,
            require_pdf_citation=False,
        )

        if cached_analysis:
            set_stage(
                "Reusing saved analysis"
            )

            summary = cached_analysis
            error = None
            evidence = safe(
                (
                    cached_row
                    or {}
                ).get(
                    "Evidence"
                )
            )
            meta = {
                "model": safe(
                    (
                        cached_row
                        or {}
                    ).get(
                        "Model"
                    )
                )
                or "Saved analysis",
                "api": safe(
                    (
                        cached_row
                        or {}
                    ).get(
                        "API"
                    )
                )
                or "progress-cache",
            }

            log(
                f"Reuse saved valid analysis without AI: "
                f"{title[:70]}",
                "ok",
            )
        else:
            summary, error, meta, evidence = deep_analyze(
                routes,
                title,
                authors,
                year,
                doi,
                source,
                text_pages,
                images,
                image_pages,
                stage_callback=set_stage,
            )

        row["Evidence"] = evidence
        row["Model"] = safe(meta.get("model"))
        row["API"] = safe(meta.get("api"))

        if not summary:
            row["Status"] = "AIError"
            row["Error"] = error or ""

        else:
            try:
                set_stage(
                    "Writing Zotero notes"
                )

                deep_status = write_ai_note(
                    zot,
                    item_key,
                    summary,
                    meta,
                    attachment_key,
                    text_source,
                    text_pages,
                    image_pages,
                )

                summary_status = write_ai_summary_note(
                    zot,
                    item_key,
                    summary,
                    cls,
                    routes=routes,
                )

                zstatus = (
                    f"Deep:{deep_status}; "
                    f"Summary:{summary_status}"
                )

            except Exception as e:
                zstatus = "Write failed: " + str(e)

            row["Analysis"] = summary
            row["Grade"] = extract_grade(summary)
            row["Summary"] = extract_one_line(summary)
            row["Zotero"] = zstatus

            if zstatus.startswith(
                "Write failed:"
            ):
                row["Status"] = "WriteError"
                row["Error"] = zstatus
            else:
                # Fresh server verification: do not mark Done merely because
                # create/update returned without raising.
                contract = paper_note_contract_report(
                    zot,
                    paper,
                )

                if contract["valid"]:
                    row["Status"] = "Done"
                    completed.add(
                        item_key
                    )
                else:
                    row["Status"] = "WriteError"
                    row["Error"] = "; ".join(
                        contract[
                            "issues"
                        ]
                    )

        set_stage(
            "Saving HTML"
        )

        upsert(results, row)

        if SAVE_AFTER_EACH_PAPER:
            save_all(
                paths,
                "WHOLE_LIBRARY",
                "My Library",
                results,
                discovery,
            )

        if holder:
            holder.cleanup()

        set_stage(
            "Completed"
        )

        time.sleep(SLEEP_SECONDS)

    save_all(
        paths,
        "WHOLE_LIBRARY",
        "My Library",
        results,
        discovery,
    )

    remaining_standalone = collect_standalone_pdfs(
        zot,
        manual_keys=set(),
    )

    if remaining_standalone:
        console.print()
        console.rule(
            "[bold red]Standalone PDF contract failure[/bold red]",
            style="dim",
        )

        for pdf in remaining_standalone:
            console.print(
                "[red]![/red] "
                + _standalone_pdf_parent_title(
                    pdf
                )
            )

        raise RuntimeError(
            f"{len(remaining_standalone)} standalone PDF(s) still have no "
            "bibliographic parent, so the requested note contract cannot "
            "be guaranteed for every literature item."
        )

    final_unresolved = enforce_final_note_contract(
        zot,
        papers,
        routes,
        paths,
        results=results,
    )

    save_all(
        paths,
        "WHOLE_LIBRARY",
        "My Library",
        results,
        discovery,
    )

    if final_unresolved:
        console.print()
        console.rule(
            "[bold red]Incomplete note contract[/bold red]",
            style="dim",
        )

        log(
            f"Items still missing/invalid: {len(final_unresolved)}",
            "warn",
        )

        for report in final_unresolved:
            console.print(
                f"[red]![/red] {report['title']}"
            )

            for issue in report[
                "issues"
            ]:
                console.print(
                    f"    [dim]- {issue}[/dim]"
                )

        raise RuntimeError(
            "Final Zotero note-contract audit failed. "
            "The script did not mark the library complete because "
            f"{len(final_unresolved)} bibliographic item(s) still lack "
            "a valid named Chinese 摘要/深度分析."
        )

    try:
        generate_pulse_tube_design_guide(
            routes,
            results,
            paths,
        )
    except Exception as e:
        log(
            f"Design guide generation failed without affecting Zotero: "
            f"{safe(e)[:600]}",
            "warn",
        )

    console.print()
    console.rule("[bold green]Done[/bold green]", style="dim")

    success_count = sum(
        1
        for r in results
        if r.get("Status") == "Done"
    )

    failed_count = sum(
        1
        for r in results
        if r.get("Status") in ("AIError", "NoContent", "WriteError")
    )

    # Final reporting must never invalidate a completed analysis run.
    print_summary([
        ("Library papers", len(papers or [])),
        ("Manuals", len(manuals or [])),
        ("Standalone PDFs", len(standalone_pdfs or [])),
        ("Discovered", len(discovery or [])),
        ("Analyzed", success_count),
        ("Failed / no content", failed_count),
    ])

    console.print()
    console.print(
        "[dim]Output[/dim]  "
        f"[bold]{paths['root']}[/bold]"
    )


if __name__ == "__main__":
    main()
