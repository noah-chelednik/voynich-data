# tests/regressions/0dea398a/test_reach_6.py
from pathlib import Path

import pytest

from tests import test_cards as checks


def test_every_card_predicates_reject_extra_mismatch_field(monkeypatch):
    target = (
        checks.ROOT
        / "huggingface"
        / "voynich-transcription-mismatch"
        / "README.md"
    )
    original_read_text = Path.read_text
    text = original_read_text(target, encoding="utf-8")
    boundary = "\n\n### Status Values"
    assert boundary in text
    changed = text.replace(
        boundary,
        "\n| `invented_field` | string | Absent from the dataset |" + boundary,
        1,
    )

    def read_text(path, *args, **kwargs):
        if path == target:
            return changed
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        checks.test_eva_card_states_the_schema_and_the_build()
        for name in checks.RECORDS:
            checks.test_metadata_card_states_the_records_and_the_build(name)
        checks.test_metadata_card_statistics_are_the_report()
