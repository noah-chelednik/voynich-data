# tests/regressions/6ca5c86f/test_finding_2.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize("expression", [
    "len(rows_by_status[status]) >= 10",
    "len(rows_by_folio[folio]) > 100",
    "100 <= len(rows_by_status[status])",
])
def test_population_threshold_overrides_incidental_identity_names(expression):
    path = "tests/probe.py"

    assert _literal_count_hits(
        path, "assert len(rows_by_status[status]) >= 2\n"
    )
    assert not _literal_count_hits(
        path, "assert response.status_code == 200\n"
    )

    hits = _literal_count_hits(path, f"assert {expression}\n")
    assert hits, f"Population threshold bypassed the detector: {expression}"
