"""
Re-aggregation Script for NL4 Batch Premium Extractor.

Rebuilds the Master_Data sheet from individual company sheets in the Excel workbook.
Useful after manual corrections are made in the verification sheets.

Source: approach document Section 13
"""

import sys
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
import openpyxl
from rich.console import Console

# Add current directory to path so we can import internal modules
sys.path.insert(0, str(Path(__file__).parent))

from extractor.models import CompanyExtract, PeriodData
from config.lob_registry import LOB_ORDER, LOB_DISPLAY_NAMES
from config.row_registry import ROW_ORDER, ROW_DISPLAY_NAMES
from config.settings import DEFAULT_OUTPUT_DIR, MASTER_COLUMNS
from validation.checks import run_validations, write_validation_report, build_validation_summary_table
from output.excel_writer import save_workbook

console = Console()
logger = logging.getLogger(__name__)

def parse_sheet_to_extract(ws) -> Optional[CompanyExtract]:
    """Parses a company verification sheet back into a CompanyExtract object."""
    try:
        # 1. Metadata from Row 2
        meta_cell = ws.cell(row=2, column=1).value
        # Expecting: "Quarter: Q1 | Year: 202526 | Source: NL4_Q1_202526_BajajAllianz.pdf"
        if not meta_cell or "Quarter:" not in meta_cell:
            return None
            
        parts = {p.split(":")[0].strip(): p.split(":")[1].strip() for p in meta_cell.split("|")}
        quarter = parts.get("Quarter", "Qx")
        year = parts.get("Year", "xxxxxx")
        source_file = parts.get("Source", "Unknown.pdf")
        
        # Company name/key from Row 1
        title = ws.cell(row=1, column=1).value
        # "VERIFICATION SHEET: Bajaj Allianz General Insurance"
        company_name = title.replace("VERIFICATION SHEET:", "").strip()
        
        # We need to map company_name back to company_key.
        # For now, let's assume sheet name format: PascalCaseKey_Qx_Year
        # Or we can look it up from config.
        from config.company_registry import COMPANY_DISPLAY_NAMES
        company_key = "unknown"
        for k, v in COMPANY_DISPLAY_NAMES.items():
            if v == company_name:
                company_key = k
                break
        
        extract = CompanyExtract(
            source_file=source_file,
            company_key=company_key,
            company_name=company_name,
            form_type="NL4",
            quarter=quarter,
            year=year
        )
        
        # 2. Parse Tables
        extract.current_year = _parse_grid(ws, start_row=4, period_label="current")
        
        # Find start of Prior Year table (usually row 20ish, but let's search)
        py_start = 20
        for r in range(15, 40):
            if ws.cell(row=r, column=1).value == "TABLE 2: Prior Year Data":
                py_start = r
                break
        
        extract.prior_year = _parse_grid(ws, start_row=py_start, period_label="prior")
        
        return extract
    except Exception as e:
        logger.error(f"Failed to parse sheet {ws.title}: {e}")
        return None

def _parse_grid(ws, start_row: int, period_label: str) -> Optional[PeriodData]:
    """Parses a single table grid (LOBs vs Rows)."""
    title = ws.cell(row=start_row, column=1).value
    if not title or "Data Not Found" in str(title):
        return None
        
    period_data = PeriodData(period_label=period_label)
    
    # Header rows: LOBs (start_row + 1), Qtr/YTD (start_row + 2)
    lob_row = start_row + 1
    
    # 1. Identify LOBs and their columns
    lob_to_cols = {}
    col = 2
    none_count = 0
    prev_lob = None

    while True:
        lob_name = ws.cell(row=lob_row, column=col).value
        
        if lob_name:
            none_count = 0
            # Map display name back to lob_key
            lob_key = None
            for k, v in LOB_DISPLAY_NAMES.items():
                if v == lob_name:
                    lob_key = k
                    break
            
            if lob_key:
                lob_to_cols[lob_key] = (col, col + 1)
                prev_lob = lob_key
        else:
            none_count += 1
            # Rule: if it's the first None after a valid header, it's just a merged spacer.
            # Terminate only on two consecutive Nones.
            if none_count >= 2:
                break
            
        col += 2
        
    # 2. Read row values
    data_start_row = start_row + 3
    for i, row_key in enumerate(ROW_ORDER):
        row_idx = data_start_row + i
        for lob_key, (col_q, col_y) in lob_to_cols.items():
            val_q = ws.cell(row=row_idx, column=col_q).value
            val_y = ws.cell(row=row_idx, column=col_y).value
            
            if lob_key not in period_data.data:
                period_data.data[lob_key] = {}
            
            try:
                fq = float(val_q) if val_q is not None else None
            except (ValueError, TypeError):
                fq = None
            try:
                fy = float(val_y) if val_y is not None else None
            except (ValueError, TypeError):
                fy = None
            period_data.data[lob_key][row_key] = {"qtr": fq, "ytd": fy}
            
    return period_data

@click.command()
@click.option("--workbook", "-w", required=True, help="Path to the Excel master workbook", type=click.Path(exists=True))
@click.option("--backup/--no-backup", default=True, help="Create a timestamped backup before overwriting")
def reaggregate(workbook, backup):
    """
    Rebuild Master_Data sheet from individual company sheets.
    """
    console.print(f"[bold blue]Re-aggregating workbook:[/bold blue] {workbook}")
    
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(workbook).with_name(f"{Path(workbook).stem}_backup_{timestamp}.xlsx")
        shutil.copy2(workbook, backup_path)
        console.print(f"[dim]Backup created: {backup_path.name}[/dim]")
        
    try:
        wb = openpyxl.load_workbook(workbook)
        extractions = []
        
        for sheet_name in wb.sheetnames:
            if sheet_name in ["Master_Data", "_meta"]:
                continue
            
            ws = wb[sheet_name]
            extract = parse_sheet_to_extract(ws)
            if extract:
                extractions.append(extract)
                console.print(f"  [green]\u2713[/green] Parsed {sheet_name}")
            else:
                console.print(f"  [red]\u2717[/red] Skipped {sheet_name} (unrecognised structure)")
                
        if not extractions:
            console.print("[bold red]No valid company sheets found to re-aggregate.[/bold red]")
            return
            
        # Re-run validations
        console.print(f"\n[bold blue]Running validation checks on {len(extractions)} companies...[/bold blue]")
        val_results = run_validations(extractions)
        report_path = Path(workbook).parent / "validation_report_reagg.csv"
        write_validation_report(val_results, str(report_path))
        
        # Save updated workbook
        save_workbook(extractions, workbook, stats={"files_processed": len(extractions), "files_succeeded": len(extractions)})
        
        console.print(f"\n[bold green]Re-aggregation successful![/bold green]")
        console.print(f"Master_Data sheet rebuilt.")
        console.print(f"Validation report: [bold]{report_path.name}[/bold]\n")

        console.print(build_validation_summary_table(val_results))
        
    except Exception as e:
        console.print(f"[bold red]Critical error during re-aggregation:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    reaggregate()
