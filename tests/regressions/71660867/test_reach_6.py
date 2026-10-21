# tests/regressions/71660867/test_reach_6.py
from pathlib import Path

import pytest

from tests import test_cards as checks


def test_words_config_guard_rejects_an_additional_line_file(monkeypatch):
    checks.test_eva_card_states_the_schema_and_the_build()
    checks.test_card_numbers_come_from_the_renderings(checks.EVA_CARD)

    card_path = checks.EVA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    anchor = "        path: eva_words.parquet\n"
    assert anchor in original
    changed = original.replace(
        anchor,
        anchor + "      - split: train\n        path: eva_lines.parquet\n",
        1,
    )
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == card_path:
            return changed
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(AssertionError):
        checks.test_eva_card_states_the_schema_and_the_build()
        checks.test_card_numbers_come_from_the_renderings(checks.EVA_CARD)
