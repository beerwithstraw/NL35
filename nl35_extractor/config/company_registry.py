"""
Company Registry for NL-35 Quarterly Business Returns extractor.
"""

# ---------------------------------------------------------------------------
# Company detection: maps normalised filename/text tokens → company key
# ---------------------------------------------------------------------------
COMPANY_MAP = {
    "bajaj allianz": "bajaj_allianz",
    "bajaj": "bajaj_allianz",
    "bajajgeneral": "bajaj_allianz",
    "bgil": "bajaj_allianz",
    "hdfc ergo": "hdfc_ergo",
    "hdfcergo": "hdfc_ergo",
    "hdfc": "hdfc_ergo",
    "national insurance": "national_insurance",
    "nationalinsurance": "national_insurance",
    "nic": "national_insurance",
    "new india": "new_india",
    "newindia": "new_india",
    "oriental insurance": "oriental_insurance",
    "orientalinsurance": "oriental_insurance",
    "oriental": "oriental_insurance",
    "united india": "united_india",
    "unitedindia": "united_india",
    "godigit": "go_digit",
    "go digit": "go_digit",
    "digit general": "go_digit",
    "aditya birla": "aditya_birla_health",
    "aditya birla health": "aditya_birla_health",
    "cholamandalam": "chola_ms",
    "chola ms": "chola_ms",
    "chola general": "chola_ms",
    "chola": "chola_ms",
    "ecgc": "ecgc",
    "icici lombard": "icici_lombard",
    "icici": "icici_lombard",
    "lombard": "icici_lombard",
    "acko": "acko",
    "tata aig": "tata_aig",
    "reliance general": "indusind_general",
    "royal sundaram": "royal_sundaram",
    "manipalcigna": "manipal_cigna",
    "manipal cigna": "manipal_cigna",
    "care health": "care_health",
    "carehealth": "care_health",
    "niva bupa": "niva_bupa",
    "nivabupa": "niva_bupa",
    "star health": "star_health",
    "starhealth": "star_health",
    "future generali": "future_generali",
    "shriram general": "shriram_general",
    "shriram": "shriram_general",
    "zurich kotak": "zurich_kotak",
    "kotak mahindra general": "zurich_kotak",
    "kotak": "zurich_kotak",
    "zuno": "zuno",
    "edelweiss general": "zuno",
    "agriculture insurance": "aic",
    "aic": "aic",
    "narayana health": "narayana_health",
    "narayana": "narayana_health",
    "navi general": "navi_general",
    "navi": "navi_general",
    "raheja qbe": "raheja_qbe",
    "universal sompo": "universal_sompo",
    "iffco tokio": "iffco_tokio",
    "iffco-tokio": "iffco_tokio",
    "iffco": "iffco_tokio",
    "liberty": "liberty_general",
    "liberty general": "liberty_general",
    "magma general": "magma_general",
    "magma hdi": "magma_general",
    "sbi": "sbi_general",
    "sbi general": "sbi_general",
    "kshema": "kshema_general",
    "kshema general": "kshema_general",
    "indusind": "indusind_general",
    "indusind general": "indusind_general",
    # Magma (plain token — "Magma General" and "Magma HDI" already covered above)
    "magma": "magma_general",
    # Galaxy Health Insurance
    "galaxy health": "galaxy_health",
    "galaxyhealth": "galaxy_health",
    "galaxy": "galaxy_health",
    # Generali Central (formerly Future Generali India Insurance)
    "generali central": "generali_central",
    "generalicentral": "generali_central",
    "future generali": "generali_central",
    "futuregenerali": "generali_central",
    "generali": "generali_central",
}

# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------
COMPANY_DISPLAY_NAMES = {
    "bajaj_allianz": "Bajaj Allianz General Insurance Company Limited",
    "hdfc_ergo": "HDFC ERGO General Insurance",
    "national_insurance": "National Insurance Company",
    "new_india": "The New India Assurance Company",
    "oriental_insurance": "The Oriental Insurance Company",
    "united_india": "United India Insurance Company",
    "go_digit": "Go Digit General Insurance Limited",
    "aditya_birla_health": "Aditya Birla Health Insurance Co. Limited",
    "chola_ms": "Cholamandalam MS General Insurance Company Limited",
    "ecgc": "ECGC Limited",
    "icici_lombard": "ICICI Lombard General Insurance Company Limited",
    "acko": "ACKO General Insurance Limited",
    "tata_aig": "Tata AIG General Insurance Company Limited",
    "royal_sundaram": "Royal Sundaram General Insurance Co. Limited",
    "manipal_cigna": "ManipalCigna Health Insurance Company Limited",
    "care_health": "Care Health Insurance Limited",
    "niva_bupa": "Niva Bupa Health Insurance Company Limited",
    "star_health": "Star Health and Allied Insurance Co. Ltd.",
    "future_generali": "Future Generali India Insurance Company Limited",
    "sbi_general": "SBI General Insurance Company Limited",
    "shriram_general": "Shriram General Insurance Company Limited",
    "zurich_kotak": "Zurich Kotak General Insurance Company (India) Limited",
    "zuno": "ZUNO General Insurance Limited",
    "aic": "Agriculture Insurance Company of India Limited",
    "narayana_health": "Narayana Health Insurance Limited",
    "navi_general": "Navi General Insurance Limited",
    "raheja_qbe": "Raheja QBE General Insurance Company Limited",
    "universal_sompo": "Universal Sompo General Insurance Company Limited",
    "iffco_tokio": "IFFCO Tokio General Insurance Company Limited",
    "liberty_general": "Liberty General Insurance Company Limited",
    "magma_general": "Magma General Insurance Limited",
    "kshema_general": "Kshema General Insurance Limited",
    "indusind_general": "IndusInd General Insurance Company Limited",
    "galaxy_health": "Galaxy Health Insurance Company Limited",
    "generali_central": "Generali Central Insurance Company Limited",
}

