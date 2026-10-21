# tests/regressions/b09d5b4b/test_reach_7.py
from pathlib import Path

import pytest

from tests import test_cards as checks


def test_card_number_guard_does_not_exempt_a_count_as_a_year(monkeypatch):
    card = checks.EVA_CARD
    checks.test_card_numbers_come_from_the_renderings(card)
    original = Path.read_text

    def changed(self, *args, **kwargs):
        text = original(self, *args, **kwargs)
        if self == card:
            text += "\nThe dataset contains 2026 loci.\n"
        return text

    monkeypatch.setattr(Path, "read_text", changed)
    with pytest.raises(AssertionError):
        checks.test_card_numbers_come_from_the_renderings(card)
