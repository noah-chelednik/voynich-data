# tests/regressions/dd4ff650/test_reach_4.py
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


def test_upstream_policy_must_be_visible_in_the_form(monkeypatch):
    checks.test_transcription_errors_go_upstream()
    target = checks.TEMPLATES / "transcription_error.yml"
    form = checks.templates()["transcription_error.yml"]

    for item in form["body"]:
        if item.get("type") == "markdown":
            item["attributes"]["value"] = (
                "Use this form to record a transcription concern."
            )
        if item.get("id") == "upstream":
            item["attributes"] = {
                "label": "Additional context",
                "description": "Describe the concern.",
            }

    changed = yaml.safe_dump(form, sort_keys=False)
    changed += "\n# upstream; never corrects\n"
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_transcription_errors_go_upstream()
