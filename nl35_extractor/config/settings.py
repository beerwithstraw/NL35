"""
Global constants, tolerances, and configuration for the NL35 Extractor.
"""

# --- Versioning ---
EXTRACTOR_VERSION = "1.0.0"

# --- Tolerances ---
# Collector snap/join tolerance (pixels)
COLLECTOR_SNAP_TOLERANCE_LINES = 4
COLLECTOR_SNAP_TOLERANCE_TEXT = 3

# --- Default Paths ---
DEFAULT_INPUT_DIR = "inputs"
DEFAULT_OUTPUT_DIR = "outputs"

# --- FY Year String Helper ---

def make_fy_string(start_year: int, end_year: int) -> str:
    """
    Build the 6-character FY string.
    e.g. start=2025, end=2026 → '202526'
    """
    return f"{start_year}{end_year % 100:02d}"


QUARTER_TO_FY = {
    "Q1": lambda y: make_fy_string(y, y + 1),
    "Q2": lambda y: make_fy_string(y, y + 1),
    "Q3": lambda y: make_fy_string(y, y + 1),
    "Q4": lambda y: make_fy_string(y - 1, y),
}

# --- Master Sheet Column Order (fixed — do not reorder) ---
# NL35: one row per company per LOB per (Year_Info × Quarter_Info) combination.
# Each original LOB expands into 4 rows: CY/PY × For Quarter/Upto Quarter.
MASTER_COLUMNS = [
    "LOB_PARTICULARS",           # A
    "Grouped_LOB",               # B
    "Company_Name",              # C
    "Company",                   # D
    "NL",                        # E
    "Quarter",                   # F
    "Year",                      # G
    "Year_Info",                 # H  — "Current Year" or "Previous Year"
    "Quarter_Info",              # I  — "For the Quarter" or "Upto the Quarter"
    "Sector",                    # J
    "Industry_Competitors",      # K
    "GI_Companies",              # L
    "No_of_Policies",            # M
    "Premium",                   # N
    "Source_File",               # O
]

# Canonical period-metric keys (internal snake_case)
PERIOD_METRIC_KEYS = [
    "cy_qtr_premium",
    "cy_qtr_policies",
    "py_qtr_premium",
    "py_qtr_policies",
    "cy_ytd_premium",
    "cy_ytd_policies",
    "py_ytd_premium",
    "py_ytd_policies",
]

# Mapping from (Year_Info, Quarter_Info) → (premium_key, policies_key)
PERIOD_ROW_MAP = [
    ("Current Year",  "For the Quarter",    "cy_qtr_premium",  "cy_qtr_policies"),
    ("Current Year",  "Upto the Quarter",   "cy_ytd_premium",  "cy_ytd_policies"),
    ("Previous Year", "For the Quarter",    "py_qtr_premium",  "py_qtr_policies"),
    ("Previous Year", "Upto the Quarter",   "py_ytd_premium",  "py_ytd_policies"),
]

# --- Excel Formatting ---
NUMBER_FORMAT = "#,##0.00"
INTEGER_FORMAT = "#,##0"
LOW_CONFIDENCE_FILL_COLOR = "FFFF99"
ALTERNATING_ROW_FILL = "F2F2F2"


def company_key_to_pascal(company_key: str) -> str:
    return company_key.replace("_", " ").title().replace(" ", "")
