# tests/regressions/e85b7f33/test_reach_3.py
from copy import deepcopy
from pathlib import Path

import pytest

from tests import test_sources as checks
from vcat import sources as registry


@pytest.mark.parametrize("pin", [None, ""])
def test_fetch_refuses_a_missing_pin(tmp_path, monkeypatch, pin):
    data = deepcopy(registry.load_sources())
    entry = data["cached"][0]
    data["cached"] = [entry]
    entry["sha256"] = pin
    monkeypatch.setattr(registry, "load_sources", lambda *args, **kwargs: data)

    try:
        fetch = checks._fetch_module()
    except ValueError:
        return  # Rejecting the malformed registry before fetching is valid.

    cache = tmp_path / "cache"
    monkeypatch.setattr(fetch, "CACHE_DIR", cache)

    def download(url, destination):
        destination.write_bytes(b"unverified downloaded bytes\n")
        return True

    monkeypatch.setattr(fetch, "fetch_file", download)
    try:
        status = fetch.main()
    except ValueError:
        status = 1

    assert not (cache / Path(entry["file"]).name).exists()
    assert status != 0
