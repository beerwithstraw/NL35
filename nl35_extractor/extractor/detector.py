"""
PDF metadata detection — form type, company, quarter, and year.
Detects NL-6 (Commission Schedule) form type.

Source: approach document Section 8.1
Anti-hallucination rule #9: every function that touches a PDF must have
try/except that logs and returns None rather than crashing the pipeline.
"""

import re
import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_MAP, COMPANY_DISPLAY_NAMES
from config.settings import make_fy_string, QUARTER_TO_FY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quarter detection from date strings
# ---------------------------------------------------------------------------

# Month-end dates that indicate each quarter
_QUARTER_MONTH_MAP = {
    6: "Q1",    # June → Q1  (FY starts April)
    9: "Q2",    # September → Q2
    12: "Q3",   # December → Q3
    3: "Q4",    # March → Q4
}

# Regex patterns for dates in NL-4 headers
# Captures patterns like "30 June 2025", "31st March, 2025", "30.06.2025",
# "June 30, 2025", etc.
_DATE_PATTERNS = [
    # "30 June 2025" / "31 March 2025" / "30th June 2025"
    re.compile(
        r'(?:ENDED|ENDING)?\s*(\d{1,2})\s*(?:st|nd|rd|th)?\s+'
        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'[,.\s]*(\d{4})',
        re.IGNORECASE,
    ),
    # "June 30, 2025" / "March 31, 2025" / "Mar 31, 2025"
    re.compile(
        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'\s+(\d{1,2})[,.\s]*(\d{4})',
        re.IGNORECASE,
    ),
    # "30.06.2025" / "31.03.2025"
    re.compile(r'(\d{1,2})[./](\d{1,2})[./](\d{4})'),
    # "31-03-2025" / "31-3-2025" (hyphen-separated DD-MM-YYYY, e.g. New India)
    re.compile(r'(\d{1,2})-(\d{1,2})-(\d{4})'),
    # "Jun-24" / "June-2024" (Month-Year pattern common in NL-4 headers)
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
    """
    Given day/month/year integers, return (quarter_str, fy_str) or (None, None).
    Handles date typos like June 31 → clamp to valid day.
    """
    # Clamp invalid days (e.g. HDFC "June 31" typo)
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        logger.warning(f"Clamped invalid date: day {day} → {max_day} for month {month}")
        day = max_day

    quarter = _QUARTER_MONTH_MAP.get(month)
    if quarter is None:
        return None, None

    fy = QUARTER_TO_FY[quarter](year)
    return quarter, fy


def _extract_dates_from_text(text):
    """
    Extract all (quarter, fy_string) pairs found in text.
    Returns list of (quarter, fy_string) tuples.
    """
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
                        if len(g1) == 2:
                            year = 2000 + int(g1)
                        else:
                            year = int(g1)
                        q, fy = _parse_quarter_year_from_date(1, month, year)
                        if q and fy:
                            results.append((q, fy))
            except (ValueError, TypeError):
                continue

    # Direct quarter label pattern for companies like ICICI Lombard
    # that use "For Q1 / Upto Q1" and "2024-25" instead of month names
    _fy_hyphen_pattern = re.compile(r'\b(20[2-9][0-9])\s*-\s*([0-9]{2})\b')
    _quarter_label_pattern = re.compile(r'\bFor\s+(Q[1-4])\b|\bUpto\s+(Q[1-4])\b|\b(Q[1-4])\s+\d{4}', re.IGNORECASE)
    fy_match = _fy_hyphen_pattern.search(text)
    q_match = _quarter_label_pattern.search(text)
    if fy_match and q_match:
        start_year = fy_match.group(1)
        end_suffix = fy_match.group(2)
        fy_string = f"{start_year}{end_suffix}"
        
        # Validate FY string (must be 6 digits and start with 20)
        if len(fy_string) == 6 and fy_string.startswith("20") and int(fy_string) >= 202021:
            quarter = (q_match.group(1) or q_match.group(2) or q_match.group(3)).upper()
            results.append((quarter, fy_string))

    # Second pass: Filter out suspicious results (like the Tata 203031 glitch)
    # Dynamic ceiling: current calendar year + 2 → max plausible FY
    from datetime import date as _date
    _max_fy_start = _date.today().year + 2
    _max_fy = _max_fy_start * 100 + (_max_fy_start + 1) % 100
    final_results = []
    for q, fy in results:
        try:
            val = int(fy)
            if 202021 <= val <= _max_fy:
                final_results.append((q, fy))
        except ValueError:
            continue
            
    return final_results


# ---------------------------------------------------------------------------
# Form type detection
# ---------------------------------------------------------------------------

_FORM_NL6_PATTERNS = [
    re.compile(r'FORM\s+NL[-\s]?0?6\b', re.IGNORECASE),
    re.compile(r'\bNL[-\s]?0?6\b', re.IGNORECASE),
    re.compile(r'COMMISSION\s+SCHEDULE', re.IGNORECASE),
]

# Filename pattern for form type fallback.
# Uses (?!\d) (not followed by another digit) instead of \b so that
# NL_06_ and NL6_ both match (underscore is a word char, so \b fails there).
_FILENAME_NL6_PATTERN = re.compile(r'NL[\s\-_]*0?6(?!\d)', re.IGNORECASE)


def detect_form_type(pdf_path):
    """
    Detect the IRDAI form type.
    Step 1: check filename (reliable for well-named files).
    Step 2: check first page PDF text.

    Returns
    -------
    str : "NL6" | "unknown"
    """
    # Step 1: filename fallback
    if _FILENAME_NL6_PATTERN.search(Path(pdf_path).name):
        return "NL6"

    # Step 2: PDF text scan
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return "unknown"
            text = pdf.pages[0].extract_text() or ""
            for pattern in _FORM_NL6_PATTERNS:
                if pattern.search(text):
                    return "NL6"
        return "unknown"
    except Exception as e:
        logger.error(f"Form detection failed for {pdf_path}: {e}")
        return "unknown"


# ---------------------------------------------------------------------------
# Company detection
# ---------------------------------------------------------------------------

def _detect_company_from_filename(filename):
    """
    Detect company from filename by stripping to lowercase alphanum+spaces
    and testing COMPANY_MAP keys longest-first.
    """
    # Normalise filename: lowercase, keep alphanum and spaces
    name = Path(filename).stem.lower()
    name_clean = re.sub(r'[^a-z0-9\s]', '', name)
    name_nospace = re.sub(r'\s+', '', name_clean)

    # Sort keys longest-first for greedy matching
    sorted_keys = sorted(COMPANY_MAP.keys(), key=len, reverse=True)

    for key in sorted_keys:
        key_nospace = key.replace(" ", "")
        if key in name_clean or key_nospace in name_nospace:
            return COMPANY_MAP[key]

    return None


def _detect_company_from_pdf_text(pdf_path):
    """
    Detect company from PDF text content (first 5 pages).
    Searches for COMPANY_DISPLAY_NAMES and COMPANY_MAP keys in the text.

    # Phase 2 TODO: if pdfplumber text is garbled (interleaved columns),
    # fall back to PyMuPDF (fitz) which reads text in visual spatial order.
    # Add: pip install pymupdf, implement _extract_text_robust() helper.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(5, len(pdf.pages))
            text = ""
            for i in range(pages_to_check):
                page_text = pdf.pages[i].extract_text() or ""
                text += " " + page_text

            text_lower = text.lower()

            # Check display names first (most specific)
            for company_key, display_name in COMPANY_DISPLAY_NAMES.items():
                if display_name.lower() in text_lower:
                    return company_key

            # Then check COMPANY_MAP keys longest-first
            sorted_keys = sorted(COMPANY_MAP.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if key in text_lower:
                    return COMPANY_MAP[key]

        return None
    except Exception as e:
        logger.error(f"PDF text company detection failed for {pdf_path}: {e}")
        return None


def detect_company(pdf_path):
    """
    Detect company from a PDF.
    Step 1: try filename-based detection.
    Step 2: fall back to PDF text content.

    Returns
    -------
    str | None : company_key or None
    """
    filename = Path(pdf_path).name

    # Step 1: filename
    result = _detect_company_from_filename(filename)
    if result:
        logger.info(f"{filename}: Company detected from filename: {result}")
        return result

    # Step 2: PDF text
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
    """
    Detect quarter and financial year from PDF header text (first page).

    Returns
    -------
    tuple : (quarter_str, fy_str) e.g. ("Q1", "202526") or (None, None)
    """
    filename = Path(pdf_path).name

    # Step 1: PDF text scan
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                pass  # fall through to filename fallback
            else:
                text = pdf.pages[0].extract_text() or ""
                results = _extract_dates_from_text(text)
                if results:
                    # Take the most recent FY, not just the first found.
                    # NL-4 page 1 contains both CY and PY dates — the prior
                    # year date may appear first in the text stream.
                    results_sorted = sorted(
                        results, key=lambda x: x[1], reverse=True
                    )
                    return results_sorted[0]
    except Exception as e:
        logger.error(f"Quarter/year PDF text detection failed for {filename}: {e}")

    # Step 2: filename fallback — for garbled PDFs (e.g. United India)
    _qy_filename_pattern = re.compile(r'(Q[1-4])[_\-](\d{6})', re.IGNORECASE)
    m = _qy_filename_pattern.search(filename)
    if m:
        logger.warning(f"{filename}: Quarter/year from filename fallback")
        return m.group(1).upper(), m.group(2)

    return None, None


# ---------------------------------------------------------------------------
# Convenience: detect everything
# ---------------------------------------------------------------------------

def detect_all(pdf_path):
    """
    Run all detection in one call.

    Returns
    -------
    tuple : (form_type, company_key, quarter, year)
             Any component may be None/"unknown".
    """
    form_type = detect_form_type(pdf_path)
    company_key = detect_company(pdf_path)
    quarter, year = detect_quarter_year(pdf_path)
    return form_type, company_key, quarter, year


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(form_type, company_key, quarter, year):
    """
    Compute detection confidence level.

    Returns
    -------
    str : "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
    """
    if form_type == "NL6" and company_key and quarter and year:
        return "HIGH"
    elif form_type == "NL6" and company_key:
        return "MEDIUM"
    elif form_type == "NL6":
        return "LOW"
    else:
        return "UNKNOWN"
