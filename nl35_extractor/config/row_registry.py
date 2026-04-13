"""
Row (LOB) Registry for NL-35 Quarterly Business Returns.

In NL-35, LOBs are the rows (not the columns). This module defines the
canonical LOB keys, their display names, alias strings, and skip patterns.
"""

import re

# Canonical LOB keys — ordered for output (matches NL-35 row order in PDFs).
NL35_LOB_ORDER = [
    "fire",
    "marine_cargo",
    "marine_hull",
    "motor_od",
    "motor_tp",
    "health",
    "personal_accident",
    "travel_insurance",
    "total_health",           # sub-total: health + PA + travel (present in most PDFs)
    "wc_el",
    "public_product_liability",
    "engineering",
    "aviation",
    "crop_insurance",
    "credit_insurance",
    "other_miscellaneous",
]

# Display-friendly names (as they appear in NL-35 PDFs)
NL35_LOB_DISPLAY_NAMES = {
    "fire":                     "Fire",
    "marine_cargo":             "Marine Cargo",
    "marine_hull":              "Marine Other than Cargo",
    "motor_od":                 "Motor OD",
    "motor_tp":                 "Motor TP",
    "health":                   "Health",
    "personal_accident":        "Personal Accident",
    "travel_insurance":         "Travel",
    "total_health":             "Total Health",
    "wc_el":                    "Workmen's Compensation/ Employer's liability",
    "public_product_liability": "Public/ Product Liability",
    "engineering":              "Engineering",
    "aviation":                 "Aviation",
    "crop_insurance":           "Crop Insurance",
    "credit_insurance":         "Credit Insurance",
    "other_miscellaneous":      "Other Miscellaneous Segments",
}

# All observed PDF label strings → canonical LOB key
# Keys are normalised (lowercase, stripped). See normalise_text() in normaliser.py.
NL35_LOB_ALIASES = {
    # --- Fire ---
    "fire":                                                  "fire",

    # --- Marine ---
    "marine cargo":                                          "marine_cargo",
    "marine other than cargo":                               "marine_hull",
    "marine hull":                                           "marine_hull",
    "marine other":                                          "marine_hull",      # NIC truncated

    # --- Motor ---
    "motor od":                                              "motor_od",
    "motor (od)":                                            "motor_od",
    "motor owner damage":                                    "motor_od",
    "motor own damage":                                      "motor_od",
    "motor tp":                                              "motor_tp",
    "motor (tp)":                                            "motor_tp",
    "motor third party":                                     "motor_tp",
    "motortp":                                               "motor_tp",         # Navi (no space)

    # --- Health / PA / Travel ---
    "health":                                                "health",
    "health insurance":                                      "health",
    "personal accident":                                     "personal_accident",
    "personal":                                              "personal_accident", # NIC truncated
    "travel":                                                "travel_insurance",
    "travel insurance":                                      "travel_insurance",

    # --- Total Health ---
    "total health":                                          "total_health",
    "total health segment":                                  "total_health",
    "health segment":                                        "total_health",
    "total health / total miscellaneous":                    "total_health",
    "total health/total miscellaneous":                      "total_health",

    # --- WC/EL ---
    "workmen's compensation/ employer's liability":          "wc_el",
    "workmen\u2019s compensation/ employer\u2019s liability": "wc_el",
    "workmen's compensation/employer's liability":           "wc_el",
    "workmen's compensation":                                "wc_el",            # HDFC Ergo (straight)
    "workmen\u2019s compensation":                           "wc_el",            # HDFC Ergo (curly)
    "workmen compensation":                                  "wc_el",
    "wc/el":                                                 "wc_el",
    "workers compensation":                                  "wc_el",
    "employer's liability":                                  "wc_el",
    "workmen's":                                             "wc_el",            # NIC truncated

    # --- Public / Product Liability ---
    "public/ product liability":                             "public_product_liability",
    "public/product liability":                              "public_product_liability",
    "public liability":                                      "public_product_liability",
    "product liability":                                     "public_product_liability",
    "public/ product":                                       "public_product_liability",  # NIC truncated
    "public/ product/other liability":                       "public_product_liability",  # Kotak variant
    "liability":                                             "public_product_liability",  # GoDigit

    # --- Engineering / Aviation ---
    "engineering":                                           "engineering",
    "aviation":                                              "aviation",

    # --- Crop ---
    "crop insurance":                                        "crop_insurance",
    "weather & crop insurance":                              "crop_insurance",
    "weather and crop insurance":                            "crop_insurance",
    "crop/weather insurance":                                "crop_insurance",   # HDFC Ergo
    "crop":                                                  "crop_insurance",   # Magma

    # --- Credit ---
    "credit insurance":                                      "credit_insurance",

    # --- Other Miscellaneous ---
    "other miscellaneous segments":                          "other_miscellaneous",
    "other miscellaneous":                                   "other_miscellaneous",
    "other segments":                                        "other_miscellaneous",  # broad alias (29 companies)
    "other segments (credit guarantee)":                     "other_miscellaneous",  # SBI variant
    "miscellaneous":                                         "other_miscellaneous",
    "miscellaneous - total":                                 "other_miscellaneous",  # Universal Sompo
    "others":                                                "other_miscellaneous",
}

# Compiled patterns for rows to skip entirely (serial numbers, headers, totals)
NL35_SKIP_PATTERNS = [
    re.compile(r"^\d+$"),                                          # serial numbers
    re.compile(r"^sl\.?\s*no", re.IGNORECASE),
    re.compile(r"^s\.?\s*no", re.IGNORECASE),
    re.compile(r"^line\s+of\s+business", re.IGNORECASE),
    re.compile(r"^note", re.IGNORECASE),
    re.compile(r"^grand\s+total", re.IGNORECASE),
    # Skip subtotals we don't capture in NL-35 (motor, marine, miscellaneous)
    # but NOT total_health — that is a first-class LOB in this form.
    re.compile(r"^total\s*$", re.IGNORECASE),           # bare "Total" / "TOTAL"
    re.compile(r"^total\s+motor", re.IGNORECASE),
    re.compile(r"^total\s+marine", re.IGNORECASE),
    re.compile(r"^total\s+miscellaneous", re.IGNORECASE),
    re.compile(r"^particulars", re.IGNORECASE),
    re.compile(r"^sr\.?\s*no", re.IGNORECASE),
    # Document / form header noise (United India, ICICI, etc.)
    re.compile(r"^form\s+nl[-\s\u2013]?35", re.IGNORECASE),       # "FORM NL-35 …"
    re.compile(r"^nl-35[-\s\u2013]", re.IGNORECASE),               # "NL-35- QUARTERLY …"
    re.compile(r"^periodic\s+disclosures?\s*$", re.IGNORECASE),    # "PERIODIC DISCLOSURES"
    re.compile(r"^date\s+of\s+upload", re.IGNORECASE),             # "Date of Upload: …"
    re.compile(r"^report\s+version", re.IGNORECASE),               # "Report Version: …"
    re.compile(r"(?:insurance|assurance)\s+company\s+limited", re.IGNORECASE),  # company name rows
    re.compile(r".*\*+\s*$", re.DOTALL),                                        # footnote-marker labels (e.g. "Other segments **")
]
