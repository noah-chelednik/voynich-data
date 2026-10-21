# tests/regressions/85247887/test_finding_2.py
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


@pytest.mark.parametrize(
    ("name", "predicate_name"),
    (
        ("data_bug.yml", "test_the_documents_are_linked"),
        ("transcription_error.yml", "test_transcription_errors_go_upstream"),
    ),
)
def test_issue_form_requirements_cannot_hide_in_comments(
    monkeypatch, name, predicate_name
):
    predicate = getattr(checks, predicate_name)
    predicate()
    target = checks.TEMPLATES / name
    form = checks.templates()[name]
    instructions = [
        (item, item["attributes"]["value"])
        for item in form["body"]
        if item.get("type") == "markdown"
    ]
    assert instructions

    def rendered(transform):
        for item, original in instructions:
            item["attributes"]["value"] = transform(original)
        return yaml.safe_dump(form, sort_keys=False)

    changed = rendered(lambda original: "Instructions unavailable.")
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)

    # Positive control: removing the required content is rejected.
    with pytest.raises(AssertionError):
        predicate()

    changed = rendered(lambda original: f"<!--\n{original}\n-->")
    with pytest.raises(AssertionError):
        predicate()
