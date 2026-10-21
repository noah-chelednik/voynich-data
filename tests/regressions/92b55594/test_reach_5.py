# tests/regressions/92b55594/test_reach_5.py
import json
import re

import pytest

from tests import test_transliterations as checks


def test_card_predicates_reject_boolean_agreement_in_a_numeric_example(
    tmp_path, monkeypatch
):
    text = checks.CARD.read_text(encoding="utf-8")
    candidates = [
        (match, json.loads(match.group(1)))
        for match in re.finditer(r"```json\n(.*?)\n```", text, re.S)
    ]
    match, row = next(
        (match, row)
        for match, row in candidates
        if type(row.get("word_agreement")) in (int, float)
        and row["word_agreement"] in (0, 1)
    )
    row["word_agreement"] = bool(row["word_agreement"])
    changed = (
        text[:match.start(1)]
        + json.dumps(row, indent=2)
        + text[match.end(1):]
    )
    card = tmp_path / "README.md"
    card.write_text(changed, encoding="utf-8")
    monkeypatch.setattr(checks, "CARD", card)

    with pytest.raises(AssertionError):
        checks.test_the_card_states_the_schema_and_the_build()
        checks.test_the_card_states_no_count_outside_its_renderings()
