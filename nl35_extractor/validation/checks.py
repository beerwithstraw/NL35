"""
Validation Checks for NL-6 Commission Schedule.

Three identity checks:
  1. GROSS_COMMISSION_IDENTITY  — Gross = Commission_Remuneration + Rewards + Distribution_Fees
  2. NET_COMMISSION_IDENTITY    — Net  = Gross + RI_Accepted_Commission + RI_Ceded_Commission
  3. CHANNEL_TOTAL_IDENTITY     — Total_Channel = sum of all individual channel rows

Plus segment-sum and completeness checks (unchanged logic from NL-5).
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from extractor.models import CompanyExtract, PeriodData
from config.company_registry import COMPANY_SPECIFIC_LOBS
from config.lob_registry import LOB_ORDER, COMPLETENESS_IGNORE
from config.row_registry import ROW_ORDER

logger = logging.getLogger(__name__)

# Inverted lookup: LOB → set of companies that have it.
_COMPANY_ONLY_LOBS: Dict[str, set] = {}
for _ck, _lobs in COMPANY_SPECIFIC_LOBS.items():
    for _lob in _lobs:
        _COMPANY_ONLY_LOBS.setdefault(_lob, set()).add(_ck)

TOLERANCE = 1.0
IDENTITY_TOLERANCE = 3.0

# All individual channel rows (everything in total_channel except total_channel itself)
_CHANNEL_ROWS = [
    "agent",
    "broker",
    "corporate_agent_bank",
    "corporate_agent_other",
    "misp_direct",
    "misp_dealership",
    "web_aggregator",
    "insurance_marketing_firm",
    "common_service_centre",
    "point_of_sales",
    "direct_selling",
    "micro_agent",
    "other_channels",
]


@dataclass
class ValidationResult:
    company: str
    quarter: str
    year: str
    lob: str
    period: str       # e.g. "current_qtr", "prior_ytd"
    check_name: str
    status: str       # PASS, WARN, FAIL
    expected: Optional[float]
    actual: Optional[float]
    delta: Optional[float]
    note: str


def run_validations(extractions: List[CompanyExtract]) -> List[ValidationResult]:
    """Runs all NL-6 validation checks against the provided extractions."""
    results = []

    for exc in extractions:
        for period_label, period_data in [("current", exc.current_year), ("prior", exc.prior_year)]:
            if not period_data:
                continue

            for timewise in ["qtr", "ytd"]:
                p_id = f"{period_label}_{timewise}"

                for lob in period_data.data:
                    lob_data = period_data.data[lob]
                    r1 = _check_gross_commission_identity(exc, lob, p_id, lob_data, timewise)
                    r2 = _check_net_commission_identity(exc, lob, p_id, lob_data, timewise)
                    r3 = _check_channel_total_identity(exc, lob, p_id, lob_data, timewise)
                    for r in (r1, r2, r3):
                        if r is not None:
                            results.append(r)

                results.append(_check_segment_sum(
                    exc, "total_marine", ["marine_cargo", "marine_hull"],
                    p_id, period_data, timewise,
                ))
                results.append(_check_segment_sum(
                    exc, "total_motor", ["motor_od", "motor_tp"],
                    p_id, period_data, timewise,
                ))
                results.append(_check_segment_sum(
                    exc, "total_health", ["health", "personal_accident", "travel_insurance"],
                    p_id, period_data, timewise,
                ))

            results.extend(_check_completeness_refined(exc, period_label, period_data))

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_val(data: Dict, row: str, p_key: str) -> Optional[float]:
    v = data.get(row, {}).get(p_key)
    return float(v) if v is not None else None


def _make_result(exc, lob, pid, check_name, status, expected, actual, delta, note=""):
    return ValidationResult(
        exc.company_name, exc.quarter, exc.year, lob, pid,
        check_name, status, expected, actual, delta, note,
    )


# ---------------------------------------------------------------------------
# Identity check 1: Gross Commission
# Gross = Commission_Remuneration + Rewards + Distribution_Fees
# ---------------------------------------------------------------------------
def _check_gross_commission_identity(
    exc: CompanyExtract, lob: str, pid: str, lob_data: Dict, p_key: str
) -> Optional[ValidationResult]:
    gross = _get_val(lob_data, "gross_commission", p_key)
    cr    = _get_val(lob_data, "commission_remuneration", p_key)
    rew   = _get_val(lob_data, "rewards", p_key)
    dist  = _get_val(lob_data, "distribution_fees", p_key)

    # Need at least gross and one component
    if gross is None or all(v is None for v in (cr, rew, dist)):
        return None

    expected = (cr or 0.0) + (rew or 0.0) + (dist or 0.0)
    delta = abs(gross - expected)
    status = "PASS" if delta <= IDENTITY_TOLERANCE else "FAIL"
    return _make_result(exc, lob, pid, "GROSS_COMMISSION_IDENTITY", status, expected, gross, delta)


# ---------------------------------------------------------------------------
# Identity check 2: Net Commission
# Net = Gross + RI_Accepted_Commission - RI_Ceded_Commission
# (RI_Ceded stored as positive as extracted from PDF — subtracted here)
# ---------------------------------------------------------------------------
def _check_net_commission_identity(
    exc: CompanyExtract, lob: str, pid: str, lob_data: Dict, p_key: str
) -> Optional[ValidationResult]:
    net   = _get_val(lob_data, "net_commission", p_key)
    gross = _get_val(lob_data, "gross_commission", p_key)
    acc   = _get_val(lob_data, "ri_accepted_commission", p_key)
    ced   = _get_val(lob_data, "ri_ceded_commission", p_key)

    if any(v is None for v in (net, gross)):
        return None

    acc_eff = acc if acc is not None else 0.0
    ced_eff = ced if ced is not None else 0.0

    # RI Ceded sign convention varies by company:
    #   Most PDFs: ced stored positive → Net = Gross + Acc - Ced
    #   Some PDFs (e.g. Bajaj, HDFC ERGO): ced stored negative → Net = Gross + Acc + Ced
    # Try both; pass if either is within tolerance.
    delta_sub = abs(net - (gross + acc_eff - ced_eff))
    delta_add = abs(net - (gross + acc_eff + ced_eff))
    delta = min(delta_sub, delta_add)
    expected = (gross + acc_eff - ced_eff) if delta_sub <= delta_add else (gross + acc_eff + ced_eff)
    status = "PASS" if delta <= IDENTITY_TOLERANCE else "FAIL"
    return _make_result(exc, lob, pid, "NET_COMMISSION_IDENTITY", status, expected, net, delta)


# ---------------------------------------------------------------------------
# Identity check 3: Channel total
# Total_Channel = sum of all individual channel rows (those present)
# ---------------------------------------------------------------------------
def _check_channel_total_identity(
    exc: CompanyExtract, lob: str, pid: str, lob_data: Dict, p_key: str
) -> Optional[ValidationResult]:
    total = _get_val(lob_data, "total_channel", p_key)
    if total is None:
        return None

    component_sum = 0.0
    n_found = 0
    for row in _CHANNEL_ROWS:
        v = _get_val(lob_data, row, p_key)
        if v is not None:
            component_sum += v
            n_found += 1

    if n_found == 0:
        return None

    delta = abs(total - component_sum)
    status = "PASS" if delta <= IDENTITY_TOLERANCE else "FAIL"
    return _make_result(exc, lob, pid, "CHANNEL_TOTAL_IDENTITY", status, component_sum, total, delta)


# ---------------------------------------------------------------------------
# Segment sum (LOB sub-total check) — reuses gross_commission as anchor
# ---------------------------------------------------------------------------
def _check_segment_sum(
    exc: CompanyExtract,
    total_lob: str,
    components: List[str],
    pid: str,
    period_data: PeriodData,
    p_key: str,
) -> Optional[ValidationResult]:
    metric = "gross_commission"
    actual_val = _get_val(period_data.data.get(total_lob, {}), metric, p_key)
    if actual_val is None:
        return None

    expected = 0.0
    valid_count = 0
    for cl in components:
        val = _get_val(period_data.data.get(cl, {}), metric, p_key)
        if val is not None:
            expected += val
            valid_count += 1

    if valid_count == 0:
        return None

    delta = abs(actual_val - expected)
    status = "PASS" if delta <= IDENTITY_TOLERANCE else "FAIL"
    return ValidationResult(
        exc.company_name, exc.quarter, exc.year, total_lob, pid,
        f"SEGMENT_SUM_{metric.upper()}", status, expected, actual_val, delta, "",
    )


# ---------------------------------------------------------------------------
# Completeness check — unchanged logic
# ---------------------------------------------------------------------------
def _check_completeness_refined(
    exc: CompanyExtract, period_label: str, period_data: PeriodData
) -> List[ValidationResult]:
    results = []
    MANDATORY_LOBS = {"fire", "grand_total", "total_motor", "total_health"}
    ignore_lobs = set(COMPLETENESS_IGNORE.get(exc.company_key, []))

    for lob in LOB_ORDER:
        if lob in ignore_lobs:
            continue
        if lob in _COMPANY_ONLY_LOBS and exc.company_key not in _COMPANY_ONLY_LOBS[lob]:
            continue

        lob_data = period_data.data.get(lob, {})
        has_any_data = any(
            any(v is not None for v in r.values())
            for r in lob_data.values()
        )

        if not has_any_data:
            status = "FAIL" if lob in MANDATORY_LOBS and lob not in ignore_lobs else "WARN"
            results.append(ValidationResult(
                exc.company_name, exc.quarter, exc.year, lob, period_label,
                "COMPLETENESS", status, None, None, None, f"LOB {lob} is missing",
            ))

    return results


# ---------------------------------------------------------------------------
# Reporting helpers (unchanged)
# ---------------------------------------------------------------------------

def build_validation_summary_table(results: List["ValidationResult"]):
    """Build a Rich Table summarising PASS/SKIP/WARN/FAIL counts."""
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
    """Writes the results to a CSV file."""
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "quarter", "year", "lob", "period",
            "check_name", "status", "expected", "actual", "delta", "note",
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    logger.info(f"Validation report saved to {output_path}")
