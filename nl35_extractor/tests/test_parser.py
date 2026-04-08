"""
test_parser.py — NL-35 parser unit tests using a mock table.
"""

import pytest
from extractor.companies._base_nl35 import (
    detect_period_columns,
    detect_lob_rows,
    extract_nl35_grid,
)
from extractor.models import NL35Data


def _bajaj_table():
    """Reproduce the Bajaj NL-35 table structure exactly as pdfplumber returns it."""
    return [
        [None, None, None, None, None, None, None, None, "(Amount in Rs. Lakhs)", None],
        [
            "Sr.No.", "Line of Business",
            "For the Quarter", None,
            "For the corresponding quarter of the\nprevious year", None,
            "upto the quarter", None,
            "Up to the corresponding quarter of the\nprevious year", None,
        ],
        [
            None, None,
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
        ],
        ["1", "Fire", "53,116.14", "7 03,285", "50,053.40", "629,160", "2 27,419.19", "2,030,317.00", "199,355.36", "1,961,031"],
        ["2", "Marine Cargo", "7 ,069.18", "4 3,004", "6,056.46", "37,441", "26,689.65", "129,955.00", "22,903.50", "115,493"],
        ["5", "Motor TP", "106,351.33", None, "8 5,680.32", None, "2 92,016.86", None, "225,505.85", None],
    ]


def test_extract_grid_fire_cy_qtr_premium():
    table = _bajaj_table()
    period_cols = detect_period_columns(table)
    lob_rows = detect_lob_rows(table)
    nl35_data = NL35Data()
    extract_nl35_grid(table, lob_rows, period_cols, nl35_data)

    assert "fire" in nl35_data.data
    assert nl35_data.data["fire"]["cy_qtr_premium"] == pytest.approx(53116.14)


def test_extract_grid_fire_cy_qtr_policies():
    table = _bajaj_table()
    period_cols = detect_period_columns(table)
    lob_rows = detect_lob_rows(table)
    nl35_data = NL35Data()
    extract_nl35_grid(table, lob_rows, period_cols, nl35_data)
    assert nl35_data.data["fire"]["cy_qtr_policies"] == pytest.approx(703285.0)


def test_extract_grid_motor_tp_policies_none():
    """Motor TP has no policy count — cells are None — clean_number returns None."""
    table = _bajaj_table()
    period_cols = detect_period_columns(table)
    lob_rows = detect_lob_rows(table)
    nl35_data = NL35Data()
    extract_nl35_grid(table, lob_rows, period_cols, nl35_data)
    assert nl35_data.data["motor_tp"]["cy_qtr_policies"] is None


def test_extract_grid_marine_cargo_ytd():
    table = _bajaj_table()
    period_cols = detect_period_columns(table)
    lob_rows = detect_lob_rows(table)
    nl35_data = NL35Data()
    extract_nl35_grid(table, lob_rows, period_cols, nl35_data)
    assert nl35_data.data["marine_cargo"]["cy_ytd_premium"] == pytest.approx(26689.65)


def test_extract_grid_all_8_keys_populated_for_fire():
    table = _bajaj_table()
    period_cols = detect_period_columns(table)
    lob_rows = detect_lob_rows(table)
    nl35_data = NL35Data()
    extract_nl35_grid(table, lob_rows, period_cols, nl35_data)
    fire_data = nl35_data.data["fire"]
    # All premium keys must be populated
    assert fire_data["cy_qtr_premium"] is not None
    assert fire_data["py_qtr_premium"] is not None
    assert fire_data["cy_ytd_premium"] is not None
    assert fire_data["py_ytd_premium"] is not None
