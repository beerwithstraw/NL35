"""
PDF metadata detection — form type, company, quarter, and year.
"""

import re
import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_MAP, COMPANY_DISPLAY_NAMES
from config.settings import QUARTER_TO_FY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quarter detection helpers
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
            except (ValueError, TypeError):
                continue
    return results

def detect_form_type(pdf_path):
    fn = Path(pdf_path).name.upper()
    if "NL35" in fn or "NL-35" in fn:
        return "NL35"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: return "unknown"
            text = pdf.pages[0].extract_text() or ""
            if "FORM NL-35" in text.upper() or "NL-35" in text.upper():
                return "NL35"
        return "unknown"
    except Exception:
        return "unknown"

def detect_company(pdf_path):
    fn = Path(pdf_path).name.lower()
    for key in sorted(COMPANY_MAP.keys(), key=len, reverse=True):
        if key in fn or key.replace(" ", "") in fn.replace("_", "").replace("-", ""):
            return COMPANY_MAP[key]
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = (pdf.pages[0].extract_text() or "").lower()
            for ck, dn in COMPANY_DISPLAY_NAMES.items():
                if dn.lower() in text: return ck
    except Exception: pass
    return None

def detect_quarter_year(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: return None, None
            text = pdf.pages[0].extract_text() or ""
            res = _extract_dates_from_text(text)
            if res:
                return sorted(res, key=lambda x: x[1], reverse=True)[0]
    except Exception: pass
    return None, None

def detect_all(pdf_path):
    ft = detect_form_type(pdf_path)
    ck = detect_company(pdf_path)
    q, y = detect_quarter_year(pdf_path)
    return ft, ck, q, y
