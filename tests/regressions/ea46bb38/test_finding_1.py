# tests/regressions/ea46bb38/test_finding_1.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


@pytest.mark.parametrize(
    ("doc", "destination"),
    (
        ("docs/sources.md", "../__review_missing_ea46bb38__.md"),
        ("docs/sources.md", "STABILITY.md"),
        ("README.md", "__review_missing_ea46bb38__/policy.md"),
        ("README.md", "__review_missing_ea46bb38__"),
    ),
)
def test_markdown_destinations_are_checked_where_they_resolve(
    monkeypatch, doc, destination
):
    checks.test_documented_repository_paths_exist(doc)
    target = checks.ROOT / doc
    assert not (target.parent / destination).exists()
    control = "tests/__review_missing_ea46bb38__.py"
    assert not (checks.ROOT / control).exists()
    assert not (target.parent / control).exists()

    read_text = Path.read_text
    addition = f"\n[control]({control})\n"

    def replacement(self, *args, **kwargs):
        text = read_text(self, *args, **kwargs)
        return text + addition if self == target else text

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)

    addition = f"\n[repository document]({destination})\n"
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)
