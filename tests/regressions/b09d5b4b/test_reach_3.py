# tests/regressions/b09d5b4b/test_reach_3.py
from pathlib import Path

import pytest

from data_sources import verify_sources as verifier
from tests import test_sources as checks


def test_checksum_agreement_rejects_a_conflicting_duplicate(monkeypatch):
    checks.test_checksums_file_agrees_with_the_records()
    target = verifier.CHECKSUMS
    original = Path.read_text
    text = original(target)
    digest, name = text.splitlines()[0].split()
    wrong = "0" * len(digest)
    assert wrong != digest
    corrupted = f"{wrong}  {name}\n" + text

    def changed(self, *args, **kwargs):
        if self == target:
            return corrupted
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed)
    with pytest.raises((AssertionError, ValueError)):
        checks.test_checksums_file_agrees_with_the_records()
