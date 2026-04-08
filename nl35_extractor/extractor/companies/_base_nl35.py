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
_PERIOD_LABEL_MAP = [
    # Check longer/more-specific strings first
    (re.compile(r"up\s+to\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_ytd"),
    (re.compile(r"for\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_qtr"),
    (re.compile(r"upto\s+the\s+quarter|up\s+to\s+the\s+quarter", re.IGNORECASE), "cy_ytd"),
    (re.compile(r"for\s+the\s+quarter", re.IGNORECASE), "cy_qtr"),
]

# Sub-label within each period group → metric suffix
_SUB_LABEL_MAP = [
    (re.compile(r"no\.?\s+of\s+polic", re.IGNORECASE), "policies"),
    (re.compile(r"premium", re.IGNORECASE), "premium"),
]


def detect_period_columns(table: List[List]) -> Dict[str, int]:
    """
    Scan header rows of an NL-35 table and return a dict mapping
    canonical period-metric key → column index.

    Expected table structure:
      r0: may be blank or contain "(Amount in Rs. Lakhs)"
      r1: period span headers ("For the Quarter", "upto the quarter", ...)
      r2: sub-headers ("Premium", "No. of Policies")

    Returns dict with up to 8 entries:
      "cy_qtr_premium", "cy_qtr_policies",
      "py_qtr_premium", "py_qtr_policies",
      "cy_ytd_premium", "cy_ytd_policies",
      "py_ytd_premium", "py_ytd_policies"
    """
    if not table or len(table) < 3:
        return {}

    # Find the two header rows: period spans and sub-labels
    # r1 has period spans (some cells are None for merged cols), r2 has Premium/Policies
    # We scan rows 0–4 to be robust to extra header rows
    period_row_idx = None
    sub_row_idx = None

    for ri in range(min(5, len(table))):
        row = table[ri]
        row_text = " ".join(str(c) for c in row if c)
        if any(p.search(row_text) for p, _ in _PERIOD_LABEL_MAP):
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
            for pattern, group in _PERIOD_LABEL_MAP:
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

def detect_lob_rows(table: List[List], label_col: int = 1) -> Dict[int, str]:
    """
    Scan column `label_col` of the table for LOB labels and return
    {row_index: canonical_lob_key}.

    col 0 is typically the serial number; col 1 is the LOB name.
    Rows whose label matches NL35_SKIP_PATTERNS are skipped.
    First match wins — duplicate LOBs are silently dropped.
    """
    result: Dict[int, str] = {}
    seen_lobs = set()

    for ri, row in enumerate(table):
        if len(row) <= label_col:
            continue
        cell = row[label_col]
        if cell is None:
            continue
        raw = str(cell).strip()
        if not raw:
            continue

        # Skip patterns
        if any(p.match(raw) for p in NL35_SKIP_PATTERNS):
            continue

        norm = normalise_text(raw)
        if not norm:
            continue

        lob_key = NL35_LOB_ALIASES.get(norm)
        if lob_key is None:
            # Try without apostrophe variants
            norm2 = norm.replace("\u2019", "'")
            lob_key = NL35_LOB_ALIASES.get(norm2)

        if lob_key is None:
            logger.debug(f"Unrecognised LOB label at row {ri}: '{raw}' (norm: '{norm}')")
            continue

        if lob_key in seen_lobs:
            continue

        result[ri] = lob_key
        seen_lobs.add(lob_key)

    return result


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

                    period_cols = detect_period_columns(table)
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

    return extract
