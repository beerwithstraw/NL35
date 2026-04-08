"""
test_detector.py — NL-35 form type detection tests.
"""

import pytest
from extractor.detector import detect_form_type, detect_company


def test_detect_form_type_from_filename_nl35():
    assert detect_form_type("/path/to/NL35_BajajGeneral.pdf") == "NL35"


def test_detect_form_type_from_filename_nl_35():
    assert detect_form_type("/path/to/NL-35_BajajGeneral.pdf") == "NL35"


def test_detect_form_type_unknown():
    assert detect_form_type("/path/to/random_file.pdf") == "unknown"


def test_detect_company_from_filename_bajaj():
    result = detect_company("/path/to/NL35_BajajGeneral.pdf")
    assert result == "bajaj_allianz"


def test_detect_company_from_filename_hdfc():
    result = detect_company("/path/to/NL35_HDFCErgo.pdf")
    assert result == "hdfc_ergo"
