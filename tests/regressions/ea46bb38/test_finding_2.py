# tests/regressions/ea46bb38/test_finding_2.py
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


@pytest.mark.parametrize(
    "prefix",
    ("https://example.invalid/", "__review_missing_ea46bb38__/"),
)
def test_policy_links_must_identify_the_repository_documents(monkeypatch, prefix):
    checks.test_the_documents_are_linked()
    target = checks.TEMPLATES / "data_bug.yml"
    form = checks.templates()["data_bug.yml"]

    def rendered_form(instructions):
        for item in form["body"]:
            if item.get("type") == "markdown":
                item["attributes"]["value"] = instructions
        return yaml.safe_dump(form, sort_keys=False)

    changed = rendered_form("See STABILITY.md and ERRATA.md.")
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)

    # Positive control: the predicate rejects plain filenames.
    with pytest.raises(AssertionError):
        checks.test_the_documents_are_linked()

    changed = rendered_form(
        f"[policy]({prefix}STABILITY.md)\n"
        f"[errata]({prefix}ERRATA.md)\n"
    )
    with pytest.raises(AssertionError):
        checks.test_the_documents_are_linked()
