# tests/regressions/3eacd8a0/test_finding_1.py
import importlib.util
from pathlib import Path
from threading import Event, Thread, current_thread

from vcat import sources as registry


def test_overlapping_fetches_never_install_unpinned_bytes(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "review_fetch_sources",
        registry.ROOT / "scripts/fetch_sources.py",
    )
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)

    record = registry.cached_sources()[0]
    name = Path(record.file).name
    pinned = record.path.read_bytes()
    different = pinned + b"\n# different upstream response\n"
    cache = tmp_path / "cache"
    monkeypatch.setattr(fetch, "CACHE_DIR", cache)
    monkeypatch.setattr(fetch, "SOURCES", {name: fetch.SOURCES[name]})

    first_hashed = Event()
    second_wrote = Event()
    first_done = Event()
    outcomes = {}
    original_hash = fetch.compute_sha256

    def download(url, destination):
        assert url == record.url
        if current_thread().name == "first-fetch":
            destination.write_bytes(pinned)
        else:
            destination.write_bytes(different)
            second_wrote.set()
            assert first_done.wait(5)
        return True

    def hash_with_overlap(path):
        digest = original_hash(path)
        if current_thread().name == "first-fetch":
            first_hashed.set()
            # A serialized implementation may prevent the second download.
            second_wrote.wait(2)
        return digest

    def worker(label):
        try:
            outcomes[label] = fetch.main()
        except Exception as error:
            outcomes[label] = error
        finally:
            if label == "first":
                first_done.set()

    monkeypatch.setattr(fetch, "fetch_file", download)
    monkeypatch.setattr(fetch, "compute_sha256", hash_with_overlap)

    first = Thread(target=worker, args=("first",), name="first-fetch")
    second = Thread(target=worker, args=("second",), name="second-fetch")
    first.start()
    try:
        assert first_hashed.wait(5)
        second.start()
    finally:
        first.join(10)
        if second.ident is not None:
            second.join(10)

    assert not first.is_alive() and not second.is_alive()
    assert (cache / name).read_bytes() == pinned, outcomes
    assert outcomes["first"] == 0, outcomes
    assert outcomes["second"] in (0, 1), outcomes
