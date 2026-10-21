# tests/regressions/0dea398a/test_reach_1.py
from copy import deepcopy

import pytest

from tests import test_transliterations as checks


def test_source_line_predicate_rejects_appended_text(monkeypatch):
    record = next(r for r in checks.RECORDS if r.id == "ZL")
    original_rows = checks.committed_rows
    changed = deepcopy(original_rows(record.id))
    changed[0]["text_raw"] += ".daiin"

    def rows(source_id):
        return changed if source_id == record.id else original_rows(source_id)

    monkeypatch.setattr(checks, "committed_rows", rows)
    with pytest.raises(AssertionError):
        checks.test_every_row_is_its_source_line(record)
