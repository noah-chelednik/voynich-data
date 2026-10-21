import builtins
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from parsers import page_order_key
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants
from vcat.loss_accounting import census_source, resolve_source

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output"


def rows(relative):
    return [
        json.loads(line)
        for line in (OUT / relative).read_text().splitlines()
        if line.strip()
    ]


def jsonl(records):
    return "".join(json.dumps(row) + "\n" for row in records)


@pytest.fixture(scope="module")
def observe():
    original_read = Path.read_text
    original_open = builtins.open
    original_table = pq.read_table

    def run(texts=None, tables=None):
        text_map = {
            (OUT / name).resolve(): content
            for name, content in (texts or {}).items()
        }
        table_map = {
            (OUT / name).resolve(): records
            for name, records in (tables or {}).items()
        }

        def read(path, *args, **kwargs):
            target = path.resolve()
            if target in text_map:
                return text_map[target]
            return original_read(path, *args, **kwargs)

        def opened(file, *args, **kwargs):
            if isinstance(file, (str, Path)):
                target = Path(file).resolve()
                if target in text_map:
                    return io.StringIO(text_map[target])
            return original_open(file, *args, **kwargs)

        def table(path, *args, **kwargs):
            target = Path(path).resolve()
            if target in table_map:
                return pa.Table.from_pylist(table_map[target])
            return original_table(path, *args, **kwargs)

        with (
            patch.object(Path, "read_text", read),
            patch("builtins.open", opened),
            patch.object(pq, "read_table", table),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            phase, errors = validate_outputs(OUT)
            invariant = verify_all_invariants(OUT)
        return (phase, invariant.passed), (errors, invariant.failures)

    accepted, details = run()
    assert all(accepted), details
    return run


def metadata_candidate(observe, stem, records):
    return observe(
        {f"metadata/{stem}.jsonl": jsonl(records)},
        {f"metadata/{stem}.parquet": records},
    )


@pytest.mark.parametrize("stem", ("pages", "folios", "quires"))
def test_rejects_empty_metadata_table(observe, stem):
    assert rows(f"metadata/{stem}.jsonl")
    accepted, details = metadata_candidate(observe, stem, [])
    assert not any(accepted), (stem, accepted, details)


@pytest.mark.parametrize("case", ("source_only", "false_hash_and_total"))
def test_rejects_broken_metadata_report(observe, case):
    report = json.loads((OUT / "metadata/metadata_report.json").read_text())
    if case == "source_only":
        candidate = {"source_file": report["source_file"]}
        assert candidate != report
    else:
        candidate = dict(
            report,
            source_hash="0" * len(report["source_hash"]),
            total_bifolia=-1,
            warnings=["probe failure"],
        )
        assert candidate["source_hash"] != report["source_hash"]
    accepted, details = observe(
        {"metadata/metadata_report.json": json.dumps(candidate)}
    )
    assert not any(accepted), (case, accepted, details)


def test_rejects_integer_completeness(observe):
    candidate = rows("metadata/bifolia.jsonl")
    assert candidate
    assert all(type(row["is_complete"]) is bool for row in candidate)
    for row in candidate:
        row["is_complete"] = int(row["is_complete"])
    accepted, details = metadata_candidate(observe, "bifolia", candidate)
    assert not any(accepted), (accepted, details)


def test_rejects_reversed_mismatch(observe):
    original = rows("mismatch_index.jsonl")
    expected = sorted(
        original,
        key=lambda row: (*page_order_key(row["page_id"]), row["line_number"]),
    )
    assert original == expected
    candidate = list(reversed(original))
    assert candidate != expected
    accepted, details = observe({"mismatch_index.jsonl": jsonl(candidate)})
    assert not any(accepted), (accepted, details)


def test_rejects_false_unrecognized_lines(observe):
    report = json.loads((OUT / "eva_lines_build_report.json").read_text())
    source = resolve_source(report["source_file"])
    assert source is not None
    assert not census_source(source).unrecognized
    assert not report["unrecognized_source_lines"]
    report["unrecognized_source_lines"] = [rows("eva_lines.jsonl")[0]["source_line"]]
    accepted, details = observe(
        {"eva_lines_build_report.json": json.dumps(report)}
    )
    assert not any(accepted), (accepted, details)
