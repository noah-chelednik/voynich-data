# tests/regressions/cad4bcad/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "source",
    [
        (
            "def check():\n"
            "    rows = list(IVTFFParser().parse_file(ZL))\n"
            "    assert len(rows) == 9\n"
            "    rows = []\n"
        ),
        (
            "def check():\n"
            "    rows = list(IVTFFParser().parse_file(ZL))\n"
            "    assert len(rows) == 9\n"
            "    def helper():\n"
            "        rows = []\n"
        ),
        (
            "pages = list(IVTFFParser().parse_file(ZL))\n"
            "rows = [locus for page in pages for locus in page.loci]\n"
            "assert len(rows) == 9\n"
        ),
    ],
)
def test_real_population_equalities_keep_their_provenance(source):
    control = (
        "rows = list(IVTFFParser().parse_file(ZL))\n"
        "assert len(rows) == 9\n"
    )
    assert _literal_count_hits("tests/probe.py", control)
    assert _literal_count_hits("tests/probe.py", source), source
