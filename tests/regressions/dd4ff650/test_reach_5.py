# tests/regressions/dd4ff650/test_reach_5.py
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml

from tests import test_stability as checks


@pytest.mark.parametrize("document", ("STABILITY.md", "ERRATA.md"))
def test_data_bug_form_contains_document_links(document):
    form = checks.templates()["data_bug.yml"]
    visible = "\n".join(
        item["attributes"]["value"]
        for item in form["body"]
        if item.get("type") == "markdown"
    )
    targets = re.findall(r"\]\(([^)\s]+)\)", visible)
    targets += re.findall(r"https?://[^\s<>)]+", visible)
    assert any(
        urlsplit(target).path.rsplit("/", 1)[-1] == document
        for target in targets
    ), f"No link to {document} in the data-bug form"


def test_link_guard_rejects_plain_filenames(monkeypatch):
    checks.test_the_documents_are_linked()
    target = checks.TEMPLATES / "data_bug.yml"
    form = checks.templates()["data_bug.yml"]
    for item in form["body"]:
        if item.get("type") == "markdown":
            item["attributes"]["value"] = "See STABILITY.md and ERRATA.md."
    changed = yaml.safe_dump(form, sort_keys=False)
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_the_documents_are_linked()
