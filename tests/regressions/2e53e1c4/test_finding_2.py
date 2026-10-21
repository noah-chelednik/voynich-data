# tests/regressions/2e53e1c4/test_finding_2.py
import copy
import hashlib
import importlib
import json

import pyarrow.parquet as pq

from vcat import iiif
from vcat.sources import source_file


def test_metadata_exports_keep_the_canvas_snapshot(tmp_path, monkeypatch):
    builder = importlib.import_module("builders.build_metadata")
    original = iiif.load_canvases()
    active = {"extract": original}
    monkeypatch.setattr(
        builder,
        "load_canvases",
        lambda: copy.deepcopy(active["extract"]),
    )

    destination = tmp_path / "metadata"
    result = builder.build_metadata_datasets(source_file("ZL"), destination)
    json_rows = [
        json.loads(line)
        for line in (destination / "page_canvases.jsonl").read_text().splitlines()
    ]
    assert json_rows
    assert result.report.total_page_canvases == len(json_rows)

    refreshed = copy.deepcopy(original)
    removed_id = json_rows[0]["canvas_id"]
    refreshed["canvases"] = [
        canvas
        for canvas in refreshed["canvases"]
        if canvas["canvas_id"] != removed_id
    ]
    for position, canvas in enumerate(refreshed["canvases"], start=1):
        canvas["index"] = position
    refreshed["canvases_sha256"] = hashlib.sha256(
        iiif.canonical(refreshed["canvases"]).encode()
    ).hexdigest()
    refreshed["manifest_sha256"] = hashlib.sha256(
        b"refreshed manifest"
    ).hexdigest()
    active["extract"] = refreshed

    builder.export_to_parquet(result, destination)
    parquet_rows = pq.read_table(
        destination / "page_canvases.parquet"
    ).to_pylist()
    assert parquet_rows == json_rows
    assert result.report.iiif_manifest_sha256 == original["manifest_sha256"]
