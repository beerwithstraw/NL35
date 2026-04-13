"""
Base NL-35 extraction helpers.

Core functions:
  get_nl35_pages(pdf)         — filter pages that contain NL-35 content
  detect_period_columns(table) — map col indices to 8 canonical period-metric keys
  detect_lob_rows(table)       — map row indices to canonical LOB keys
  extract_nl35_grid(...)       — fill NL35Data from a detected table
  parse_header_driven_nl35(...) — one-liner entry point for simple company parsers
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

from extractor.models import NL35Data, NL35Extract
from extractor.normaliser import clean_number, normalise_text
from config.row_registry import NL35_LOB_ALIASES, NL35_SKIP_PATTERNS
from config.company_registry import COMPANY_DISPLAY_NAMES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page detection
# ---------------------------------------------------------------------------

_NL35_RE = re.compile(
    r"(FORM\s+NL[-\s]?35|QUARTERLY\s+BUSINESS\s+RETURNS|LINE\s+OF\s+BUSINESS)",
    re.IGNORECASE,
)
_SMALL_PDF_PAGE_THRESHOLD = 4


def get_nl35_pages(pdf) -> list:
    """
    Return pages from the pdfplumber PDF object that contain NL-35 content.
    For small PDFs (≤ threshold), returns all pages.
    """
    if len(pdf.pages) <= _SMALL_PDF_PAGE_THRESHOLD:
        return list(pdf.pages)

    result = []
    for page in pdf.pages:
        try:
            text = page.extract_text() or ""
            if _NL35_RE.search(text):
                result.append(page)
        except Exception:
            result.append(page)

    return result if result else list(pdf.pages)


# ---------------------------------------------------------------------------
# Period column detection
# ---------------------------------------------------------------------------

# Period span label → canonical group prefix
# More-specific patterns first; last pattern wins within a cell if multiple match.
_PERIOD_LABEL_MAP = [
    # Standard NL-35 headers
    (re.compile(r"up\s+to\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_ytd"),
    (re.compile(r"for\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_qtr"),
    (re.compile(r"upto\s+the\s+quarter|up\s+to\s+the\s+quarter", re.IGNORECASE), "cy_ytd"),
    (re.compile(r"for\s+the\s+quarter", re.IGNORECASE), "cy_qtr"),
    # N-month variants (e.g. "For the 9 months ended …")
    (re.compile(r"for\s+the\s+(?:9|nine)\s+months?\s+ended.{0,80}previous\s+year", re.IGNORECASE | re.DOTALL), "py_ytd"),
    (re.compile(r"for\s+the\s+(?:9|nine)\s+months?\s+ended", re.IGNORECASE), "cy_ytd"),
    (re.compile(r"for\s+the\s+(?:3|three)\s+months?\s+ended.{0,80}previous\s+year", re.IGNORECASE | re.DOTALL), "py_qtr"),
    (re.compile(r"for\s+the\s+(?:3|three)\s+months?\s+ended", re.IGNORECASE), "cy_qtr"),
]
# Note: "For the period ended YYYY" (ZUNO YTD) is handled in _fy_quarter_patterns()
# because it requires knowing the fiscal year to distinguish CY vs PY.


def _fy_quarter_patterns(fy_year: str) -> list:
    """
    Build FY-quarter style period patterns for a given fiscal year string.

    Accepts two formats:
      '2026'   — FY end year (4-digit); CY start = int(fy_year) - 1
      '202526' — year_code (6-digit, pipeline format); CY start = first 4 digits

    Matches headers like:
      'For Q3 2025-26'  / 'For Q3\\n2025-26'   → cy_qtr
      'Upto Q3 2025-26' / 'Up to Q3\\n2025-26'  → cy_ytd
      'For Q3 2024-25'                           → py_qtr
      'Upto Q3 2024-25'                          → py_ytd

    Returns an empty list if fy_year is blank or an unrecognised format.
    """
    if not fy_year or not fy_year.isdigit():
        return []
    if len(fy_year) == 6:
        # Pipeline year_code format: e.g. "202526" → CY start = 2025
        fy_start = int(fy_year[:4])
    elif len(fy_year) == 4:
        # FY end year: e.g. "2026" → CY start = 2025
        fy_start = int(fy_year) - 1
    else:
        return []
    py_start = fy_start - 1       # start year of previous FY (e.g. 2024 for FY2026)
    fy_suffix = str(fy_start)[-2:]   # 2-digit year suffix (e.g. "25")
    py_suffix = str(py_start)[-2:]   # 2-digit year suffix (e.g. "24")

    # Match either full 4-digit year OR dash-separated 2-digit year (Liberty: "Dec-25")
    cy_yr = rf"(?:\b{fy_start}\b|-\s*{fy_suffix}(?!\d))"
    py_yr = rf"(?:\b{py_start}\b|-\s*{py_suffix}(?!\d))"

    return [
        # --- FY-quarter "For Q3 2025-26" style (Magma/Navi) ---
        (re.compile(rf"for\s+q\d[\s\S]*?{fy_start}-\d{{2}}", re.IGNORECASE), "cy_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+q\d[\s\S]*?{fy_start}-\d{{2}}", re.IGNORECASE), "cy_ytd"),
        (re.compile(rf"for\s+q\d[\s\S]*?{py_start}-\d{{2}}", re.IGNORECASE), "py_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+q\d[\s\S]*?{py_start}-\d{{2}}", re.IGNORECASE), "py_ytd"),
        # --- ZUNO: "For the period ended YYYY" = YTD ---
        # Must come before quarter-ended patterns so period→ytd takes priority.
        (re.compile(rf"for\s+the\s+period\s+ended[\s\S]{{0,80}}{cy_yr}", re.IGNORECASE), "cy_ytd"),
        (re.compile(rf"for\s+the\s+period\s+ended[\s\S]{{0,80}}{py_yr}", re.IGNORECASE), "py_ytd"),
        # --- Date-based "For the Quarter Ended Dec 31, 2025" style (with "Ended") ---
        (re.compile(rf"for\s+the\s+quarter\s+ended[\s\S]{{0,80}}{cy_yr}", re.IGNORECASE), "cy_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+the\s+quarter\s+ended[\s\S]{{0,80}}{cy_yr}", re.IGNORECASE), "cy_ytd"),
        (re.compile(rf"for\s+the\s+quarter\s+ended[\s\S]{{0,80}}{py_yr}", re.IGNORECASE), "py_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+the\s+quarter\s+ended[\s\S]{{0,80}}{py_yr}", re.IGNORECASE), "py_ytd"),
        # --- Date-based without "Ended": "For the Quarter December 31, 2025" (Royal/GoDigit) ---
        (re.compile(rf"for\s+the\s+quarter[\s\S]{{0,80}}{cy_yr}", re.IGNORECASE), "cy_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+the\s+quarter[\s\S]{{0,80}}{cy_yr}", re.IGNORECASE), "cy_ytd"),
        (re.compile(rf"for\s+the\s+quarter[\s\S]{{0,80}}{py_yr}", re.IGNORECASE), "py_qtr"),
        (re.compile(rf"(?:upto|up\s+to)\s+the\s+quarter[\s\S]{{0,80}}{py_yr}", re.IGNORECASE), "py_ytd"),
    ]

# Sub-label within each period group → metric suffix
_SUB_LABEL_MAP = [
    (re.compile(r"no\.?\s+of\s+polic", re.IGNORECASE), "policies"),
    (re.compile(r"premium", re.IGNORECASE), "premium"),
]


def detect_period_columns(table: List[List], fy_year: str = "") -> Dict[str, int]:
    """
    Scan header rows of an NL-35 table and return a dict mapping
    canonical period-metric key → column index.

    Expected table structure:
      r0: may be blank or contain "(Amount in Rs. Lakhs)"
      r1: period span headers ("For the Quarter", "upto the quarter", ...)
      r2: sub-headers ("Premium", "No. of Policies")

    fy_year: fiscal year string (e.g. '2026' for FY2026).  When provided,
    FY-quarter style headers like 'For Q3 2025-26' are also recognised.

    Returns dict with up to 8 entries:
      "cy_qtr_premium", "cy_qtr_policies",
      "py_qtr_premium", "py_qtr_policies",
      "cy_ytd_premium", "cy_ytd_policies",
      "py_ytd_premium", "py_ytd_policies"
    """
    if not table or len(table) < 3:
        return {}

    # FY-year-specific patterns first so date-based headers (e.g. "Dec 31, 2025")
    # take priority over the generic "for the quarter" fallback.
    combined_label_map = _fy_quarter_patterns(fy_year) + _PERIOD_LABEL_MAP

    # Find the two header rows: period spans and sub-labels
    # r1 has period spans (some cells are None for merged cols), r2 has Premium/Policies
    # We scan rows 0–6 to be robust to extra header rows
    period_row_idx = None
    sub_row_idx = None

    for ri in range(min(7, len(table))):
        row = table[ri]
        row_text = " ".join(str(c) for c in row if c)
        if any(p.search(row_text) for p, _ in combined_label_map):
            period_row_idx = ri
        elif re.search(r"premium", row_text, re.IGNORECASE) and re.search(r"polic", row_text, re.IGNORECASE):
            sub_row_idx = ri

    if period_row_idx is None or sub_row_idx is None:
        logger.warning("Could not find period header rows in table")
        return {}

    period_row = table[period_row_idx]
    sub_row = table[sub_row_idx]

    # Walk period_row left→right; None cells inherit the last seen group prefix
    col_to_group: Dict[int, str] = {}
    current_group = None
    for ci, cell in enumerate(period_row):
        if cell is not None and str(cell).strip():
            cell_text = str(cell).strip()
            for pattern, group in combined_label_map:
                if pattern.search(cell_text):
                    current_group = group
                    break
        if current_group:
            col_to_group[ci] = current_group

    # Walk sub_row and combine with group to get full key
    result: Dict[str, int] = {}
    for ci, cell in enumerate(sub_row):
        if cell is None or not str(cell).strip():
            continue
        cell_text = str(cell).strip()
        group = col_to_group.get(ci)
        if not group:
            continue
        for pattern, suffix in _SUB_LABEL_MAP:
            if pattern.search(cell_text):
                key = f"{group}_{suffix}"
                if key not in result:   # first-match wins
                    result[key] = ci
                break

    return result


# ---------------------------------------------------------------------------
# LOB row detection
# ---------------------------------------------------------------------------

def _detect_lob_rows_for_col(table: List[List], label_col: int) -> Dict[int, str]:
    """Inner helper — scan one specific column for LOB labels."""
    result: Dict[int, str] = {}
    seen_lobs: set = set()

    for ri, row in enumerate(table):
        if len(row) <= label_col:
            continue
        cell = row[label_col]
        if cell is None:
            continue
        raw = str(cell).strip()
        if not raw:
            continue

        if any(p.match(raw) for p in NL35_SKIP_PATTERNS):
            continue

        norm = normalise_text(raw)
        if not norm:
            continue

        lob_key = NL35_LOB_ALIASES.get(norm)
        if lob_key is None:
            norm2 = norm.replace("\u2019", "'")
            lob_key = NL35_LOB_ALIASES.get(norm2)

        if lob_key is None:
            logger.debug(f"Unrecognised LOB label (col {label_col}) row {ri}: '{raw}'")
            continue

        if lob_key in seen_lobs:
            continue

        result[ri] = lob_key
        seen_lobs.add(lob_key)

    return result


def detect_lob_rows(table: List[List], label_col: Optional[int] = None) -> Dict[int, str]:
    """
    Scan the table for LOB labels and return {row_index: canonical_lob_key}.

    If `label_col` is given, only that column is scanned.
    If `label_col` is None (default), columns 0–6 are tried and the column
    with the most recognised LOBs is used (ties broken by lower col index).

    Rows whose label matches NL35_SKIP_PATTERNS are skipped.
    First match wins — duplicate LOBs are silently dropped.
    """
    if label_col is not None:
        return _detect_lob_rows_for_col(table, label_col)

    max_col = min(7, max((len(r) for r in table), default=0))
    best: Dict[int, str] = {}
    best_col = 1  # default fallback

    for col in range(max_col):
        candidate = _detect_lob_rows_for_col(table, col)
        if len(candidate) > len(best):
            best = candidate
            best_col = col

    if best_col != 1:
        logger.debug(f"detect_lob_rows: auto-selected label column {best_col} ({len(best)} LOBs)")

    return best


# ---------------------------------------------------------------------------
# Grid extraction
# ---------------------------------------------------------------------------

def extract_nl35_grid(
    table: List[List],
    lob_rows: Dict[int, str],
    period_cols: Dict[str, int],
    nl35_data: NL35Data,
) -> None:
    """
    Fill nl35_data.data[lob_key][period_metric_key] from the table.
    Skips cells whose column index is out of range.
    """
    for row_idx, lob_key in lob_rows.items():
        if row_idx >= len(table):
            continue
        row = table[row_idx]
        if lob_key not in nl35_data.data:
            nl35_data.data[lob_key] = {}

        for col_key, col_idx in period_cols.items():
            if col_idx >= len(row):
                continue
            val = clean_number(row[col_idx])
            nl35_data.data[lob_key][col_key] = val


# ---------------------------------------------------------------------------
# Derived-total computation
# ---------------------------------------------------------------------------

from config.settings import PERIOD_METRIC_KEYS as _PMK


def _sum_lobs(data: NL35Data, lob_keys: List[str], period_key: str) -> Optional[float]:
    """Sum `period_key` across `lob_keys`, treating None as 0 but returning None
    only if ALL contributing LOBs have None (i.e. truly absent, not zero-reported)."""
    values = [data.data.get(lob, {}).get(period_key) for lob in lob_keys]
    non_none = [v for v in values if v is not None]
    return sum(non_none) if non_none else None


def compute_derived_totals(data: NL35Data) -> None:
    """
    Compute total_health if it is absent from the extracted data.

    total_health = health + personal_accident + travel_insurance

    Called after every extraction so both general insurers (which have
    Fire/Motor/etc. data) and standalone health insurers (which do not)
    get a consistent total_health row.
    """
    if "total_health" in data.data:
        return   # already present in the PDF — trust the source

    health_lobs = ("health", "personal_accident", "travel_insurance")
    # Only compute if at least one of the three LOBs has any data
    has_any = any(data.data.get(lob) for lob in health_lobs)
    if not has_any:
        return

    total: Dict[str, Optional[float]] = {}
    for pk in _PMK:
        v = _sum_lobs(data, health_lobs, pk)
        if v is not None:
            total[pk] = v

    if total:
        data.data["total_health"] = total
        logger.debug(f"compute_derived_totals: total_health computed from {health_lobs}")


# ---------------------------------------------------------------------------
# Header-driven entry point
# ---------------------------------------------------------------------------

def parse_header_driven_nl35(
    pdf_path: str,
    company_key: str,
    company_name_fallback: str = "",
    quarter: str = "",
    year: str = "",
) -> NL35Extract:
    """
    Standard NL-35 parser. Works for any company whose table follows the
    standard layout: serial-number col 0, LOB names col 1, 8 data cols 2–9,
    with period span headers in row 1 and Premium/Policies sub-headers in row 2.

    Returns NL35Extract populated with NL35Data.
    """
    company_name = (
        COMPANY_DISPLAY_NAMES.get(company_key)
        or company_name_fallback
        or str(company_key).title()
    )

    extract = NL35Extract(
        source_file=Path(pdf_path).name,
        company_key=company_key,
        company_name=company_name,
        form_type="NL35",
        quarter=quarter,
        year=year,
    )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = get_nl35_pages(pdf)
            if not pages:
                extract.extraction_errors.append("No NL-35 pages found")
                return extract

            for page in pages:
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    if not table or len(table) < 3:
                        continue

                    ncols = max(len(r) for r in table)
                    if ncols < 5:
                        continue

                    period_cols = detect_period_columns(table, fy_year=year)
                    if not period_cols:
                        logger.debug(f"No period columns found in table on page")
                        continue

                    lob_rows = detect_lob_rows(table)
                    if not lob_rows:
                        logger.debug("No LOB rows found in table")
                        continue

                    extract_nl35_grid(table, lob_rows, period_cols, extract.data)
                    logger.info(
                        f"Extracted {len(lob_rows)} LOBs with "
                        f"{len(period_cols)} period-metric columns"
                    )

    except Exception as e:
        logger.error(f"parse_header_driven_nl35 failed for {pdf_path}: {e}", exc_info=True)
        extract.extraction_errors.append(str(e))

    compute_derived_totals(extract.data)
    return extract
