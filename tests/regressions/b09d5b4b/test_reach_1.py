# tests/regressions/b09d5b4b/test_reach_1.py
import json
from pathlib import Path

import pytest

from tests import test_paperwork as checks


def test_version_predicate_checks_persisted_metadata_report(monkeypatch):
    checks.test_one_version_everywhere()
    target = checks.ROOT / "output/metadata/metadata_report.json"
    original = Path.read_text
    report = json.loads(original(target))
    report["build_version"] = checks.package_version() + "-stale"

    def changed(self, *args, **kwargs):
        if self == target:
            return json.dumps(report)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed)
    with pytest.raises(AssertionError):
        checks.test_one_version_everywhere()
