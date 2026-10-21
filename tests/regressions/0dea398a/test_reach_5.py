# tests/regressions/0dea398a/test_reach_5.py
from pathlib import Path

import pytest

from tests import test_transliterations as checks


def test_card_count_guard_rejects_short_numeric_count(monkeypatch):
    original_read_text = Path.read_text
    card = original_read_text(checks.CARD, encoding="utf-8")
    changed = card + f"\nThe dataset contains {len(checks.RECORDS)} readings.\n"

    def read_text(path, *args, **kwargs):
        if path == checks.CARD:
            return changed
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        checks.test_the_card_states_no_count_outside_its_renderings()
