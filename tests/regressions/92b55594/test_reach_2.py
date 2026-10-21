# tests/regressions/92b55594/test_reach_2.py
from copy import deepcopy

import pytest

from tests import test_variants as checks


@pytest.mark.parametrize(
    "field",
    ["source", "transcriber", "locus_type", "source_line"],
)
def test_locus_predicate_rejects_changed_reader_provenance(monkeypatch, field):
    changed = deepcopy(checks.LOCI)
    locus = next(row for row in changed if row["readings"])
    reading = locus["readings"][0]
    original = reading[field]
    reading[field] = (
        original + 1 if field == "source_line" else f"{original}_reach_probe"
    )
    monkeypatch.setattr(checks, "LOCI", changed)

    with pytest.raises(AssertionError):
        checks.test_every_locus_row_is_its_sources_read_again()
