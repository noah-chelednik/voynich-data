# tests/regressions/3eacd8a0/test_finding_2.py
import importlib
from copy import deepcopy

import pytest

from vcat import sources as registry


def test_registered_source_alias_cannot_bypass_license(tmp_path, monkeypatch):
    builder = importlib.import_module("builders.build_metadata")
    record = next(r for r in registry.cached_sources() if r.id == "ZL")
    data = deepcopy(registry.load_sources())
    entry = next(e for e in data["cached"] if e["id"] == record.id)
    entry["license"] = "not-stated"
    entry["license_verified"] = False
    monkeypatch.setattr(registry, "load_sources", lambda *args, **kwargs: data)

    # Positive control: the registered path is refused.
    with pytest.raises(PermissionError):
        builder.build_metadata_datasets(record.path)

    alias = tmp_path / "unverified-source-alias.ivtff"
    alias.symlink_to(record.path)
    assert alias.resolve() == record.path.resolve()

    output = tmp_path / "metadata"
    with pytest.raises(PermissionError):
        builder.build_metadata_datasets(alias, output)

    assert not list(output.glob("*.jsonl"))
