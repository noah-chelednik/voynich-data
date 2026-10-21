# tests/regressions/094aaa5d/test_finding_1.py
from dataclasses import replace
from pathlib import Path

import pytest

from data_sources import verify_sources as verifier
from vcat import sources


@pytest.mark.parametrize("alias_kind", ["copy", "symlink"])
def test_unregistered_cache_alias_is_reported(tmp_path, monkeypatch, alias_kind):
    original = sources.cached_sources()[0]
    payload = original.path.read_bytes()

    root = tmp_path / "repo"
    cache = root / "data_sources" / "cache"
    cache.mkdir(parents=True)
    canonical = cache / Path(original.file).name
    canonical.write_bytes(payload)
    record = replace(
        original,
        file=canonical.relative_to(root).as_posix(),
    )

    monkeypatch.setattr(sources, "ROOT", root)
    monkeypatch.setattr(sources, "cached_sources", lambda: [record])
    monkeypatch.setattr(verifier, "ROOT", root)
    monkeypatch.setattr(
        verifier,
        "read_checksums",
        lambda: {canonical.name: record.sha256},
    )

    assert verifier.verify_cache()["_metadata"]["all_pass"] is True

    alias = cache / "unregistered-alias.txt"
    if alias_kind == "symlink":
        alias.symlink_to(canonical)
    else:
        alias.write_bytes(payload)

    metadata = verifier.verify_cache()["_metadata"]
    assert alias.name in metadata["unlisted_cache_files"]
    assert metadata["all_pass"] is False
