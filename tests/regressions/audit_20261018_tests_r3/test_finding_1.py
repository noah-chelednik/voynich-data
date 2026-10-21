# tests/regressions/audit_20261018_tests_r3/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "snippet",
    [
        (
            "from vcat.sources import cached_sources\n"
            "items = cached_sources()\n"
            "assert len(items) == 9\n"
        ),
        (
            "from vcat.sources import ROOT, source_file\n"
            "from parsers import IVTFFParser\n"
            'items = list(IVTFFParser().parse_file(ROOT / source_file("CD")))\n'
            "assert len(items) == 9\n"
        ),
    ],
)
def test_registry_reads_are_recognized_as_real_data(snippet):
    assert _literal_count_hits("tests/probe.py", snippet), snippet
