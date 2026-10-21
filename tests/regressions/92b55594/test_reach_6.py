# tests/regressions/92b55594/test_reach_6.py
import pytest

from tests import test_transliterations as checks


def test_card_predicates_reject_a_count_hidden_in_inline_code(
    tmp_path, monkeypatch
):
    rows = (checks.OUT / "word_alignments.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    wrong_count = sum(1 for row in rows if row.strip()) + 1
    text = checks.CARD.read_text(encoding="utf-8")
    text += f"\n\nThis configuration contains `{wrong_count}` alignment rows.\n"
    card = tmp_path / "README.md"
    card.write_text(text, encoding="utf-8")
    monkeypatch.setattr(checks, "CARD", card)

    with pytest.raises(AssertionError):
        checks.test_the_card_states_the_schema_and_the_build()
        checks.test_the_card_states_no_count_outside_its_renderings()
