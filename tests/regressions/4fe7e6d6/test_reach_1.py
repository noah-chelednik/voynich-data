# tests/regressions/4fe7e6d6/test_reach_1.py
"""Clause 1: the literal-count guard flags a population count read through the registry's readers. `license_statement`
is a reader of the same registry as `cached_sources` (vcat/sources.py: `load_sources(path).get("license_statement")`),
used by the suite (tests/test_sources.py), but REAL_DATA does not name it, so a literal count of the tables it reads
passes the guard while the same count read through `load_sources` is flagged."""
from tests import test_ci_checks as checks

THROUGH_LOAD_SOURCES = (
    "from vcat.sources import load_sources\n"
    "tables = load_sources()['license_statement']['tables']\n"
    "assert len(tables) == 3\n"
)
THROUGH_LICENSE_STATEMENT = (
    "from vcat.sources import license_statement\n"
    "tables = license_statement()['tables']\n"
    "assert len(tables) == 3\n"
)


def test_a_count_read_through_license_statement_is_flagged():
    # control: the same population, read through a listed reader, is flagged
    assert checks._literal_count_hits("tests/probe.py", THROUGH_LOAD_SOURCES)
    assert checks._literal_count_hits("tests/probe.py", THROUGH_LICENSE_STATEMENT), (
        "a literal count read through the registry's reader license_statement() passes the guard"
    )
