# tests/regressions/e85b7f33/test_reach_4.py
from pathlib import Path

import pytest

from tests import test_sources as checks


def test_license_matrix_rejects_an_extra_conflicting_row(monkeypatch):
    checks.test_license_document_is_the_record()
    target = checks.ROOT / "docs/SOURCES_LICENSE.md"
    original = target.read_text(encoding="utf-8")
    row = next(line for line in original.splitlines() if line.startswith("| ZL |"))
    conflicting = row.replace("| CC0-1.0 |", "| not-stated |", 1)
    assert conflicting != row
    marker = "<!-- license:matrix:end -->"
    assert marker in original
    changed = original.replace(marker, conflicting + "\n" + marker, 1)

    read_text = Path.read_text

    def replacement(self, *args, **kwargs):
        if self == target:
            return changed
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replacement)
    with pytest.raises(AssertionError):
        checks.test_license_document_is_the_record()
