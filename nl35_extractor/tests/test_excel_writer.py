"""
test_excel_writer.py — NL-6 Excel output tests.
"""

import os
import pytest
from openpyxl import load_workbook
from output.excel_writer import save_workbook
from extractor.models import CompanyExtract, PeriodData


def _make_extract(lob: str = "fire", metric: str = "gross_commission", value: float = 100.0):
    extract = CompanyExtract(
        source_file="test.pdf",
        company_key="bajaj_allianz",
        company_name="Bajaj Allianz General Insurance Company Limited",
        form_type="NL6",
        quarter="Q3",
        year="202526",
    )
    extract.current_year = PeriodData(period_label="current")
    extract.current_year.data[lob] = {metric: {"qtr": value, "ytd": value * 2}}
    return extract


def test_save_workbook_creates_file(tmp_path):
    output_file = tmp_path / "nl6_test.xlsx"
    save_workbook([_make_extract()], str(output_file))
    assert os.path.exists(output_file)


def test_save_workbook_has_expected_sheets(tmp_path):
    output_file = tmp_path / "nl6_test.xlsx"
    save_workbook([_make_extract()], str(output_file))
    wb = load_workbook(output_file)
    assert "Master_Data" in wb.sheetnames
    assert "_meta" in wb.sheetnames
    assert "BajajAllianz_Q3_202526" in wb.sheetnames


def test_save_workbook_empty_list(tmp_path):
    output_file = tmp_path / "empty.xlsx"
    save_workbook([], str(output_file))
    assert os.path.exists(output_file)


def test_master_data_column_headers(tmp_path):
    """Master_Data row 1 must contain NL6 commission column names."""
    from config.settings import MASTER_COLUMNS
    output_file = tmp_path / "headers.xlsx"
    save_workbook([_make_extract()], str(output_file))
    wb = load_workbook(output_file)
    ws = wb["Master_Data"]
    header_row = [ws.cell(row=1, column=c).value for c in range(1, len(MASTER_COLUMNS) + 1)]
    assert "Gross_Commission" in header_row
    assert "Net_Commission" in header_row
    assert "Agent" in header_row
    assert "Total_Channel" in header_row
    # NL5 columns must NOT be present
    assert "Claims_Paid_Direct" not in header_row
    assert "Net_Incurred_Claims" not in header_row


def test_gross_commission_value_written(tmp_path):
    output_file = tmp_path / "values.xlsx"
    extract = _make_extract(lob="fire", metric="gross_commission", value=500.0)
    save_workbook([extract], str(output_file))
    wb = load_workbook(output_file)
    ws = wb["Master_Data"]

    from config.settings import MASTER_COLUMNS
    gross_col = MASTER_COLUMNS.index("Gross_Commission") + 1
    # Find a data row where LOB is fire
    data_rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[7] == "fire":   # column H (index 7) = LOB_PARTICULARS or Grouped_LOB
            data_rows.append(row)
    # At least one row should have the gross commission value
    values_in_gross_col = [ws.cell(row=r, column=gross_col).value for r in range(2, ws.max_row + 1)]
    assert 500.0 in values_in_gross_col
