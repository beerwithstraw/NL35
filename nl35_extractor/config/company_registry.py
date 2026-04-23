"""
Company Registry for NL-35 Quarterly Business Returns extractor.
"""

# ---------------------------------------------------------------------------
# Company detection: maps normalised filename/text tokens → company key
# ---------------------------------------------------------------------------
COMPANY_MAP = {
    "acko": "acko",
    "acko general": "acko",
    "acko insurance": "acko",
    "aditya birla": "aditya_birla_health",
    "aditya birla health": "aditya_birla_health",
    "aditya birla health insurance": "aditya_birla_health",
    "adityabirla": "aditya_birla_health",
    "agriculture insurance": "aic",
    "agriculture insurance company": "aic",
    "agriculture insurance company of india": "aic",
    "aic": "aic",
    "aicof": "aic",
    "bajaj": "bajaj_allianz",
    "bajaj allianz": "bajaj_allianz",
    "bajajgeneral": "bajaj_allianz",
    "bgil": "bajaj_allianz",
    "care": "care_health",
    "care health": "care_health",
    "carehealth": "care_health",
    "chola": "chola_ms",
    "chola general": "chola_ms",
    "chola ms": "chola_ms",
    "cholamandalam": "chola_ms",
    "digit general": "go_digit",
    "ecgc": "ecgc",
    "ecgc limited": "ecgc",
    "edelweiss": "zuno",
    "edelweiss general": "zuno",
    "export credit guarantee": "ecgc",
    "future generali": "future_generali",
    "futuregenerali": "future_generali",
    "galaxy": "galaxy_health",
    "galaxy health": "galaxy_health",
    "galaxy health and allied": "galaxy_health",
    "galaxy health insurance": "galaxy_health",
    "galaxyhealth": "galaxy_health",
    "generali": "future_generali",
    "generali central": "future_generali",
    "generalicentral": "future_generali",
    "go digit": "go_digit",
    "godigit": "go_digit",
    "hdfc": "hdfc_ergo",
    "hdfc ergo": "hdfc_ergo",
    "hdfcergo": "hdfc_ergo",
    "icici": "icici_lombard",
    "icici lombard": "icici_lombard",
    "icici lombard general": "icici_lombard",
    "iffco": "iffco_tokio",
    "iffco tokio": "iffco_tokio",
    "iffco-tokio": "iffco_tokio",
    "iffcotokio": "iffco_tokio",
    "indusind": "indusind_general",
    "indusind general": "indusind_general",
    "indusind general insurance": "indusind_general",
    "kotak": "zurich_kotak",
    "kotak mahindra": "zurich_kotak",
    "kotak mahindra general": "zurich_kotak",
    "kshema": "kshema_general",
    "kshema general": "kshema_general",
    "kshema general insurance": "kshema_general",
    "liberty": "liberty_general",
    "liberty general": "liberty_general",
    "liberty videocon": "liberty_general",
    "libertygeneral": "liberty_general",
    "lombard": "icici_lombard",
    "magma": "magma_general",
    "magma general": "magma_general",
    "magma hdi": "magma_general",
    "manipal": "manipal_cigna",
    "manipal cigna": "manipal_cigna",
    "manipalcigna": "manipal_cigna",
    "narayana": "narayana_health",
    "narayana health": "narayana_health",
    "narayanahealth": "narayana_health",
    "national insurance": "national_insurance",
    "nationalinsurance": "national_insurance",
    "navi": "navi_general",
    "navi general": "navi_general",
    "new india": "new_india",
    "newindia": "new_india",
    "nic": "national_insurance",
    "niva bupa": "niva_bupa",
    "nivabupa": "niva_bupa",
    "oriental": "oriental_insurance",
    "oriental insurance": "oriental_insurance",
    "orientalinsurance": "oriental_insurance",
    "raheja": "raheja_qbe",
    "raheja qbe": "raheja_qbe",
    "reliance": "indusind_general",
    "reliance general": "indusind_general",
    "royal sundaram": "royal_sundaram",
    "sbi": "sbi_general",
    "sbi general": "sbi_general",
    "sgi": "shriram_general",
    "shriram": "shriram_general",
    "shriram general": "shriram_general",
    "sriram general": "shriram_general",
    "star": "star_health",
    "star health": "star_health",
    "star health and allied": "star_health",
    "starhealth": "star_health",
    "tata aig": "tata_aig",
    "tataaig": "tata_aig",
    "united india": "united_india",
    "united": "united_india",
    "unitedindia": "united_india",
    "universal sompo": "universal_sompo",
    "universalsompo": "universal_sompo",
    "zuno": "zuno",
    "zurich kotak": "zurich_kotak",
}

# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------
COMPANY_DISPLAY_NAMES = {
    "acko": "ACKO General Insurance Limited",
    "aditya_birla_health": "Aditya Birla Health Insurance Co. Limited",
    "aic": "Agriculture Insurance Company of India Limited",
    "bajaj_allianz": "Bajaj Allianz General Insurance Company Limited",
    "care_health": "Care Health Insurance Limited",
    "chola_ms": "Cholamandalam MS General Insurance Company Limited",
    "ecgc": "ECGC Limited",
    "future_generali": "Future Generali India Insurance Company Limited",
    "galaxy_health": "Galaxy Health and Allied Insurance Company Limited",
    "go_digit": "Go Digit General Insurance Limited",
    "hdfc_ergo": "HDFC ERGO General Insurance",
    "icici_lombard": "ICICI Lombard General Insurance Company Limited",
    "iffco_tokio": "IFFCO Tokio General Insurance Company Limited",
    "indusind_general": "IndusInd General Insurance Company Limited",
    "kshema_general": "Kshema General Insurance Limited",
    "liberty_general": "Liberty General Insurance Company Limited",
    "magma_general": "Magma General Insurance Limited",
    "manipal_cigna": "Manipal Cigna Health Insurance Company Limited",
    "narayana_health": "Narayana Health Insurance Limited",
    "national_insurance": "National Insurance Company",
    "navi_general": "Navi General Insurance Limited",
    "new_india": "The New India Assurance Company",
    "niva_bupa": "Niva Bupa Health Insurance Company Limited",
    "oriental_insurance": "The Oriental Insurance Company",
    "raheja_qbe": "Raheja QBE General Insurance Company Limited",
    "royal_sundaram": "Royal Sundaram General Insurance Co. Limited",
    "sbi_general": "SBI General Insurance Company Limited",
    "shriram_general": "Shriram General Insurance Company Limited",
    "star_health": "Star Health and Allied Insurance Co. Ltd.",
    "tata_aig": "Tata AIG General Insurance Company Limited",
    "united_india": "United India Insurance Company",
    "universal_sompo": "Universal Sompo General Insurance Company Limited",
    "zuno": "ZUNO General Insurance Limited",
    "zurich_kotak": "Zurich Kotak General Insurance Company (India) Limited",
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
