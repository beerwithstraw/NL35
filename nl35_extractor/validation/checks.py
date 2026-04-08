"""
Validation Checks for NL-35 Quarterly Business Returns.

Checks:
  1. POLICY_COUNT_NON_NEGATIVE   — No. of Policies >= 0 for all LOBs/periods
  2. PREMIUM_NON_NEGATIVE        — Premium >= 0 (warn on negative)
  3. CY_YTD_GE_CY_QTR           — CY YTD >= CY Qtr for Q2, Q3, Q4; equal for Q1
  4. PY_YTD_GE_PY_QTR           — PY YTD >= PY Qtr
  5. COMPLETENESS                — Mandatory LOBs must have CY_Qtr_Premium
  6. CROSS_PERIOD_CONSISTENCY    — CY Qtr vs PY Qtr ratio sanity
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict

from extractor.models import NL35Extract
from config.row_registry import NL35_LOB_ORDER
from config.company_registry import COMPLETENESS_IGNORE

logger = logging.getLogger(__name__)

TOLERANCE = 1.0
CROSS_PERIOD_RATIO_MAX = 10.0

MANDATORY_LOBS = {"fire", "motor_od", "motor_tp", "health"}


@dataclass
class ValidationResult:
    company: str
    quarter: str
    year: str
    lob: str
    check_name: str
    status: str       # PASS, WARN, FAIL
    expected: Optional[float]
    actual: Optional[float]
    delta: Optional[float]
    note: str


def run_validations(extractions: List[NL35Extract]) -> List[ValidationResult]:
    results = []
    for exc in extractions:
        for lob in NL35_LOB_ORDER:
            lob_data = exc.data.data.get(lob, {})
            results.extend(_check_policy_count_non_negative(exc, lob, lob_data))
            results.extend(_check_premium_non_negative(exc, lob, lob_data))
            r = _check_cy_ytd_ge_cy_qtr(exc, lob, lob_data)
            if r:
                results.append(r)
            r = _check_py_ytd_ge_py_qtr(exc, lob, lob_data)
            if r:
                results.append(r)
            r = _check_cross_period_consistency(exc, lob, lob_data)
            if r:
                results.append(r)
        results.extend(_check_completeness(exc))
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make(exc, lob, check_name, status, expected, actual, delta, note=""):
    return ValidationResult(
        exc.company_name, exc.quarter, exc.year,
        lob, check_name, status, expected, actual, delta, note,
    )


def _get(lob_data, key):
    v = lob_data.get(key)
    return float(v) if v is not None else None


# ---------------------------------------------------------------------------
# Check 1: Policy count >= 0
# ---------------------------------------------------------------------------

def _check_policy_count_non_negative(exc, lob, lob_data) -> List[ValidationResult]:
    results = []
    for key in ("cy_qtr_policies", "py_qtr_policies", "cy_ytd_policies", "py_ytd_policies"):
        v = _get(lob_data, key)
        if v is None:
            continue
        if v < 0:
            results.append(_make(exc, lob, "POLICY_COUNT_NON_NEGATIVE", "FAIL",
                                  0.0, v, abs(v), f"{key} is negative"))
        else:
            results.append(_make(exc, lob, "POLICY_COUNT_NON_NEGATIVE", "PASS",
                                  0.0, v, 0.0))
    return results


# ---------------------------------------------------------------------------
# Check 2: Premium >= 0 (warn on negative, not fail — reversals are valid)
# ---------------------------------------------------------------------------

def _check_premium_non_negative(exc, lob, lob_data) -> List[ValidationResult]:
    results = []
    for key in ("cy_qtr_premium", "py_qtr_premium", "cy_ytd_premium", "py_ytd_premium"):
        v = _get(lob_data, key)
        if v is None:
            continue
        if v < 0:
            results.append(_make(exc, lob, "PREMIUM_NON_NEGATIVE", "WARN",
                                  0.0, v, abs(v), f"{key} is negative (possible reversal)"))
        else:
            results.append(_make(exc, lob, "PREMIUM_NON_NEGATIVE", "PASS",
                                  0.0, v, 0.0))
    return results


# ---------------------------------------------------------------------------
# Check 3: CY YTD >= CY Qtr
# ---------------------------------------------------------------------------

def _check_cy_ytd_ge_cy_qtr(exc, lob, lob_data) -> Optional[ValidationResult]:
    qtr = _get(lob_data, "cy_qtr_premium")
    ytd = _get(lob_data, "cy_ytd_premium")
    if qtr is None or ytd is None:
        return None
    if exc.quarter == "Q1":
        # YTD == Qtr for Q1
        delta = abs(ytd - qtr)
        status = "PASS" if delta <= TOLERANCE else "FAIL"
        return _make(exc, lob, "CY_YTD_GE_CY_QTR", status, qtr, ytd, delta,
                      "Q1: YTD should equal Qtr")
    else:
        if ytd >= qtr - TOLERANCE:
            return _make(exc, lob, "CY_YTD_GE_CY_QTR", "PASS", qtr, ytd, ytd - qtr)
        else:
            return _make(exc, lob, "CY_YTD_GE_CY_QTR", "FAIL", qtr, ytd, qtr - ytd,
                          "YTD < Qtr")


# ---------------------------------------------------------------------------
# Check 4: PY YTD >= PY Qtr
# ---------------------------------------------------------------------------

def _check_py_ytd_ge_py_qtr(exc, lob, lob_data) -> Optional[ValidationResult]:
    qtr = _get(lob_data, "py_qtr_premium")
    ytd = _get(lob_data, "py_ytd_premium")
    if qtr is None or ytd is None:
        return None
    if exc.quarter == "Q1":
        delta = abs(ytd - qtr)
        status = "PASS" if delta <= TOLERANCE else "FAIL"
        return _make(exc, lob, "PY_YTD_GE_PY_QTR", status, qtr, ytd, delta,
                      "Q1: YTD should equal Qtr")
    else:
        if ytd >= qtr - TOLERANCE:
            return _make(exc, lob, "PY_YTD_GE_PY_QTR", "PASS", qtr, ytd, ytd - qtr)
        else:
            return _make(exc, lob, "PY_YTD_GE_PY_QTR", "FAIL", qtr, ytd, qtr - ytd,
                          "YTD < Qtr")


# ---------------------------------------------------------------------------
# Check 5: Completeness
# ---------------------------------------------------------------------------

def _check_completeness(exc) -> List[ValidationResult]:
    results = []
    ignore_lobs = set(COMPLETENESS_IGNORE.get(exc.company_key, []))

    for lob in NL35_LOB_ORDER:
        if lob in ignore_lobs:
            continue
        v = _get(exc.data.data.get(lob, {}), "cy_qtr_premium")
        if v is None:
            status = "FAIL" if lob in MANDATORY_LOBS else "WARN"
            results.append(_make(exc, lob, "COMPLETENESS", status,
                                  None, None, None, f"LOB {lob} CY_Qtr_Premium is missing"))

    return results


# ---------------------------------------------------------------------------
# Check 6: Cross-period consistency
# ---------------------------------------------------------------------------

def _check_cross_period_consistency(exc, lob, lob_data) -> Optional[ValidationResult]:
    cy = _get(lob_data, "cy_qtr_premium")
    py = _get(lob_data, "py_qtr_premium")
    if cy is None or py is None or py == 0:
        return None
    if cy == 0:
        return None
    ratio = cy / py if py > 0 else None
    if ratio is None:
        return None
    if ratio > CROSS_PERIOD_RATIO_MAX or ratio < (1.0 / CROSS_PERIOD_RATIO_MAX):
        return _make(exc, lob, "CROSS_PERIOD_CONSISTENCY", "WARN",
                      py, cy, abs(cy - py),
                      f"CY/PY ratio {ratio:.2f} outside plausible range")
    return _make(exc, lob, "CROSS_PERIOD_CONSISTENCY", "PASS",
                  py, cy, abs(cy - py))


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def build_validation_summary_table(results: List[ValidationResult]):
    from rich.table import Table
    counts = {"PASS": 0, "SKIP": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    t = Table(title="Validation Summary")
    t.add_column("Status", style="bold")
    t.add_column("Count", justify="right")
    t.add_row("[green]PASS[/green]", str(counts["PASS"]))
    t.add_row("[blue]SKIP[/blue]", str(counts["SKIP"]))
    t.add_row("[yellow]WARN[/yellow]", str(counts["WARN"]))
    t.add_row("[red]FAIL[/red]", str(counts["FAIL"]))
    return t


def write_validation_report(results: List[ValidationResult], output_path: str):
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "quarter", "year", "lob",
            "check_name", "status", "expected", "actual", "delta", "note",
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    logger.info(f"Validation report saved to {output_path}")
