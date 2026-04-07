"""
test_heuristics.py — NL-6 section-boundary and skip-row detection tests.

Tests detect_row_metrics() in _base_nl6.py, which is section-aware:
  - Rows before "break-up of the expenses" → top-section metrics
  - Rows after the separator → channel-section metrics
  - "MISP (Direct)" maps to distribution_fees before, misp_direct after
  - "In India" / "Outside India" are always skipped
"""

import pytest
from extractor.companies._base_nl6 import detect_row_metrics


def _make_table(label_rows):
    """Build a minimal table with labels in col 0 and dummy data in col 1."""
    return [[label, "0"] for label in label_rows]


# ---------------------------------------------------------------------------
# Top-section detection
# ---------------------------------------------------------------------------

def test_top_section_basic():
    table = _make_table([
        "Commission & Remuneration",
        "Rewards",
        "Distribution Fees",
        "Gross Commission",
        "Add: Commission on Re-insurance Accepted",
        "Less: Commission on Re-insurance Ceded",
        "Net Commission",
    ])
    metrics = detect_row_metrics(table)
    assert metrics[0] == "commission_remuneration"
    assert metrics[1] == "rewards"
    assert metrics[2] == "distribution_fees"
    assert metrics[3] == "gross_commission"
    assert metrics[4] == "ri_accepted_commission"
    assert metrics[5] == "ri_ceded_commission"
    assert metrics[6] == "net_commission"


def test_misp_direct_in_top_section_maps_to_distribution_fees():
    """Bajaj pages 3/4: 'MISP (Direct)' appears in top section position 3."""
    table = _make_table([
        "Commission & Remuneration",
        "Rewards",
        "MISP (Direct)",          # top section → distribution_fees
        "Gross Commission",
        "Net Commission",
    ])
    metrics = detect_row_metrics(table)
    assert metrics[2] == "distribution_fees"
    assert metrics[3] == "gross_commission"


# ---------------------------------------------------------------------------
# Channel-section detection (after boundary)
# ---------------------------------------------------------------------------

def test_channel_section_basic():
    table = _make_table([
        "Gross Commission",
        "Net Commission",
        "Break-up of the expenses (Gross) incurred to procure business",
        "Agent",
        "Broker",
        "Corporate Agent (Bank)",
        "Corporate Agent (Other)",
        "MISP (Direct)",          # channel section → misp_direct
        "MISP (Dealership)",
        "Web Aggregator",
        "Insurance Marketing Firm",
        "Common Service Centre",
        "Point of Sales",
        "Direct Selling",
        "Others",
        "Total",
    ])
    metrics = detect_row_metrics(table)
    # top section
    assert metrics[0] == "gross_commission"
    assert metrics[1] == "net_commission"
    # boundary row itself is NOT in metrics
    assert 2 not in metrics
    # channel section
    assert metrics[3] == "agent"
    assert metrics[4] == "broker"
    assert metrics[5] == "corporate_agent_bank"
    assert metrics[6] == "corporate_agent_other"
    assert metrics[7] == "misp_direct"
    assert metrics[8] == "misp_dealership"
    assert metrics[9] == "web_aggregator"
    assert metrics[10] == "insurance_marketing_firm"
    assert metrics[11] == "common_service_centre"
    assert metrics[12] == "point_of_sales"
    assert metrics[13] == "direct_selling"
    assert metrics[14] == "other_channels"
    assert metrics[15] == "total_channel"


def test_misp_direct_disambiguation():
    """MISP (Direct) must map differently depending on section."""
    table = _make_table([
        "MISP (Direct)",    # before boundary → distribution_fees
        "Gross Commission",
        "Break-up of the expenses incurred to procure business",
        "MISP (Direct)",    # after boundary → misp_direct
        "Total",
    ])
    metrics = detect_row_metrics(table)
    assert metrics[0] == "distribution_fees"
    assert metrics[3] == "misp_direct"
    assert metrics[4] == "total_channel"


# ---------------------------------------------------------------------------
# Skip-row tests
# ---------------------------------------------------------------------------

def test_in_india_skipped():
    table = _make_table([
        "Gross Commission",
        "Net Commission",
        "In India",
        "Outside India",
    ])
    metrics = detect_row_metrics(table)
    assert 2 not in metrics
    assert 3 not in metrics
    assert metrics[0] == "gross_commission"
    assert metrics[1] == "net_commission"


def test_empty_rows_ignored():
    table = [
        ["", ""],
        ["Commission & Remuneration", "0"],
        [None, "0"],
        ["Rewards", "0"],
    ]
    metrics = detect_row_metrics(table)
    assert metrics[1] == "commission_remuneration"
    assert metrics[3] == "rewards"
    assert 0 not in metrics
    assert 2 not in metrics


# ---------------------------------------------------------------------------
# Duplicate suppression
# ---------------------------------------------------------------------------

def test_no_duplicate_metric_assignments():
    """Each canonical metric key may appear at most once."""
    table = _make_table([
        "Gross Commission",
        "Gross Commission",   # duplicate label
        "Net Commission",
    ])
    metrics = detect_row_metrics(table)
    values = list(metrics.values())
    assert values.count("gross_commission") == 1