# ---------------------------------------------------------------------------
# Dedicated parser function name (None = not yet implemented for NL35)
# Phase 1: Bajaj only
# ---------------------------------------------------------------------------
DEDICATED_PARSER = {
    "bajaj_allianz": "parse_bajaj_nl35",
}

# ---------------------------------------------------------------------------
# Companies where certain LOBs are always absent (NL35-specific completeness).
# Built from PDF smoke-test evidence — only confirmed absent LOBs are listed.
# credit_insurance is reported only by Bajaj Allianz; all others ignore it.
# ---------------------------------------------------------------------------

# LOBs every non-Bajaj company ignores (credit_insurance not in their PDFs)
_NO_CREDIT = ["credit_insurance"]

# Full non-health LOB set that standalone health insurers never write
_HEALTH_ONLY_IGNORE = [
    "fire", "marine_cargo", "marine_hull",
    "motor_od", "motor_tp",
    "wc_el", "public_product_liability", "engineering",
    "aviation", "crop_insurance",
    "credit_insurance", "other_miscellaneous",
]

COMPLETENESS_IGNORE: dict = {

    # ── Standalone health insurers ──────────────────────────────────────────
    # Write only health / personal_accident / travel_insurance.
    "aditya_birla_health": _HEALTH_ONLY_IGNORE,
    "care_health":         _HEALTH_ONLY_IGNORE,
    "manipal_cigna":       _HEALTH_ONLY_IGNORE,
    "niva_bupa":           _HEALTH_ONLY_IGNORE,
    "star_health":         _HEALTH_ONLY_IGNORE,
    "narayana_health":     _HEALTH_ONLY_IGNORE,
    "galaxy_health":       _HEALTH_ONLY_IGNORE + ["travel_insurance"],
    # Kshema: general insurer but fire/marine/motor absent this quarter;
    # has crop & health but not travel
    "kshema_general":      [
        "fire", "marine_cargo", "marine_hull",
        "motor_od", "motor_tp",
        "wc_el", "public_product_liability", "engineering",
        "aviation", "travel_insurance",
        "credit_insurance", "other_miscellaneous",
    ],

    # ── General insurers — confirmed absent LOBs ────────────────────────────
    "acko":             ["aviation", "crop_insurance", "engineering",
                         "marine_cargo", "marine_hull",
                         "other_miscellaneous", "wc_el",
                         "credit_insurance"],
    "chola_ms":         ["aviation", "travel_insurance", "other_miscellaneous", "credit_insurance"],
    "go_digit":         ["crop_insurance", "credit_insurance"],
    "hdfc_ergo":        ["other_miscellaneous", "credit_insurance"],
    "icici_lombard":    ["other_miscellaneous", "credit_insurance"],
    "liberty_general":  ["aviation", "crop_insurance", "marine_hull",
                         "other_miscellaneous", "credit_insurance"],
    "raheja_qbe":       ["aviation", "crop_insurance", "marine_hull",
                         "marine_cargo", "public_product_liability",
                         "other_miscellaneous", "travel_insurance",
                         "credit_insurance"],
    "royal_sundaram":   ["aviation", "crop_insurance",
                         "other_miscellaneous", "credit_insurance"],
    "sbi_general":      _NO_CREDIT,
    "shriram_general":  _NO_CREDIT,
    "new_india":        _NO_CREDIT,
    "oriental_insurance": _NO_CREDIT,
    "universal_sompo":  ["aviation", "credit_insurance"],
    "zuno":             ["aviation", "crop_insurance", "marine_hull",
                         "public_product_liability", "credit_insurance"],
    "zurich_kotak":     ["aviation", "crop_insurance", "marine_hull",
                         "other_miscellaneous", "credit_insurance"],

    # ── Remaining companies without credit_insurance ────────────────────────
    # AIC only writes crop_insurance and other_miscellaneous
    "aic":              [
        "fire", "marine_cargo", "marine_hull",
        "motor_od", "motor_tp",
        "health", "personal_accident", "travel_insurance", "total_health",
        "wc_el", "public_product_liability", "engineering",
        "aviation", "credit_insurance",
    ],
    # ECGC only writes credit guarantee business (captured under other_miscellaneous).
    # All standard GI LOBs are always NA in their PDFs.
    "ecgc":             [
        "fire", "marine_cargo", "marine_hull",
        "motor_od", "motor_tp",
        "health", "personal_accident", "travel_insurance", "total_health",
        "wc_el", "public_product_liability", "engineering",
        "aviation", "crop_insurance", "credit_insurance",
    ],
    "generali_central": _NO_CREDIT,
    "iffco_tokio":      _NO_CREDIT,
    "indusind_general": _NO_CREDIT,
    "magma_general":    ["marine_hull", "travel_insurance", "aviation",
                         "crop_insurance", "other_miscellaneous", "credit_insurance"],
    "navi_general":     ["marine_cargo", "marine_hull", "travel_insurance",
                         "wc_el", "public_product_liability", "engineering",
                         "aviation", "crop_insurance", "other_miscellaneous",
                         "credit_insurance"],
    "national_insurance": _NO_CREDIT,
    "tata_aig":         _NO_CREDIT,
    "united_india":     _NO_CREDIT,
}
