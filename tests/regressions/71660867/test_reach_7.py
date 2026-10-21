# tests/regressions/71660867/test_reach_7.py
from pathlib import Path

import pytest

from tests import test_cards as checks


def test_card_row_guard_reaches_tilde_fenced_json(monkeypatch):
    checks.test_eva_card_states_the_schema_and_the_build()
    checks.test_card_numbers_come_from_the_renderings(checks.EVA_CARD)

    card_path = checks.EVA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    changed = original + (
        "\nAdditional word example:\n\n"
        "~~~json\n"
        '{"word": "not-a-committed-row"}\n'
        "~~~\n"
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
