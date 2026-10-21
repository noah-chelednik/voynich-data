# tests/regressions/e85b7f33/test_reach_2.py
import importlib
from copy import deepcopy

from vcat import sources as registry


def test_unverified_registered_source_cannot_write_metadata(tmp_path, monkeypatch):
    data = deepcopy(registry.load_sources())
    source = next(e for e in data["cached"] if e["id"] == "ZL")
    source["license_verified"] = False
    source["license"] = "not-stated"
    monkeypatch.setattr(registry, "load_sources", lambda *args, **kwargs: data)

    record = next(r for r in registry.cached_sources() if r.id == source["id"])
    assert record.license_verified is False
    output = tmp_path / "metadata"

    try:
        builder = importlib.import_module("builders.build_metadata")
        status = builder.main(["--output", str(output)])
    except (ValueError, PermissionError, RuntimeError):
        status = 1
    except SystemExit as error:
        status = error.code

    assert not list(output.glob("*.jsonl")), (
        "An unverified registered source reached dataset files"
    )
    assert status not in (None, 0)
