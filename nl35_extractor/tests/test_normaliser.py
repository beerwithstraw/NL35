"""
test_normaliser.py — clean_number tests.
"""

from extractor.normaliser import clean_number, normalise_text
import pytest

@pytest.mark.parametrize("raw, expected", [
    (None,          None),
    ("",            None),
    ("-",           None),
    ("0",           0.0),
    ("1,357",       1357.0),
    ("(500)",       -500.0),
])
def test_clean_number(raw, expected):
    res = clean_number(raw)
    if expected is None:
        assert res is None
    else:
        assert res == pytest.approx(expected)

def test_normalise_text():
    assert normalise_text("  Policy Related  ") == "policy related"
