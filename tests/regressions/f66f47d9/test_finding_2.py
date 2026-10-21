# tests/regressions/f66f47d9/test_finding_2.py
from pathlib import Path

import pytest

from tests import test_cards as checks


@pytest.mark.parametrize(
    ("opening", "closing"),
    [
        ("```json", "````"),
        ("~~~json", "~~~~"),
        ("``` json", "```"),
    ],
)
def test_card_guard_checks_valid_json_fences(monkeypatch, opening, closing):
    checks.test_eva_card_states_the_schema_and_the_build()

    bad = '{"word":"not-a-committed-row"}'
    assert checks.json_blocks("```json\n" + bad + "\n```\n") == [
        {"word": "not-a-committed-row"}
    ]

    card_path = checks.EVA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    changed = original + "\n" + opening + "\n" + bad + "\n" + closing + "\n"
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == card_path:
            return changed
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(AssertionError):
        checks.test_eva_card_states_the_schema_and_the_build()
