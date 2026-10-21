# tests/regressions/cc2c2127/test_finding_2.py
import json
from pathlib import Path

from vcat.sources import load_sources


def test_registry_records_all_mismatch_inputs():
    root = Path(__file__).resolve().parents[3]
    registry = load_sources()
    name = "voynich-transcription-mismatch"
    dataset = next(
        d for d in registry["datasets"] if d["name"] == name
    )
    report = json.loads(
        (root / "output/mismatch_report.json").read_text()
    )
    rows = [
        json.loads(line)
        for line in (
            root / "output/mismatch_index.jsonl"
        ).read_text().splitlines()
    ]

    observed = {source.upper() for source in report["sources"]}
    present = {
        source.upper()
        for row in rows
        for source in row["sources_present"]
    }
    assert observed and present and present <= observed

    assert set(dataset["sources"]) == observed
    declared_users = {
        entry["id"]
        for entry in registry["cached"]
        if name in entry["used_by"]
    }
    assert declared_users == observed
