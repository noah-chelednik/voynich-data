# tests/regressions/cf1c8c6e/test_reach_5.py
import json

import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize("name", ["pages", "folios", "quires"])
@pytest.mark.parametrize("change", ["remove", "reorder"])
def test_metadata_fields_are_checked_after_the_first_row(
    monkeypatch, tmp_path, name, change
):
    checks.test_metadata_field_lists_are_the_outputs(name)
    source = checks.OUTPUT / "metadata" / f"{name}.jsonl"
    lines = source.read_text(encoding="utf-8").splitlines()
    assert lines[1:]
    original = json.loads(lines[-1])

    if change == "remove":
        changed = dict(original)
        changed.pop(next(iter(changed)))
    else:
        changed = dict(reversed(list(original.items())))
    assert list(changed) != list(original)
    lines[-1] = json.dumps(changed)

    destination = tmp_path / "metadata"
    destination.mkdir()
    (destination / f"{name}.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(checks, "OUTPUT", tmp_path)

    with pytest.raises(AssertionError):
        checks.test_metadata_field_lists_are_the_outputs(name)
