# tests/regressions/729a5385/test_finding_1.py
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from data_sources.verify_sources import verify_cache
from vcat import sources


@pytest.mark.parametrize("bad_first", [True, False])
def test_duplicate_source_cannot_hide_failed_verification(
    monkeypatch, bad_first
):
    assert verify_cache()["_metadata"]["all_pass"] is True

    original_read = Path.read_text
    data = yaml.safe_load(original_read(sources.SOURCES_YAML))
    duplicate = deepcopy(data["cached"][0])
    duplicate["sha256"] = "0" * len(duplicate["sha256"])
    assert duplicate["sha256"] != data["cached"][0]["sha256"]

    if bad_first:
        data["cached"].insert(0, duplicate)
    else:
        data["cached"].append(duplicate)
    changed = yaml.safe_dump(data)

    def read_text(path, *args, **kwargs):
        if path == sources.SOURCES_YAML:
            return changed
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    try:
        receipt = verify_cache()
    except ValueError:
        return  # Rejecting the malformed registry also fails closed.
    assert receipt["_metadata"]["all_pass"] is False, receipt
