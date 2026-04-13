"""
smoke_test.py — NL-35 PDF batch smoke tester.

Scans every PDF in the configured NL35 folder, extracts all tables, and
reports:
  - Unrecognised LOB row labels (candidates for alias expansion)
  - Unrecognised period/column headers
  - Company keys not in COMPANY_MAP
  - Per-file LOB coverage summary

Usage:
  cd nl35_extractor
  python3 smoke_test.py
"""

import os
import re
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
import yaml

from config.company_registry import COMPANY_MAP, COMPANY_DISPLAY_NAMES
from config.row_registry import NL35_LOB_ALIASES, NL35_SKIP_PATTERNS
from extractor.normaliser import normalise_text

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)-5s | %(message)s",
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "extraction_config.yaml")

with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

BASE_PATH = cfg["base_path"]
PDF_DIR = os.path.join(BASE_PATH, "FY2026", "Q3", "NL35")

# ---------------------------------------------------------------------------
# Period column header patterns (same as _base_nl35.py, widened to 7 rows)
# ---------------------------------------------------------------------------
_PERIOD_LABEL_MAP = [
    (re.compile(r"up\s+to\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_ytd"),
    (re.compile(r"for\s+the\s+corresponding\s+quarter\s+of\s+the\s+previous\s+year", re.IGNORECASE), "py_qtr"),
    (re.compile(r"upto\s+the\s+quarter|up\s+to\s+the\s+quarter", re.IGNORECASE), "cy_ytd"),
    (re.compile(r"for\s+the\s+quarter", re.IGNORECASE), "cy_qtr"),
]

_SUB_LABEL_MAP = [
    (re.compile(r"no\.?\s+of\s+polic", re.IGNORECASE), "policies"),
    (re.compile(r"premium", re.IGNORECASE), "premium"),
]


def _is_period_header(text: str) -> bool:
    return any(p.search(text) for p, _ in _PERIOD_LABEL_MAP)


def _is_sub_header(text: str) -> bool:
    return any(p.search(text) for p, _ in _SUB_LABEL_MAP)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_company(filename: str):
    name = filename.lower()
    if name.endswith(".pdf"):
        name = name[:-4]
    name_nospace = re.sub(r'[^a-z0-9]', '', name)
    for key in sorted(COMPANY_MAP.keys(), key=len, reverse=True):
        key_norm = re.sub(r'[^a-z0-9]', '', key.lower())
        if key_norm in name_nospace or key.lower() in name:
            return COMPANY_MAP[key]
    return None


def _scan_table_headers(table, max_rows=7):
    """Return (period_row_texts, sub_row_texts, unrecognised_header_cells)."""
    period_hits = []
    sub_hits = []
    unrecognised = []

    for ri in range(min(max_rows, len(table))):
        row = table[ri]
        for cell in row:
            if cell is None:
                continue
            t = str(cell).strip()
            if not t:
                continue
            if _is_period_header(t):
                period_hits.append(t)
            elif _is_sub_header(t):
                sub_hits.append(t)
            elif any(kw in t.lower() for kw in ["premium", "polic", "quarter", "period", "ytd", "year"]):
                unrecognised.append(t)

    return period_hits, sub_hits, unrecognised


def _scan_table_lobs(table, max_cols=7):
    """
    Try label columns 0..max_cols-1.
    Returns (recognised_lobs, unrecognised_labels, best_label_col).
    """
    best_col = None
    best_recognised = {}
    best_unrecognised = []

    for label_col in range(min(max_cols, max(len(r) for r in table) if table else 0)):
        recognised = {}
        unrecognised = []
        seen = set()

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

            if lob_key:
                if lob_key not in seen:
                    recognised[ri] = (raw, lob_key)
                    seen.add(lob_key)
            else:
                unrecognised.append((ri, raw, norm))

        if len(recognised) > len(best_recognised):
            best_recognised = recognised
            best_unrecognised = unrecognised
            best_col = label_col

    return best_recognised, best_unrecognised, best_col


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    print(f"\n{'='*70}")
    print(f"NL-35 SMOKE TEST — {PDF_DIR}")
    print(f"PDFs found: {len(pdfs)}")
    print(f"{'='*70}\n")

    all_unrecognised_lobs: dict[str, list[str]] = {}   # norm → [files]
    all_unrecognised_headers: dict[str, list[str]] = {}
    unmapped_companies: list[str] = []

    for fname in pdfs:
        pdf_path = os.path.join(PDF_DIR, fname)
        company_key = _match_company(fname)

        print(f"--- {fname}")
        print(f"    company_key : {company_key or '** UNKNOWN **'}")
        if not company_key:
            unmapped_companies.append(fname)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_recognised_lobs = {}
                file_unrecognised_lobs = []
                file_unrecognised_headers = []
                tables_found = 0
                best_label_col = None

                for page in pdf.pages:
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    for table in tables:
                        if not table or len(table) < 3:
                            continue
                        ncols = max(len(r) for r in table) if table else 0
                        if ncols < 4:
                            continue
                        tables_found += 1

                        # Period/column header scan (up to 7 rows)
                        period_hits, sub_hits, unrecog_hdrs = _scan_table_headers(table, max_rows=7)
                        file_unrecognised_headers.extend(unrecog_hdrs)

                        # LOB row scan (try cols 0–6)
                        recognised, unrecognised, label_col = _scan_table_lobs(table, max_cols=7)
                        if recognised:
                            all_recognised_lobs.update(recognised)
                            if best_label_col is None:
                                best_label_col = label_col
                        file_unrecognised_lobs.extend(unrecognised)

                # Deduplicate unrecognised labels
                seen_norms = set()
                deduped_lobs = []
                for ri, raw, norm in file_unrecognised_lobs:
                    if norm not in seen_norms:
                        seen_norms.add(norm)
                        deduped_lobs.append((raw, norm))

                seen_hdrs = set()
                deduped_hdrs = []
                for h in file_unrecognised_headers:
                    hn = normalise_text(h)
                    if hn and hn not in seen_hdrs:
                        seen_hdrs.add(hn)
                        deduped_hdrs.append(h)

                print(f"    tables found: {tables_found}  |  label_col: {best_label_col}  |  recognised LOBs: {len(all_recognised_lobs)}")

                if all_recognised_lobs:
                    lob_names = ", ".join(v[1] for v in all_recognised_lobs.values())
                    print(f"    LOBs: {lob_names}")

                if deduped_lobs:
                    print(f"    UNRECOGNISED LOB LABELS ({len(deduped_lobs)}):")
                    for raw, norm in deduped_lobs:
                        print(f"      raw='{raw}'  norm='{norm}'")
                        all_unrecognised_lobs.setdefault(norm, []).append(fname)

                if deduped_hdrs:
                    print(f"    UNRECOGNISED COLUMN HEADERS ({len(deduped_hdrs)}):")
                    for h in deduped_hdrs:
                        print(f"      '{h}'")
                        hn = normalise_text(h)
                        all_unrecognised_headers.setdefault(hn, []).append(fname)

        except Exception as e:
            print(f"    ERROR: {e}")

        print()

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("SUMMARY — UNMAPPED COMPANIES")
    print(f"{'='*70}")
    if unmapped_companies:
        for f in unmapped_companies:
            print(f"  {f}")
    else:
        print("  (none)")

    print(f"\n{'='*70}")
    print("SUMMARY — UNRECOGNISED LOB LABELS (alias candidates)")
    print(f"{'='*70}")
    for norm, files in sorted(all_unrecognised_lobs.items()):
        print(f"  '{norm}'  ←  {', '.join(set(files))}")

    print(f"\n{'='*70}")
    print("SUMMARY — UNRECOGNISED COLUMN HEADERS")
    print(f"{'='*70}")
    for norm, files in sorted(all_unrecognised_headers.items()):
        print(f"  '{norm}'  ←  {', '.join(set(files))}")


if __name__ == "__main__":
    main()
