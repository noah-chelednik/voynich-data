# tests/regressions/0ba7d188/test_finding_1.py
import importlib.util
import io
from http.client import IncompleteRead
from pathlib import Path

from vcat import sources as registry


def test_interrupted_fetch_leaves_no_cache_debris(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "review_fetch_cleanup",
        registry.ROOT / "scripts/fetch_sources.py",
    )
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)

    record = registry.cached_sources()[0]
    name = Path(record.file).name
    payload = record.path.read_bytes()
    cache = tmp_path / "cache"
    monkeypatch.setattr(fetch, "CACHE_DIR", cache)
    monkeypatch.setattr(fetch, "SOURCES", {name: fetch.SOURCES[name]})

    class TruncatedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            raise IncompleteRead(payload[:1], len(payload) - 1)

    monkeypatch.setattr(
        fetch, "urlopen", lambda *args, **kwargs: TruncatedResponse()
    )
    try:
        status = fetch.main()
    except IncompleteRead:
        status = 1

    assert status != 0
    assert list(cache.iterdir()) == [], "Interrupted fetch left cache debris"

    # A complete response must still install the pinned source.
    monkeypatch.setattr(
        fetch, "urlopen", lambda *args, **kwargs: io.BytesIO(payload)
    )
    assert fetch.main() == 0
    assert (cache / name).read_bytes() == payload
    assert sorted(path.name for path in cache.iterdir()) == [name]
