# tests/regressions/bef641e7/test_reach_4.py
from pathlib import Path

import pytest

from builders.cards import layers_field_table
from tests import test_cards as checks


@pytest.mark.parametrize("guard", ["records", "statistics"])
def test_card_rejects_conflicting_layer_table(monkeypatch, guard):
    def verify():
        if guard == "records":
            checks.test_metadata_card_states_the_records_and_the_build("pages")
        else:
            checks.test_metadata_card_statistics_are_the_report()

    verify()

    card_path = checks.METADATA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    rendered = layers_field_table()
    incorrect = rendered.replace(
        "| `source` |", "| `invented_field` |", 1
    )
    assert incorrect != rendered
    assert rendered in original
    candidate = original.replace(
        rendered, incorrect + "\n\n" + rendered, 1
    )

    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == card_path:
            return candidate
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(AssertionError):
        verify()
