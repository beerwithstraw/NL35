"""
test_detector.py — NL-6 form/company detection tests.
"""

import pytest
from extractor.detector import detect_all, detect_company
import os


def test_detect_all_bajaj():
    pdf_path = "/Users/pulkit/Desktop/Forms/FY2026/Q3/NL6/NL_06_2025_26_Q3_BajajGeneral.pdf"
    if os.path.exists(pdf_path):
        form, company, quarter, year = detect_all(pdf_path)
        assert form == "NL6"
        assert company == "bajaj_allianz"
    else:
        pytest.skip("Bajaj NL6 PDF not found at expected path")


def test_filename_detection_nl6():
    """Filenames containing NL_06/NL-6/NL6 should detect as NL6 via filename pattern."""
    from extractor.detector import _FILENAME_NL6_PATTERN
    # Verify the pattern matches the standard naming conventions
    assert _FILENAME_NL6_PATTERN.search("NL_06_2025_26_Q3_BajajGeneral.pdf")
    assert _FILENAME_NL6_PATTERN.search("NL6_Q3_202526_Acko.pdf")
    assert _FILENAME_NL6_PATTERN.search("NL-6_2025_Q1_Company.pdf")
    assert not _FILENAME_NL6_PATTERN.search("NL_05_2025_26_Q3_BajajGeneral.pdf")


def test_detect_company_bajaj():
    result = detect_company("NL_06_2025_26_Q3_BajajGeneral.pdf")
    assert result == "bajaj_allianz"


def test_detect_national_insurance():
    result = detect_company("NL6_Q3_202526_NationalInsurance.pdf")
    assert result == "national_insurance"


def test_detect_new_india():
    result = detect_company("NL6_Q3_202526_NewIndia.pdf")
    assert result == "new_india"
