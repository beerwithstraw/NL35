"""
Generic table collection logic for NL-35.
Used primarily by the pipeline for pre-flight checks; dedicated parsers
call pdfplumber directly via _base_nl35.get_nl35_pages().
"""

import pdfplumber
import logging
from typing import List

from config.settings import COLLECTOR_SNAP_TOLERANCE_LINES

logger = logging.getLogger(__name__)


def collect_tables(pdf_path: str, extraction_strategy: str = "lines") -> list:
    """
    Returns list of table objects, each with page metadata preserved.
    Each item: {"page": int, "table_index": int, "rows": list[list[str]]}
    """
    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "snap_x_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "snap_y_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "intersection_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "join_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "join_x_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
        "join_y_tolerance": COLLECTOR_SNAP_TOLERANCE_LINES,
    }

    try:
        table_data = []
        with pdfplumber.open(pdf_path) as pdf:
            from extractor.companies._base_nl35 import get_nl35_pages
            for i, page in enumerate(get_nl35_pages(pdf)):
                tables = page.extract_tables(table_settings=settings)
                if not tables:
                    continue

                for t_idx, table in enumerate(tables):
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [
                            str(cell).strip() if cell is not None else ""
                            for cell in row
                        ]
                        if any(cell for cell in cleaned_row):
                            cleaned_table.append(cleaned_row)

                    if cleaned_table and max(len(r) for r in cleaned_table) >= 3:
                        table_data.append({
                            "page": i + 1,
                            "table_index": t_idx,
                            "rows": cleaned_table,
                        })

        if not table_data:
            logger.warning(f"Extracted table is empty for {pdf_path}")

        return table_data

    except Exception as e:
        logger.error(f"Table extraction failed for {pdf_path}: {e}")
        return []
