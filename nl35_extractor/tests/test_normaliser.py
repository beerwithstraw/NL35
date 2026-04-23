"""
test_normaliser.py — clean_number tests (unchanged from NL-35, shared logic).
"""

from extractor.normaliser import clean_number, normalise_text


def test_clean_number_basic():
    assert clean_number("53,116.14") == 53116.14


def test_clean_number_space_broken():
    """Space-broken numbers from Bajaj NL-35 PDF (e.g. '7 03,285')."""
    assert clean_number("7 03,285") == 703285.0


def test_clean_number_none():
    assert clean_number(None) is None


def test_clean_number_dash():
    assert clean_number("-") is None


def test_clean_number_negative():
    assert clean_number("-100.0") == -100.0


def test_clean_number_parentheses():
    assert clean_number("(500)") == -500.0


def test_normalise_text_basic():
    assert normalise_text("Fire") == "fire"


def test_normalise_text_wc_el():
    result = normalise_text("Workmen\u2019s Compensation/ Employer\u2019s liability")
    assert "workmen" in result
    assert "compensation" in result


def test_normalise_text_none():
    assert normalise_text(None) == ""
