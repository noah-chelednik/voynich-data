# tests/regressions/88bdfa1e/test_finding_2.py
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tests import test_cards as checks


@pytest.mark.parametrize(
    ("field", "value"),
    [("word_index", True), ("line_initial", 1)],
)
def test_card_guard_preserves_word_json_types(monkeypatch, field, value):
    checks.test_eva_card_states_the_schema_and_the_build()

    row = json.loads(
        (checks.OUTPUT / "eva_words.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    assert type(row[field]) is not type(value)
    row[field] = value

    schema = json.loads(
        (checks.ROOT / "schemas" / "eva_words.schema.json")
        .read_text(encoding="utf-8")
    )
    assert not Draft7Validator(schema).is_valid(row)

    card_path = checks.EVA_CARD.resolve()
    original = card_path.read_text(encoding="utf-8")
    changed = original + "\n```json\n" + json.dumps(row) + "\n```\n"
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == card_path:
            return changed
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(AssertionError):
        checks.test_eva_card_states_the_schema_and_the_build()
