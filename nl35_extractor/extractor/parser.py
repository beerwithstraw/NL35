"""
NL-35 parser entry point.

Routes to the dedicated parser for each company (DEDICATED_PARSER in
company_registry.py). Falls back to the generic header-driven parser when
no dedicated parser is registered.
"""

import logging

from config.company_registry import DEDICATED_PARSER
from extractor.models import NL35Extract

logger = logging.getLogger(__name__)


def parse_pdf(pdf_path: str, company_key: str, quarter: str = "", year: str = "") -> NL35Extract:
    """
    Parse an NL-35 PDF and return an NL35Extract.
    Routes to the dedicated parser registered for the company, or falls back
    to the generic header-driven parser.
    """
    logger.info(f"Parsing PDF: {pdf_path} for company: {company_key}")

    dedicated_func_name = DEDICATED_PARSER.get(company_key)
    if dedicated_func_name:
        from extractor.companies import PARSER_REGISTRY
        dedicated_func = PARSER_REGISTRY.get(dedicated_func_name)
        if dedicated_func:
            logger.info(f"Routing to dedicated parser: {dedicated_func_name}")
            return dedicated_func(pdf_path, company_key, quarter, year)
        else:
            logger.error(f"Dedicated parser '{dedicated_func_name}' not in PARSER_REGISTRY")

    # No dedicated parser — fall back to the generic header-driven parser.
    logger.info(f"No dedicated parser for {company_key} — using generic header-driven fallback")
    from extractor.companies._base_nl35 import parse_header_driven_nl35
    return parse_header_driven_nl35(pdf_path, company_key, quarter=quarter, year=year)
