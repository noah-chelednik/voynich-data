# tests/regressions/92b55594/test_reach_4.py
import json

import pytest

from tests import test_transliterations as checks


@pytest.mark.parametrize("opener", ["~~~json", "``` json"])
def test_card_predicates_reject_uncommitted_json_in_other_fences(
    tmp_path, monkeypatch, opener
):
    text = checks.CARD.read_text(encoding="utf-8")
    fabricated = {"reader": "reach_probe"}
    text += (
        "\n\nAdditional alignment example:\n\n"
        + opener
        + "\n"
        + json.dumps(fabricated)
        + "\n"
        + opener[:3]
        + "\n"
    )
    card = tmp_path / "README.md"
    card.write_text(text, encoding="utf-8")
    monkeypatch.setattr(checks, "CARD", card)

    with pytest.raises(AssertionError):
        checks.test_the_card_states_the_schema_and_the_build()
        checks.test_the_card_states_no_count_outside_its_renderings()
