"""Bajaj Allianz General Insurance — NL-35 Quarterly Business Returns parser."""
import logging
from extractor.companies._base_nl35 import parse_header_driven_nl35

logger = logging.getLogger(__name__)


def parse_bajaj_nl35(pdf_path: str, company_key: str, quarter: str = "", year: str = ""):
    """
    Bajaj NL-35 layout: 1 page, 1 table, 18 rows × 10 cols.
    Standard layout — fully handled by parse_header_driven_nl35.
    """
    logger.info(f"Parsing Bajaj NL35: {pdf_path}")
    return parse_header_driven_nl35(
        pdf_path=pdf_path,
        company_key=company_key,
        company_name_fallback="Bajaj Allianz General Insurance Company Limited",
        quarter=quarter,
        year=year,
    )
