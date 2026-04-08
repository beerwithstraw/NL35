"""
test_heuristics.py — NL-35 period column and LOB row detection tests.
"""

import pytest
from extractor.companies._base_nl35 import detect_period_columns, detect_lob_rows


# ---------------------------------------------------------------------------
# detect_period_columns
# ---------------------------------------------------------------------------

def _make_header_table():
    """Minimal 3-row table matching Bajaj NL-35 header structure."""
    return [
        [None, None, None, None, None, None, None, None, "(Amount in Rs. Lakhs)", None],
        [
            "Sr.No.", "Line of Business",
            "For the Quarter", None,
            "For the corresponding quarter of the previous year", None,
            "upto the quarter", None,
            "Up to the corresponding quarter of the previous year", None,
        ],
        [
            None, None,
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
            "Premium", "No. of Policies",
        ],
        ["1", "Fire", "53116.14", "703285", "50053.40", "629160", "227419.19", "2030317", "199355.36", "1961031"],
    ]


def test_detect_period_columns_basic():
    table = _make_header_table()
    cols = detect_period_columns(table)
    assert cols["cy_qtr_premium"] == 2
    assert cols["cy_qtr_policies"] == 3
    assert cols["py_qtr_premium"] == 4
    assert cols["py_qtr_policies"] == 5
    assert cols["cy_ytd_premium"] == 6
    assert cols["cy_ytd_policies"] == 7
    assert cols["py_ytd_premium"] == 8
    assert cols["py_ytd_policies"] == 9


def test_detect_period_columns_all_8_keys():
    table = _make_header_table()
    cols = detect_period_columns(table)
    assert len(cols) == 8


def test_detect_period_columns_empty_table():
    assert detect_period_columns([]) == {}


def test_detect_period_columns_too_few_rows():
    assert detect_period_columns([["a", "b"]]) == {}


# ---------------------------------------------------------------------------
# detect_lob_rows
# ---------------------------------------------------------------------------

def _make_lob_table():
    return [
        [None, None, None, None, None, None, None, None, None, None],
        ["Sr.No.", "Line of Business", "For the Quarter", None, None, None, None, None, None, None],
        [None, None, "Premium", "No. of Policies", None, None, None, None, None, None],
        ["1", "Fire", "53116.14", "703285", "50053.40", "629160", "227419.19", "2030317", "199355.36", "1961031"],
        ["2", "Marine Cargo", "7069.18", "43004", "6056.46", "37441", "26689.65", "129955", "22903.50", "115493"],
        ["3", "Marine Other than Cargo", "1094.52", "10", "845.71", "11", "2451.93", "39", "2243.44", "33"],
        ["4", "Motor OD", "96061.99", "3602870", "79367.11", "2396389", "250795.91", "9243149", "232036.36", "6367693"],
        ["5", "Motor TP", "106351.33", None, "85680.32", None, "292016.86", None, "225505.85", None],
        ["6", "Health", "364221.12", "1595624", "322021.21", "1580273", "724550.04", "4188523", "679397.90", "5232437"],
        ["7", "Personal Accident", "3645.59", "329819", "4088.42", "696232", "14744.37", "1098689", "17355.24", "1687847"],
        ["8", "Travel", "3449.20", "213642", "3654.22", "224556", "14389.58", "688317", "15905.32", "781280"],
        ["9", "Workmen\u2019s Compensation/ Employer\u2019s liability", "1849.28", "15220", "1695.18", "13247", "6352.59", "48777", "5586.65", "42501"],
        ["10", "Public/ Product Liability", "1863.31", "1184", "1865.19", "1088", "8835.62", "4011", "7680.89", "3691"],
        ["11", "Engineering", "14673.33", "4050", "11903.91", "3802", "41901.78", "11179", "35167.97", "10711"],
        ["12", "Aviation", "387.44", "307", "233.27", "103", "1266.78", "1356", "1002.45", "355"],
        ["13", "Crop Insurance", "42726.41", "520921", "61241.84", "6561663", "148182.82", "4908269", "153738.19", "12331157"],
        ["14", "Credit Insurance", "943.97", "11", "565.98", "9", "3347.40", "65", "2354.81", "30"],
        ["15", "Other Miscellaneous Segments", "35026.67", "1914389", "26257.71", "1874720", "124970.23", "5121450", "111011.53", "7015572"],
    ]


def test_detect_lob_rows_all_15_lobs():
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    assert len(lob_rows) == 15


def test_detect_lob_rows_correct_keys():
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    lob_values = set(lob_rows.values())
    assert "fire" in lob_values
    assert "motor_od" in lob_values
    assert "motor_tp" in lob_values
    assert "health" in lob_values
    assert "other_miscellaneous" in lob_values


def test_detect_lob_rows_fire_at_row_3():
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    # Row 3 is "Fire" (0-indexed)
    assert lob_rows.get(3) == "fire"


def test_detect_lob_rows_wc_el_matched():
    """Curly-apostrophe Workmen's Compensation maps to wc_el."""
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    assert "wc_el" in lob_rows.values()


def test_detect_lob_rows_skips_header():
    """Header rows (Sr.No., Line of Business) must not appear."""
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    for row_idx, lob_key in lob_rows.items():
        assert lob_key not in ("", None)
    # No "Sr.No." key should be in values
    assert all(v in {
        "fire", "marine_cargo", "marine_hull", "motor_od", "motor_tp",
        "health", "personal_accident", "travel_insurance", "wc_el",
        "public_product_liability", "engineering", "aviation",
        "crop_insurance", "credit_insurance", "other_miscellaneous",
    } for v in lob_rows.values())


def test_detect_lob_rows_no_duplicates():
    table = _make_lob_table()
    lob_rows = detect_lob_rows(table)
    values = list(lob_rows.values())
    assert len(values) == len(set(values))
