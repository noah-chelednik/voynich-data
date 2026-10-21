# tests/regressions/be0dc250/test_finding_1.py
"""`vcat-verify --online` on a malformed registry: the offline run fails it in its receipt (review 729a5385 finding 1);
the online run must do the same, never stop before a receipt is written."""
import json
from pathlib import Path

import yaml

from data_sources import verify_sources
from vcat import sources, upstream


def test_online_run_on_a_malformed_registry_writes_a_failing_receipt(monkeypatch, tmp_path):
    original_read = Path.read_text
    data = yaml.safe_load(original_read(sources.SOURCES_YAML, encoding="utf-8"))
    del data["cached"][0]["sha256"]  # a record lacking a required field: cached_sources() refuses it
    changed = yaml.safe_dump(data)

    def read_text(path, *args, **kwargs):
        if Path(path) == Path(sources.SOURCES_YAML):
            return changed
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)

    def no_network(url):
        raise OSError("no network in this test")

    monkeypatch.setattr(upstream, "fetch", no_network)

    # the offline run fails the verification in its receipt
    assert verify_sources.main(["--reports-dir", str(tmp_path / "offline")]) == 1
    assert json.loads(original_read(tmp_path / "offline" / "source_verification.json"))["_metadata"]["all_pass"] is False

    # the online run must too; at be0dc250 it raises the registry's ValueError and writes no receipt
    status = verify_sources.main(["--online", "--reports-dir", str(tmp_path / "online")])
    assert status == 1
    receipt = json.loads(original_read(tmp_path / "online" / "source_verification.json"))
    assert receipt["_metadata"]["all_pass"] is False
