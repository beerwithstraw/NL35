"""
Company parser registry for NL-35.
Phase 1: Bajaj only. Add other companies in Phase 2.
"""
from .bajaj_allianz import parse_bajaj_nl35

PARSER_REGISTRY = {
    "parse_bajaj_nl35": parse_bajaj_nl35,
}
