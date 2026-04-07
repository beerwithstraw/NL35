"""
Data models for NL-35 Quarterly Business Returns extraction.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class NL35Data:
    """
    Holds extracted NL-35 data for one company.

    data[lob_key][period_metric_key] = float | None
    e.g. data["fire"]["cy_qtr_premium"] = 53116.14
         data["fire"]["cy_qtr_policies"] = 703285.0

    period_metric_key is one of:
        cy_qtr_premium, cy_qtr_policies,
        py_qtr_premium, py_qtr_policies,
        cy_ytd_premium, cy_ytd_policies,
        py_ytd_premium, py_ytd_policies
    """
    data: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)


@dataclass
class NL35Extract:
    """Top-level container for one extracted NL-35 PDF."""
    source_file: str
    company_key: str                # e.g. "bajaj_allianz"
    company_name: str               # e.g. "Bajaj Allianz General Insurance"
    form_type: str = "NL35"
    quarter: str = ""               # e.g. "Q3"
    year: str = ""                  # e.g. "202526"
    data: NL35Data = field(default_factory=NL35Data)
    extraction_warnings: list = field(default_factory=list)
    extraction_errors: list = field(default_factory=list)
