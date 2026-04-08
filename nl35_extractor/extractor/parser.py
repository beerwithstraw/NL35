"""
NL-35 parser entry point.

Routes to the dedicated parser for each company (DEDICATED_PARSER in
company_registry.py). NL-35 has no generic fallback parser — all companies
must have a dedicated parser registered.
"""

import logging
from pathlib import Path

from config.company_registry import DEDICATED_PARSER, COMPANY_DISPLAY_NAMES
from extractor.models import NL35Extract

logger = logging.getLogger(__name__)


def parse_pdf(pdf_path: str, company_key: str, quarter: str = "", year: str = "") -> NL35Extract:
    """
    Parse an NL-35 PDF and return an NL35Extract.
    Routes to the dedicated parser registered for the company.
    """
    logger.info(f"Parsing PDF: {pdf_path} for company: {company_key}")

    company_name = COMPANY_DISPLAY_NAMES.get(company_key, str(company_key).title())

    dedicated_func_name = DEDICATED_PARSER.get(company_key)
    if dedicated_func_name:
        from extractor.companies import PARSER_REGISTRY
        dedicated_func = PARSER_REGISTRY.get(dedicated_func_name)
        if dedicated_func:
            logger.info(f"Routing to dedicated parser: {dedicated_func_name}")
            return dedicated_func(pdf_path, company_key, quarter, year)
        else:
            logger.error(f"Dedicated parser '{dedicated_func_name}' not in PARSER_REGISTRY")

    # No parser available — return empty extract with error
    extract = NL35Extract(
        source_file=Path(pdf_path).name,
        company_key=company_key,
        company_name=company_name,
        form_type="NL35",
        quarter=quarter,
        year=year,
    )
    extract.extraction_errors.append(
        f"No dedicated NL-35 parser registered for {company_key}"
    )
    logger.error(f"No dedicated NL-35 parser for {company_key}")
    return extract
