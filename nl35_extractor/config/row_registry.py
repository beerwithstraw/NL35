"""
Row (LOB) Registry for NL-35 Quarterly Business Returns.

In NL-35, LOBs are the rows (not the columns). This module defines the
canonical LOB keys, their display names, alias strings, and skip patterns.
"""

import re

# Canonical LOB keys — ordered for output (matches NL-35 row order in PDFs).
# 15 entries — no sub-totals (no total_marine, total_motor, total_health,
# no grand_total). This is the defining difference from NL-6.
NL35_LOB_ORDER = [
    "fire",
    "marine_cargo",
    "marine_hull",
    "motor_od",
    "motor_tp",
    "health",
    "personal_accident",
    "travel_insurance",
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
    "fire":                                                  "fire",
    "marine cargo":                                          "marine_cargo",
    "marine other than cargo":                               "marine_hull",
    "marine hull":                                           "marine_hull",
    "motor od":                                              "motor_od",
    "motor (od)":                                            "motor_od",
    "motor owner damage":                                    "motor_od",
    "motor own damage":                                      "motor_od",
    "motor tp":                                              "motor_tp",
    "motor (tp)":                                            "motor_tp",
    "motor third party":                                     "motor_tp",
    "health":                                                "health",
    "health insurance":                                      "health",
    "personal accident":                                     "personal_accident",
    "travel":                                                "travel_insurance",
    "travel insurance":                                      "travel_insurance",
    "workmen's compensation/ employer's liability":          "wc_el",
    "workmen\u2019s compensation/ employer\u2019s liability": "wc_el",
    "workmen's compensation/employer's liability":           "wc_el",
    "workmen compensation":                                  "wc_el",
    "wc/el":                                                 "wc_el",
    "workers compensation":                                  "wc_el",
    "employer's liability":                                  "wc_el",
    "public/ product liability":                             "public_product_liability",
    "public/product liability":                              "public_product_liability",
    "public liability":                                      "public_product_liability",
    "product liability":                                     "public_product_liability",
    "engineering":                                           "engineering",
    "aviation":                                              "aviation",
    "crop insurance":                                        "crop_insurance",
    "weather & crop insurance":                              "crop_insurance",
    "weather and crop insurance":                            "crop_insurance",
    "credit insurance":                                      "credit_insurance",
    "other miscellaneous segments":                          "other_miscellaneous",
    "other miscellaneous":                                   "other_miscellaneous",
    "miscellaneous":                                         "other_miscellaneous",
    "others":                                                "other_miscellaneous",
}

# Compiled patterns for rows to skip entirely (serial numbers, headers, totals)
NL35_SKIP_PATTERNS = [
    re.compile(r"^\d+$"),                       # serial numbers
    re.compile(r"^sl\.?\s*no", re.IGNORECASE),
    re.compile(r"^s\.?\s*no", re.IGNORECASE),
    re.compile(r"^line\s+of\s+business", re.IGNORECASE),
    re.compile(r"^note", re.IGNORECASE),
    re.compile(r"^total", re.IGNORECASE),
    re.compile(r"^grand\s+total", re.IGNORECASE),
    re.compile(r"^particulars", re.IGNORECASE),
    re.compile(r"^sr\.?\s*no", re.IGNORECASE),
]
