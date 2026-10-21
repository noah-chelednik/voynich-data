# tests/regressions/3d607506/test_finding_2.py
import pytest

from tests import test_transliterations as checks


def test_card_count_guard_rejects_a_number_and_unit_in_inline_code(
    tmp_path, monkeypatch
):
    original = checks.CARD.read_text(encoding="utf-8")
    wrong_count = sum(
        bool(line.strip())
        for line in (checks.OUT / "word_alignments.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ) + 1
    card = tmp_path / "README.md"
    monkeypatch.setattr(checks, "CARD", card)

    # Positive control: the existing digits-only spelling is detected.
    card.write_text(
        original
        + f"\n\nThis configuration contains `{wrong_count}` alignment rows.\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        checks.test_the_card_states_no_count_outside_its_renderings()

    # Putting the unit inside the span does not turn the count into an identifier.
    card.write_text(
        original
        + f"\n\nThis configuration contains `{wrong_count} alignment rows`.\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        checks.test_the_card_states_no_count_outside_its_renderings()
