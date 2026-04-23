"""
PDF metadata detection — form type, company, quarter, and year for NL-35.
"""

import re
import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_MAP, COMPANY_DISPLAY_NAMES
from config.settings import make_fy_string, QUARTER_TO_FY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quarter detection helpers (shared with NL-35)
# ---------------------------------------------------------------------------

_QUARTER_MONTH_MAP = {6: "Q1", 9: "Q2", 12: "Q3", 3: "Q4"}

_DATE_PATTERNS = [
    re.compile(
        r'(?:ENDED|ENDING)?\s*(\d{1,2})\s*(?:st|nd|rd|th)?\s+'
        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'[,.\s]*(\d{4})',
        re.IGNORECASE,
    ),
    re.compile(
        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'\s+(\d{1,2})[,.\s]*(\d{4})',
        re.IGNORECASE,
    ),
    re.compile(r'(\d{1,2})[./](\d{1,2})[./](\d{4})'),
    re.compile(r'(\d{1,2})-(\d{1,2})-(\d{4})'),
    re.compile(
        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'[.\s\-\']*(\d{2,4})',
        re.IGNORECASE,
    ),
]

_MONTH_NAME_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_quarter_year_from_date(day, month, year):
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        day = max_day
    quarter = _QUARTER_MONTH_MAP.get(month)
    if quarter is None:
        return None, None
    fy = QUARTER_TO_FY[quarter](year)
    return quarter, fy


def _extract_dates_from_text(text):
    results = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            try:
                if len(groups) == 3:
                    g0, g1, g2 = groups
                    day, month, year = None, None, None
                    if g0.isdigit() and g2.isdigit() and not g1.isdigit():
                        day, month, year = int(g0), _MONTH_NAME_TO_NUM.get(g1.lower()), int(g2)
                    elif g1.isdigit() and g2.isdigit() and not g0.isdigit():
                        month, day, year = _MONTH_NAME_TO_NUM.get(g0.lower()), int(g1), int(g2)
                    elif g0.isdigit() and g1.isdigit() and g2.isdigit():
                        day, month, year = int(g0), int(g1), int(g2)
                    if month and year:
                        q, fy = _parse_quarter_year_from_date(day or 1, month, year)
                        if q and fy:
                            results.append((q, fy))
                elif len(groups) == 2:
                    g0, g1 = groups
                    month = _MONTH_NAME_TO_NUM.get(g0.lower())
                    if month:
                        year = 2000 + int(g1) if len(g1) == 2 else int(g1)
                        q, fy = _parse_quarter_year_from_date(1, month, year)
                        if q and fy:
                            results.append((q, fy))
            except (ValueError, TypeError):
                continue

    from datetime import date as _date
    _max_fy_start = _date.today().year + 2
    _max_fy = _max_fy_start * 100 + (_max_fy_start + 1) % 100
    return [(q, fy) for q, fy in results if 202021 <= int(fy) <= _max_fy]


# ---------------------------------------------------------------------------
# Form type detection
# ---------------------------------------------------------------------------

_FORM_NL35_PATTERNS = [
    re.compile(r'FORM\s+NL[-\s]?35\b', re.IGNORECASE),
    re.compile(r'\bNL[-\s]?35\b', re.IGNORECASE),
    re.compile(r'QUARTERLY\s+BUSINESS\s+RETURNS', re.IGNORECASE),
]

_FILENAME_NL35_PATTERN = re.compile(r'NL[\s\-_]*35(?!\d)', re.IGNORECASE)


def detect_form_type(pdf_path):
    if _FILENAME_NL35_PATTERN.search(Path(pdf_path).name):
        return "NL35"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return "unknown"
            text = pdf.pages[0].extract_text() or ""
            for pattern in _FORM_NL35_PATTERNS:
                if pattern.search(text):
                    return "NL35"
        return "unknown"
    except Exception as e:
        logger.error(f"Form detection failed for {pdf_path}: {e}")
        return "unknown"


# ---------------------------------------------------------------------------
# Company detection
# ---------------------------------------------------------------------------

def _detect_company_from_filename(filename):
    name = Path(filename).stem.lower()
    name_clean = re.sub(r'[^a-z0-9\s]', '', name)
    name_nospace = re.sub(r'\s+', '', name_clean)
    sorted_keys = sorted(COMPANY_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        key_nospace = key.replace(" ", "")
        if key in name_clean or key_nospace in name_nospace:
            return COMPANY_MAP[key]
    return None


def _detect_company_from_pdf_text(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for i in range(min(5, len(pdf.pages))):
                text += " " + (pdf.pages[i].extract_text() or "")
            text_lower = text.lower()
            for company_key, display_name in COMPANY_DISPLAY_NAMES.items():
                if display_name.lower() in text_lower:
                    return company_key
            sorted_keys = sorted(COMPANY_MAP.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if key in text_lower:
                    return COMPANY_MAP[key]
        return None
    except Exception as e:
        logger.error(f"PDF text company detection failed for {pdf_path}: {e}")
        return None


def detect_company(pdf_path):
    filename = Path(pdf_path).name
    result = _detect_company_from_filename(filename)
    if result:
        logger.info(f"{filename}: Company detected from filename: {result}")
        return result
    result = _detect_company_from_pdf_text(pdf_path)
    if result:
        logger.info(f"{filename}: Company detected from PDF text: {result}")
        return result
    logger.warning(f"{filename}: Company could not be detected")
    return None


# ---------------------------------------------------------------------------
# Quarter / Year detection
# ---------------------------------------------------------------------------

def detect_quarter_year(pdf_path):
    filename = Path(pdf_path).name
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text() or ""
                results = _extract_dates_from_text(text)
                if results:
                    return sorted(results, key=lambda x: x[1], reverse=True)[0]
    except Exception as e:
        logger.error(f"Quarter/year PDF text detection failed for {filename}: {e}")

    _qy_filename_pattern = re.compile(r'(Q[1-4])[_\-](\d{6})', re.IGNORECASE)
    m = _qy_filename_pattern.search(filename)
    if m:
        return m.group(1).upper(), m.group(2)

    return None, None


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def detect_all(pdf_path):
    form_type = detect_form_type(pdf_path)
    company_key = detect_company(pdf_path)
    quarter, year = detect_quarter_year(pdf_path)
    return form_type, company_key, quarter, year


def compute_confidence(form_type, company_key, quarter, year):
    if form_type == "NL35" and company_key and quarter and year:
        return "HIGH"
    elif form_type == "NL35" and company_key:
        return "MEDIUM"
    elif form_type == "NL35":
        return "LOW"
    else:
        return "UNKNOWN"
