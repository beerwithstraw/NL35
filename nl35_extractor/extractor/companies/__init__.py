from .acko import parse_acko
from .aditya_birla import parse_aditya_birla
from .aditya_birla_health import parse_aditya_birla_health
from .aic import parse_aic
from .bajaj_allianz import parse_bajaj_allianz
from .care_health import parse_care_health
from .chola_ms import parse_chola_ms
from .ecgc import parse_ecgc
from .future_generali import parse_future_generali
from .go_digit import parse_go_digit
from .hdfc_ergo import parse_hdfc_ergo
from .icici_lombard import parse_icici_lombard
from .iffco_tokio import parse_iffco_tokio
from .indusind_general import parse_indusind_general
from .kshema_general import parse_kshema_general
from .liberty_general import parse_liberty_general
from .magma_general import parse_magma_general
from .national_insurance import parse_national_insurance
from .manipal_cigna import parse_manipal_cigna
from .narayana_health import parse_narayana_health
from .navi_general import parse_navi_general
from .new_india import parse_new_india
from .niva_bupa import parse_niva_bupa
from .oriental_insurance import parse_oriental_insurance
from .raheja_qbe import parse_raheja_qbe
from .royal_sundaram import parse_royal_sundaram
from .sbi_general import parse_sbi_general
from .shriram_general import parse_shriram_general
from .tata_aig import parse_tata_aig
from .united_india import parse_united_india
from .universal_sompo import parse_universal_sompo
from .zuno import parse_zuno
from .zurich_kotak import parse_zurich_kotak

PARSER_REGISTRY = {
    "parse_acko": parse_acko,
    "parse_aditya_birla": parse_aditya_birla,
    "parse_aditya_birla_health": parse_aditya_birla_health,
    "parse_aic": parse_aic,
    "parse_bajaj_allianz": parse_bajaj_allianz,
    "parse_care_health": parse_care_health,
    "parse_chola_ms": parse_chola_ms,
    "parse_ecgc": parse_ecgc,
    "parse_future_generali": parse_future_generali,
    "parse_go_digit": parse_go_digit,
    "parse_hdfc_ergo": parse_hdfc_ergo,
    "parse_icici_lombard": parse_icici_lombard,
    "parse_iffco_tokio": parse_iffco_tokio,
    "parse_indusind_general": parse_indusind_general,
    "parse_kshema_general": parse_kshema_general,
    "parse_liberty_general": parse_liberty_general,
    "parse_magma_general": parse_magma_general,
    "parse_manipal_cigna": parse_manipal_cigna,
    "parse_narayana_health": parse_narayana_health,
    "parse_national_insurance": parse_national_insurance,
    "parse_navi_general": parse_navi_general,
    "parse_new_india": parse_new_india,
    "parse_niva_bupa": parse_niva_bupa,
    "parse_oriental_insurance": parse_oriental_insurance,
    "parse_raheja_qbe": parse_raheja_qbe,
    "parse_royal_sundaram": parse_royal_sundaram,
    "parse_sbi_general": parse_sbi_general,
    "parse_shriram_general": parse_shriram_general,
    "parse_tata_aig": parse_tata_aig,
    "parse_united_india": parse_united_india,
    "parse_universal_sompo": parse_universal_sompo,
    "parse_zuno": parse_zuno,
    "parse_zurich_kotak": parse_zurich_kotak,
}
