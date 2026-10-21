# tests/regressions/e85b7f33/test_reach_5.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


@pytest.mark.parametrize("style", ["titled", "reference"])
def test_documented_paths_include_all_markdown_link_forms(monkeypatch, style):
    doc = "docs/sources.md"
    target = checks.ROOT / doc
    destination = "../__reach_e85b7f33_missing__.md"
    assert not (target.parent / destination).exists()
    checks.test_documented_repository_paths_exist(doc)

    read_text = Path.read_text
    addition = f"\n[control]({destination})\n"

    def replacement(self, *args, **kwargs):
        text = read_text(self, *args, **kwargs)
        return text + addition if self == target else text

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)

    if style == "titled":
        addition = f'\n[source]({destination} "Source details")\n'
    else:
        addition = f"\n[source][reach-source]\n\n[reach-source]: {destination}\n"

    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)
