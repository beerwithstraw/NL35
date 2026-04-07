"""
consolidated_detector.py

Finds the page range of the NL-6 form within a consolidated PDF.

A consolidated PDF contains multiple IRDAI forms (NL-1 through NL-15+)
merged into one file. This module scans page text to find where the
NL-6 Commission Schedule starts and ends.

Detection strategy:
  START: First page where >= min_matches NL-6 keywords appear
  END:   Page before the next form header appears, or last page of PDF

Next form detection: looks for "FORM NL-" followed by a digit other than 6,
or "FORM NL-6" appearing again (which would mean a second NL-6 section,
stop before it).
"""

import re
import logging
import tempfile
import os
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "FORM NL-6",
    "COMMISSION SCHEDULE",
    "NET COMMISSION",
    "GROSS COMMISSION",
    "REINSURANCE ACCEPTED",
    "REINSURANCE CEDED",
]

# Regex to detect any IRDAI form header on a page
FORM_HEADER_PATTERN = re.compile(r"FORM\s+NL[-\s]?(\d+)", re.IGNORECASE)


def _page_keyword_count(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in the page text (case-insensitive)."""
    text_upper = text.upper()
    return sum(1 for kw in keywords if kw.upper() in text_upper)


def find_nl6_pages(
    pdf_path: str,
    keywords: Optional[List[str]] = None,
    min_matches: int = 2,
) -> Optional[Tuple[int, int]]:
    """
    Scan the consolidated PDF and return (start_page, end_page) 0-indexed
    for the NL-5 section. Returns None if NL-6 section not found.

    start_page is inclusive, end_page is inclusive.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not available")
        return None

    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    try:
        with pdfplumber.open(pdf_path) as pdf:
            n_pages = len(pdf.pages)
            page_texts = []

            for page in pdf.pages:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                page_texts.append(text)

        # --- Find start page ---
        start_page = None
        for i, text in enumerate(page_texts):
            if _page_keyword_count(text, keywords) >= min_matches:
                start_page = i
                break

        if start_page is None:
            logger.warning(f"NL-6 section not found in: {pdf_path}")
            return None

        # --- Find end page ---
        # Scan from start_page+1 for the next form header
        end_page = n_pages - 1  # default: end of document

        for i in range(start_page + 1, n_pages):
            text = page_texts[i]
            matches = FORM_HEADER_PATTERN.findall(text)
            # Only stop when a DIFFERENT form number appears.
            # Repeated NL-5 headers are continuation pages of the same form.
            non_nl6 = [m for m in matches if m != "6"]
            if non_nl6:
                end_page = i - 1
                logger.debug(
                    f"NL-6 ends at page {end_page} "
                    f"(NL-{non_nl6[0]} starts at page {i})"
                )
                break

        logger.info(
            f"NL-6 found at pages {start_page}-{end_page} "
            f"(0-indexed) in {os.path.basename(pdf_path)}"
        )
        return (start_page, end_page)

    except Exception as e:
        logger.error(f"Error scanning consolidated PDF {pdf_path}: {e}")
        return None


def extract_nl6_to_temp(
    pdf_path: str,
    start_page: int,
    end_page: int,
) -> Optional[str]:
    """
    Extract pages start_page..end_page from pdf_path into a temporary PDF file.
    Returns the path to the temp file, or None on failure.
    Caller is responsible for deleting the temp file after use.
    """
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError:
            logger.error("pypdf or PyPDF2 not available — cannot extract pages")
            return None

    try:
        reader = pypdf.PdfReader(pdf_path)
        writer = pypdf.PdfWriter()

        for page_num in range(start_page, end_page + 1):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])

        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False, prefix="nl6_extract_"
        )
        with open(tmp.name, "wb") as f:
            writer.write(f)

        logger.debug(f"Extracted pages {start_page}-{end_page} to {tmp.name}")
        return tmp.name

    except Exception as e:
        logger.error(f"Error extracting pages from {pdf_path}: {e}")
        return None
