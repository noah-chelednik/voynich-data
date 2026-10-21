# tests/regressions/b09d5b4b/test_reach_8.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


def test_document_path_guard_reaches_vcat_paths(monkeypatch):
    doc = "README.md"
    checks.test_documented_repository_paths_exist(doc)
    missing = "vcat/__reach_missing__.py"
    assert not (checks.ROOT / missing).exists()
    target = checks.ROOT / doc
    original = Path.read_text

    def changed(self, *args, **kwargs):
        text = original(self, *args, **kwargs)
        if self == target:
            text += f"\nImplementation: `{missing}`.\n"
        return text

    monkeypatch.setattr(Path, "read_text", changed)
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)
