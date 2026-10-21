# tests/regressions/9fa0ae04/test_finding_2.py
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


@pytest.mark.parametrize("mode", ("parent_relative", "absolute_filesystem"))
def test_issue_form_links_cannot_use_local_filesystem_resolution(
    monkeypatch, mode
):
    checks.test_the_documents_are_linked()
    target = checks.TEMPLATES / "data_bug.yml"
    form = checks.templates()["data_bug.yml"]

    def rendered(instructions):
        for item in form["body"]:
            if item.get("type") == "markdown":
                item["attributes"]["value"] = instructions
        return yaml.safe_dump(form, sort_keys=False)

    changed = rendered("See STABILITY.md and ERRATA.md.")
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)

    # Positive control: plain filenames are rejected.
    with pytest.raises(AssertionError):
        checks.test_the_documents_are_linked()

    names = ("STABILITY.md", "ERRATA.md")
    targets = [
        f"../{name}"
        if mode == "parent_relative"
        else (checks.ROOT / name).as_posix()
        for name in names
    ]
    changed = rendered(
        "\n".join(
            f"[{name}]({destination})"
            for name, destination in zip(names, targets)
        )
    )

    with pytest.raises(AssertionError):
        checks.test_the_documents_are_linked()
