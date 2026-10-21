# tests/regressions/b7c1ae53/test_reach_2.py
from pathlib import Path

import pytest

from tests import test_cards as checks


@pytest.mark.parametrize(
    "predicate",
    [
        "test_metadata_card_states_the_page_canvases",
        "test_metadata_card_statistics_are_the_report",
    ],
)
def test_card_guard_rejects_wrong_canvas_config_file(monkeypatch, predicate):
    guard = getattr(checks, predicate)
    guard()

    card_path = checks.METADATA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    expected = "        path: page_canvases.jsonl"
    assert expected in original
    candidate = original.replace(expected, "        path: pages.jsonl", 1)
    assert candidate != original

    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == card_path:
            return candidate
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(AssertionError):
        guard()
