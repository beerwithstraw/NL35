"""
test_validation.py — NL-6 commission identity check tests.
"""

import os
from extractor.models import CompanyExtract, PeriodData
from validation.checks import (
    _check_gross_commission_identity,
    _check_net_commission_identity,
    _check_channel_total_identity,
    _check_segment_sum,
    _check_completeness_refined,
    run_validations,
    ValidationResult,
    write_validation_report,
)


def _exc():
    return CompanyExtract(
        source_file="test.pdf",
        company_key="bajaj_allianz",
        company_name="Bajaj Allianz General Insurance Company Limited",
        form_type="NL6",
        quarter="Q3",
        year="202526",
    )


# ---------------------------------------------------------------------------
# Gross Commission Identity: Gross = CR + Rewards + Distribution_Fees
# ---------------------------------------------------------------------------

def test_gross_commission_identity_pass():
    lob_data = {
        "gross_commission":       {"qtr": 100.0},
        "commission_remuneration": {"qtr": 60.0},
        "rewards":                {"qtr": 25.0},
        "distribution_fees":      {"qtr": 15.0},
    }
    res = _check_gross_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "PASS"
    assert abs(res.delta) <= 3.0


def test_gross_commission_identity_fail():
    lob_data = {
        "gross_commission":       {"qtr": 200.0},   # wrong total
        "commission_remuneration": {"qtr": 60.0},
        "rewards":                {"qtr": 25.0},
        "distribution_fees":      {"qtr": 15.0},
    }
    res = _check_gross_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "FAIL"


def test_gross_commission_identity_returns_none_when_gross_missing():
    lob_data = {
        "commission_remuneration": {"qtr": 60.0},
        "rewards":                {"qtr": 25.0},
    }
    res = _check_gross_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is None


# ---------------------------------------------------------------------------
# Net Commission Identity: Net = Gross + RI_Acc + RI_Ced
# ---------------------------------------------------------------------------

def test_net_commission_identity_pass():
    lob_data = {
        "net_commission":          {"qtr": 95.0},
        "gross_commission":        {"qtr": 100.0},
        "ri_accepted_commission":  {"qtr": 5.0},
        "ri_ceded_commission":     {"qtr": -10.0},
    }
    # 100 + 5 + (-10) = 95. PASS.
    res = _check_net_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "PASS"


def test_net_commission_identity_fail():
    lob_data = {
        "net_commission":   {"qtr": 50.0},    # wrong
        "gross_commission": {"qtr": 100.0},
    }
    res = _check_net_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "FAIL"


def test_net_commission_identity_none_when_net_missing():
    lob_data = {"gross_commission": {"qtr": 100.0}}
    res = _check_net_commission_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is None


# ---------------------------------------------------------------------------
# Channel Total Identity: Total = sum of channel rows
# ---------------------------------------------------------------------------

def test_channel_total_identity_pass():
    lob_data = {
        "total_channel": {"qtr": 100.0},
        "agent":         {"qtr": 40.0},
        "broker":        {"qtr": 35.0},
        "direct_selling": {"qtr": 25.0},
    }
    res = _check_channel_total_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "PASS"


def test_channel_total_identity_fail():
    lob_data = {
        "total_channel": {"qtr": 200.0},   # wrong
        "agent":         {"qtr": 40.0},
        "broker":        {"qtr": 35.0},
    }
    res = _check_channel_total_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is not None
    assert res.status == "FAIL"


def test_channel_total_returns_none_when_total_missing():
    lob_data = {"agent": {"qtr": 40.0}}
    res = _check_channel_total_identity(_exc(), "fire", "current_qtr", lob_data, "qtr")
    assert res is None


# ---------------------------------------------------------------------------
# Segment sum
# ---------------------------------------------------------------------------

def test_check_segment_sum_pass():
    exc = _exc()
    period_data = PeriodData(period_label="current")
    period_data.data["marine_cargo"] = {"gross_commission": {"qtr": 10.0}}
    period_data.data["marine_hull"]  = {"gross_commission": {"qtr": 20.0}}
    period_data.data["total_marine"] = {"gross_commission": {"qtr": 30.0}}
    res = _check_segment_sum(exc, "total_marine", ["marine_cargo", "marine_hull"], "current_qtr", period_data, "qtr")
    assert res is not None
    assert res.status == "PASS"


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------

def test_check_completeness_refined():
    exc = _exc()
    period_data = PeriodData(period_label="current")
    # All LOBs missing
    results = _check_completeness_refined(exc, "current", period_data)
    assert len(results) > 0
    assert any(r.check_name == "COMPLETENESS" for r in results)


# ---------------------------------------------------------------------------
# run_validations smoke test
# ---------------------------------------------------------------------------

def test_run_validations_smoke():
    exc = _exc()
    exc.current_year = PeriodData(period_label="current")
    exc.current_year.data["fire"] = {
        "gross_commission":        {"qtr": 100.0, "ytd": 200.0},
        "commission_remuneration": {"qtr": 60.0,  "ytd": 120.0},
        "rewards":                 {"qtr": 25.0,  "ytd":  50.0},
        "distribution_fees":       {"qtr": 15.0,  "ytd":  30.0},
        "net_commission":          {"qtr": 95.0,  "ytd": 190.0},
        "ri_accepted_commission":  {"qtr":  5.0,  "ytd":  10.0},
        "ri_ceded_commission":     {"qtr": -10.0, "ytd": -20.0},
    }
    results = run_validations([exc])
    assert len(results) > 0
    pass_results = [r for r in results if r.status == "PASS"]
    assert len(pass_results) > 0


# ---------------------------------------------------------------------------
# write_validation_report
# ---------------------------------------------------------------------------

def test_write_validation_report(tmp_path):
    res = [ValidationResult("Bajaj", "Q3", "202526", "fire", "current_qtr", "TEST", "PASS", 100.0, 100.0, 0.0, "")]
    output = tmp_path / "report.csv"
    write_validation_report(res, str(output))
    assert os.path.exists(output)
