"""
The Generic Parser.

Coordinates the Collector, Col Mapper, and Row Matcher, and performs the
actual cell extraction block (clean_number).

Source: approach document Section 9
"""

import logging
from typing import Dict, List
from pathlib import Path

from config.company_registry import EXTRACTION_STRATEGY, COMPANY_DISPLAY_NAMES
from extractor.collector import collect_tables
from extractor.col_mapper import build_column_map
from extractor.row_matcher import build_row_map
from extractor.normaliser import clean_number
from extractor.models import CompanyExtract, PeriodData

logger = logging.getLogger(__name__)


def _extract_period_data(tables: List[Dict], company_key: str, strategy: str, period_label: str) -> PeriodData:
    """
    Given a list of table objects, build maps, and extract either CY or PY data.
    """
    period_data = PeriodData(period_label=period_label)

    # Map 'current'/'prior' label to 'current'/'prior' in col_def
    year_filter = 'current' if period_label == 'current' else 'prior'

    for table_obj in tables:
        rows = table_obj["rows"]
        if not rows:
            continue

        col_map = build_column_map(rows, company_key, strategy, default_year=year_filter)
        if not col_map:
            logger.warning(f"No columns mapped for page {table_obj['page']} table {table_obj['table_index']}")
            continue

        row_map = build_row_map(rows)
        if not row_map:
            continue

        for row_key, row_idx in row_map.items():
            if row_idx >= len(rows):
                continue
            row_data = rows[row_idx]
            for col_idx, col_def in col_map.items():
                if col_idx < len(row_data):
                    # Filter by year if present in col_def (from col_mapper Step 3)
                    col_year = col_def.get("year", "current")  # Default to current if not specified
                    if col_year != year_filter:
                        continue

                    val = clean_number(row_data[col_idx])
                    lob = col_def["lob"]
                    period_col = col_def["period"]
                    score = col_def.get("score", 1.0)

                    if lob not in period_data.data:
                        period_data.data[lob] = {}
                    if row_key not in period_data.data[lob]:
                        period_data.data[lob][row_key] = {"qtr": None, "ytd": None}

                    if val is not None:
                        period_data.data[lob][row_key][period_col] = val

                    if score < 0.60:
                        period_data.low_confidence_cells.add((lob, row_key))

    # No sign heuristics for NL-6 commission schedules
    return period_data


def parse_pdf(pdf_path: str, company_key: str, quarter: str = "", year: str = "") -> CompanyExtract:
    """..."""
    logger.info(f"Parsing PDF: {pdf_path} for company: {company_key}")
    
    company_name = COMPANY_DISPLAY_NAMES.get(company_key, str(company_key).title())
    
    # Check for dedicated parser
    from config.company_registry import DEDICATED_PARSER
    dedicated_func_name = DEDICATED_PARSER.get(company_key)
    if dedicated_func_name:
        from extractor.companies import PARSER_REGISTRY
        dedicated_func = PARSER_REGISTRY.get(dedicated_func_name)
        if dedicated_func:
            logger.info(f"Routing to dedicated parser: {dedicated_func_name}")
            return dedicated_func(pdf_path, company_key, quarter, year)
    
    extract = CompanyExtract(
        source_file=Path(pdf_path).name,
        company_key=company_key,
        company_name=company_name,
        form_type="NL6",
        quarter=quarter,
        year=year,
    )
    
    strategy = EXTRACTION_STRATEGY.get(company_key, "lines")
    
    # Step 1: Collector
    tables = collect_tables(pdf_path, extraction_strategy=strategy)
    if not tables:
        logger.error("Collector returned no tables.")
        extract.extraction_errors.append("No tables extracted.")
        return extract
        
    logger.info(f"Collected {len(tables)} table blocks.")

    # Merge all table objects on the same page into a single row list.
    # This handles cases where pdfplumber splits a single logical table horizontally.
    page_to_rows = {}
    for t in tables:
        page = t["page"]
        if page not in page_to_rows:
            page_to_rows[page] = []
        page_to_rows[page].extend(t["rows"])

    merged_tables_by_page = [
        {"page": page, "table_index": 0, "rows": rows}
        for page, rows in page_to_rows.items()
    ]

    # Pass all pages to both period extractors; col_mapper filters by year label.
    cy_tables = merged_tables_by_page
    py_tables = merged_tables_by_page
    
    # Step 3: Extract Data
    extract.current_year = _extract_period_data(cy_tables, company_key, strategy, "current")
    
    # If no explicit py_tables were found (e.g. single 16-col table), 
    # we MUST attempt to extract PY from the same cy_tables list, 
    # as our new col_mapper might have found 'prior' columns there.
    if py_tables:
        extract.prior_year = _extract_period_data(py_tables, company_key, strategy, "prior")
    elif cy_tables:
        # Fallback: check if the 'cy_tables' actually contain 'prior' columns
        logger.info("No explicit PY tables, attempting PY extraction from CY tables as fallback.")
        py_data_fallback = _extract_period_data(cy_tables, company_key, strategy, "prior")
        if py_data_fallback and py_data_fallback.data:
            extract.prior_year = py_data_fallback
            
    # Log summary
    cy_lobs = len(extract.current_year.data) if extract.current_year else 0
    py_lobs = len(extract.prior_year.data) if extract.prior_year else 0
    logger.info(f"Extraction complete: CY found {cy_lobs} LOBs, PY found {py_lobs} LOBs.")
    
    return extract
