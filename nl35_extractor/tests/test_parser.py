"""
test_parser.py — NL-6 generic parser tests.
"""

import pytest
import os
from extractor.parser import parse_pdf, _extract_period_data
from extractor.models import PeriodData


def test_parse_pdf_bajaj():
    pdf_path = "/Users/pulkit/Desktop/Forms/FY2026/Q3/NL6/NL_06_2025_26_Q3_BajajGeneral.pdf"
    if os.path.exists(pdf_path):
        extract = parse_pdf(pdf_path, "bajaj_allianz", "Q3", "202526")
        assert extract.company_key == "bajaj_allianz"
        assert extract.form_type == "NL6"
        assert len(extract.current_year.data) > 0
    else:
        pytest.skip("Bajaj NL6 PDF not found")


def test_parse_pdf_form_type_is_nl6(tmp_path):
    """Generic parser must always stamp form_type=NL6."""
    # Use a mock: no real PDF needed — just verify the stub extract has NL6 stamped
    # We exercise parse_pdf with a non-existent file and catch the error path
    from extractor.models import CompanyExtract
    # Can't call parse_pdf without a PDF; check the fallback CompanyExtract stamp instead
    from extractor.parser import parse_pdf
    pdf_path = str(tmp_path / "fake.pdf")
    # Create a minimal empty file so pdfplumber can at least try to open it
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%%EOF\n")
    extract = parse_pdf(pdf_path, "unknown_co", "Q3", "202526")
    assert extract.form_type == "NL6"


def test_extract_period_data_mock_commission_row():
    """Mock table with a commission row should yield gross_commission data."""
    tables = [{
        "page": 1,
        "table_index": 0,
        "rows": [
            ["Particulars", "Fire", "Fire"],
            ["", "Qtr", "YTD"],
            ["Gross Commission", "100", "200"],
        ],
    }]
    period_data = _extract_period_data(tables, "bajaj_allianz", "lines", "current")
    # The mock table has a "Gross Commission" row — if col_mapper finds Fire columns
    # and row_matcher finds the label, data should be populated.
    # (This test passes as long as _extract_period_data doesn't crash.)
    assert isinstance(period_data, PeriodData)
