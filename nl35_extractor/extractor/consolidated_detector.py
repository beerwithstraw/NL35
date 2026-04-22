"""
consolidated_detector.py — finds the NL-35 page range within a consolidated PDF.
"""

import re
import logging
import tempfile
import os
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "FORM NL-35",
    "QUARTERLY BUSINESS RETURNS",
    "LINE OF BUSINESS",
    "NO. OF POLICIES",
    "PREMIUM",
]

FORM_HEADER_PATTERN = re.compile(
    r"^\s*(?:FORM\s+)?NL[-\s]?(\d+)|\bFORM\s+NL[-\s]?(\d+)", 
    re.IGNORECASE | re.MULTILINE
)
def is_toc_page(text: str) -> bool:
    if re.search(r"TABLE\s+OF\s+CONTENTS|FORM\s+INDEX|INDEX\s+OF\s+FORMS", text, re.IGNORECASE):
        return True
    matches = re.findall(r"\bNL[-\s]?(\d+)\b", text, re.IGNORECASE)
    valid_forms = set(m for m in matches if 1 <= int(m) <= 45)
    return len(valid_forms) >= 4


def _page_keyword_count(text: str, keywords: List[str]) -> int:
    text_upper = text.upper()
    return sum(1 for kw in keywords if kw.upper() in text_upper)


def find_nl35_pages(
    pdf_path: str,
    keywords: Optional[List[str]] = None,
    min_matches: int = 3,
) -> Optional[Tuple[int, int]]:
    """Return (start_page, end_page) 0-indexed for the NL-35 section."""
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

        start_page = None
        for i, text in enumerate(page_texts):
            if is_toc_page(text):
                logger.debug(f"  page {i + 1}: TOC page, skipping")
                continue
            if _page_keyword_count(text, keywords) >= min_matches:
                start_page = i
                break

        if start_page is None:
            logger.warning(f"NL-35 section not found in: {pdf_path}")
            return None

        end_page = n_pages - 1
        for i in range(start_page + 1, n_pages):
            matches = FORM_HEADER_PATTERN.findall(page_texts[i])
            non_nl35 = [m for m in matches if m != "35"]
            if non_nl35:
                end_page = i - 1
                break

        logger.info(f"NL-35 found at pages {start_page}-{end_page} (0-indexed) in {os.path.basename(pdf_path)}")
        return (start_page, end_page)

    except Exception as e:
        logger.error(f"Error scanning consolidated PDF {pdf_path}: {e}")
        return None


def extract_nl35_to_temp(pdf_path: str, start_page: int, end_page: int) -> Optional[str]:
    """Extract pages into a temp PDF. Caller must delete the file."""
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError:
            logger.error("pypdf or PyPDF2 not available")
            return None

    try:
        reader = pypdf.PdfReader(pdf_path)
        writer = pypdf.PdfWriter()
        for page_num in range(start_page, end_page + 1):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="nl35_extract_")
        with open(tmp.name, "wb") as f:
            writer.write(f)
        return tmp.name
    except Exception as e:
        logger.error(f"Error extracting pages from {pdf_path}: {e}")
        return None
