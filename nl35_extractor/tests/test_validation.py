"""
test_validation.py — NL-35 validation check tests.
"""

import os
from extractor.models import NL35Extract, NL35Data
from validation.checks import (
    _check_policy_count_non_negative,
    _check_premium_non_negative,
    _check_cy_ytd_ge_cy_qtr,
    _check_py_ytd_ge_py_qtr,
    _check_completeness,
    _check_cross_period_consistency,
    run_validations,
    ValidationResult,
    write_validation_report,
)


def _exc(quarter="Q3"):
    return NL35Extract(
        source_file="test.pdf",
        company_key="bajaj_allianz",
        company_name="Bajaj Allianz General Insurance Company Limited",
        form_type="NL35",
        quarter=quarter,
        year="202526",
    )


# ---------------------------------------------------------------------------
# Policy count non-negative
# ---------------------------------------------------------------------------

def test_policy_non_negative_pass():
    exc = _exc()
    lob_data = {"cy_qtr_policies": 703285.0}
    results = _check_policy_count_non_negative(exc, "fire", lob_data)
    assert all(r.status == "PASS" for r in results)


def test_policy_non_negative_fail():
    exc = _exc()
    lob_data = {"cy_qtr_policies": -1.0}
    results = _check_policy_count_non_negative(exc, "fire", lob_data)
    assert any(r.status == "FAIL" for r in results)


def test_policy_non_negative_skip_when_none():
    exc = _exc()
    lob_data = {}
    results = _check_policy_count_non_negative(exc, "fire", lob_data)
    assert results == []


# ---------------------------------------------------------------------------
# Premium non-negative (warn on negative)
# ---------------------------------------------------------------------------

def test_premium_non_negative_pass():
    exc = _exc()
    lob_data = {"cy_qtr_premium": 53116.14}
    results = _check_premium_non_negative(exc, "fire", lob_data)
    assert any(r.status == "PASS" for r in results)


def test_premium_negative_warn():
    exc = _exc()
    lob_data = {"cy_qtr_premium": -100.0}
    results = _check_premium_non_negative(exc, "fire", lob_data)
    assert any(r.status == "WARN" for r in results)
    assert not any(r.status == "FAIL" for r in results)


# ---------------------------------------------------------------------------
# CY YTD >= CY Qtr
# ---------------------------------------------------------------------------

def test_cy_ytd_ge_cy_qtr_pass_q3():
    exc = _exc("Q3")
    lob_data = {"cy_qtr_premium": 53116.14, "cy_ytd_premium": 227419.19}
    r = _check_cy_ytd_ge_cy_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "PASS"


def test_cy_ytd_ge_cy_qtr_fail_q3():
    exc = _exc("Q3")
    lob_data = {"cy_qtr_premium": 100.0, "cy_ytd_premium": 50.0}
    r = _check_cy_ytd_ge_cy_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "FAIL"


def test_cy_ytd_eq_cy_qtr_q1_pass():
    exc = _exc("Q1")
    lob_data = {"cy_qtr_premium": 100.0, "cy_ytd_premium": 100.0}
    r = _check_cy_ytd_ge_cy_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "PASS"


def test_cy_ytd_ne_cy_qtr_q1_fail():
    exc = _exc("Q1")
    lob_data = {"cy_qtr_premium": 100.0, "cy_ytd_premium": 200.0}
    r = _check_cy_ytd_ge_cy_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "FAIL"


def test_cy_ytd_missing_returns_none():
    exc = _exc("Q3")
    lob_data = {"cy_qtr_premium": 100.0}
    r = _check_cy_ytd_ge_cy_qtr(exc, "fire", lob_data)
    assert r is None


# ---------------------------------------------------------------------------
# PY YTD >= PY Qtr
# ---------------------------------------------------------------------------

def test_py_ytd_ge_py_qtr_pass():
    exc = _exc("Q3")
    lob_data = {"py_qtr_premium": 50053.40, "py_ytd_premium": 199355.36}
    r = _check_py_ytd_ge_py_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "PASS"


def test_py_ytd_ge_py_qtr_fail():
    exc = _exc("Q3")
    lob_data = {"py_qtr_premium": 200.0, "py_ytd_premium": 100.0}
    r = _check_py_ytd_ge_py_qtr(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "FAIL"


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------

def test_completeness_mandatory_lob_missing_fail():
    exc = _exc()
    # No data at all
    results = _check_completeness(exc)
    fail_lobs = {r.lob for r in results if r.status == "FAIL"}
    assert "fire" in fail_lobs
    assert "motor_od" in fail_lobs
    assert "motor_tp" in fail_lobs
    assert "health" in fail_lobs


def test_completeness_optional_lob_missing_warn():
    exc = _exc()
    results = _check_completeness(exc)
    warn_lobs = {r.lob for r in results if r.status == "WARN"}
    # Non-mandatory LOBs should be WARN
    assert "aviation" in warn_lobs or "credit_insurance" in warn_lobs


def test_completeness_pass_when_present():
    exc = _exc()
    exc.data.data["fire"] = {"cy_qtr_premium": 53116.14}
    results = _check_completeness(exc)
    fire_results = [r for r in results if r.lob == "fire" and r.check_name == "COMPLETENESS"]
    assert len(fire_results) == 0


# ---------------------------------------------------------------------------
# Cross-period consistency
# ---------------------------------------------------------------------------

def test_cross_period_ratio_normal_pass():
    exc = _exc()
    lob_data = {"cy_qtr_premium": 53116.14, "py_qtr_premium": 50053.40}
    r = _check_cross_period_consistency(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "PASS"


def test_cross_period_ratio_extreme_warn():
    exc = _exc()
    lob_data = {"cy_qtr_premium": 1000000.0, "py_qtr_premium": 10.0}
    r = _check_cross_period_consistency(exc, "fire", lob_data)
    assert r is not None
    assert r.status == "WARN"


def test_cross_period_missing_returns_none():
    exc = _exc()
    lob_data = {"cy_qtr_premium": 100.0}
    r = _check_cross_period_consistency(exc, "fire", lob_data)
    assert r is None


# ---------------------------------------------------------------------------
# run_validations smoke test
# ---------------------------------------------------------------------------

def test_run_validations_smoke():
    exc = _exc()
    exc.data.data["fire"] = {
        "cy_qtr_premium": 53116.14,
        "cy_qtr_policies": 703285.0,
        "py_qtr_premium": 50053.40,
        "py_qtr_policies": 629160.0,
        "cy_ytd_premium": 227419.19,
        "cy_ytd_policies": 2030317.0,
        "py_ytd_premium": 199355.36,
        "py_ytd_policies": 1961031.0,
    }
    results = run_validations([exc])
    assert len(results) > 0
    pass_results = [r for r in results if r.status == "PASS"]
    assert len(pass_results) > 0


# ---------------------------------------------------------------------------
# write_validation_report
# ---------------------------------------------------------------------------

def test_write_validation_report(tmp_path):
    res = [ValidationResult(
        "Bajaj", "Q3", "202526", "fire",
        "TEST", "PASS", 100.0, 100.0, 0.0, ""
    )]
    output = tmp_path / "report.csv"
    write_validation_report(res, str(output))
    assert os.path.exists(output)
