"""
test_collector.py — NL-35 page detection and collector smoke tests.
"""

import pytest
from extractor.companies._base_nl35 import get_nl35_pages


class _MockPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _MockPDF:
    def __init__(self, pages):
        self.pages = pages


def test_get_nl35_pages_small_pdf():
    """For PDFs with <= 4 pages, return all pages."""
    pdf = _MockPDF([_MockPage("some text")] * 3)
    result = get_nl35_pages(pdf)
    assert len(result) == 3


def test_get_nl35_pages_large_pdf_filters():
    """For large PDFs, return only pages with NL-35 keywords."""
    pages = [_MockPage("unrelated content")] * 10
    pages[3] = _MockPage("FORM NL-35 QUARTERLY BUSINESS RETURNS")
    pdf = _MockPDF(pages)
    result = get_nl35_pages(pdf)
    assert len(result) == 1


def test_get_nl35_pages_large_pdf_no_match_returns_all():
    """If no NL-35 pages found in large PDF, return all pages as fallback."""
    pdf = _MockPDF([_MockPage("unrelated content")] * 10)
    result = get_nl35_pages(pdf)
    assert len(result) == 10
