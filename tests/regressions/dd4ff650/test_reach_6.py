# tests/regressions/dd4ff650/test_reach_6.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


@pytest.mark.parametrize("doc", ("STABILITY.md", "ERRATA.md"))
def test_collected_path_checks_cover_new_policy_documents(monkeypatch, doc):
    target = checks.ROOT / doc
    missing = "tests/__reach_missing_dd4ff650__.py"
    assert not (checks.ROOT / missing).exists()
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        text = read_text(self, *args, **kwargs)
        if self == target:
            text += f"\nRepository file: `{missing}`.\n"
        return text

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        for registered_doc in checks.DOCS_WITH_PATHS:
            checks.test_documented_repository_paths_exist(registered_doc)


@pytest.mark.parametrize(
    ("missing", "reference"),
    (
        (
            "__reach_missing_dd4ff650__.md",
            "`__reach_missing_dd4ff650__.md`",
        ),
        (
            "tests/__reach_missing_dd4ff650__.py",
            "[repository file](tests/__reach_missing_dd4ff650__.py)",
        ),
        (
            ".github/__reach_missing_dd4ff650__.yml",
            "`.github/__reach_missing_dd4ff650__.yml`",
        ),
    ),
)
def test_path_guard_reaches_reference_spellings(
    monkeypatch, missing, reference
):
    doc = "README.md"
    checks.test_documented_repository_paths_exist(doc)
    assert not (checks.ROOT / missing).exists()
    target = checks.ROOT / doc
    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        text = read_text(self, *args, **kwargs)
        if self == target:
            text += f"\nRepository file: {reference}.\n"
        return text

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)
