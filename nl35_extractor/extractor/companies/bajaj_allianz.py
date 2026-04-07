"""
Parser for Bajaj Allianz General Insurance Company Limited (NL-6 Commission Schedule).
Also filed as "BajajGeneral" in IRDAI submissions — same company.

PDF Structure: 4 pages, 2 tables per page.
  Pages 1 & 3 = CY (period ended Dec 2025)
  Pages 2 & 4 = PY (period ended Dec 2024)

  Page 1 (CY) / Page 2 (PY):
    T0 — top section: fire, marine_cargo, marine_hull, total_marine,
          motor_od, motor_tp, total_motor, health, personal_accident,
          travel_insurance
    T1 — channel section: same LOB columns, no header rows

  Page 3 (CY) / Page 4 (PY):
    T0 — top section: total_health, wc_el, public_product_liability,
          engineering, aviation, crop_insurance, credit_insurance,
          other_miscellaneous, total_miscellaneous, grand_total
    T1 — channel section: same LOB columns, no header rows

Two-row LOB header: row 0 has category spans ("Miscellaneous"), row 1 has
  actual sub-LOB names. merge_lob_header_rows() resolves this.

CY/PY detection: period headers contain "Dec 2025" / "Dec 2024".
  detect_period_year() returns None (no YYYY-YY pattern).
  detect_calendar_year() extracts 2025 / 2024 from T0.
  Max year → CY; lower year → PY.

Channel section: in T1 (separate table, no boundary row).
  detect_row_metrics(T1, start_in_channel_section=True).
  lob_cols reused from T0 (same column layout).
"""

import logging
from pathlib import Path

import pdfplumber

from extractor.models import CompanyExtract, PeriodData
from extractor.companies._base_nl6 import (
    get_nl6_pages,
    resolve_company_name,
    merge_lob_header_rows,
    detect_row_metrics,
    detect_calendar_year,
    extract_grid,
)

logger = logging.getLogger(__name__)

_FALLBACK_NAME = "Bajaj Allianz General Insurance Company Limited"


def parse_bajaj_allianz(
    pdf_path: str,
    company_key: str,
    quarter: str = "",
    year: str = "",
) -> CompanyExtract:
    logger.info(f"Parsing Bajaj Allianz NL-6 PDF: {pdf_path}")
    company_name = resolve_company_name(company_key, pdf_path, _FALLBACK_NAME)

    extract = CompanyExtract(
        source_file=Path(pdf_path).name,
        company_key=company_key,
        company_name=company_name,
        form_type="NL6",
        quarter=quarter,
        year=year,
    )

    cy = PeriodData(period_label="current")
    py = PeriodData(period_label="prior")

    # First pass: collect (cal_year, t0, t1, lob_cols) for CY/PY assignment
    page_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in get_nl6_pages(pdf):
            tables = page.extract_tables()
            if len(tables) < 2:
                continue
            t0, t1 = tables[0], tables[1]

            lob_cols = merge_lob_header_rows(t0)
            if not lob_cols:
                continue

            cal_year = detect_calendar_year(t0)
            page_data.append((cal_year, t0, t1, lob_cols))

    if not page_data:
        logger.warning("Bajaj Allianz: no valid pages found")
        extract.current_year = cy
        extract.prior_year = py
        return extract

    # Max calendar year = CY; lower = PY
    years = [d[0] for d in page_data if d[0] is not None]
    max_year = max(years) if years else None

    for cal_year, t0, t1, lob_cols in page_data:
        if max_year is not None:
            period_data = cy if (cal_year is not None and cal_year >= max_year) else py
        else:
            period_data = cy  # fallback: all tables treated as CY

        rm_top = detect_row_metrics(t0)
        if rm_top:
            extract_grid(t0, rm_top, lob_cols, period_data)

        rm_ch = detect_row_metrics(t1, start_in_channel_section=True)
        if rm_ch:
            extract_grid(t1, rm_ch, lob_cols, period_data)

    logger.info(
        f"Extraction complete: CY {len(cy.data)} LOBs, PY {len(py.data)} LOBs."
    )
    extract.current_year = cy
    extract.prior_year = py
    return extract
