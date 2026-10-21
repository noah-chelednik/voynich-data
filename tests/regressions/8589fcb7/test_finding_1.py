# tests/regressions/8589fcb7/test_finding_1.py
import json

import pyarrow.parquet as pq

from vcat.sources import ROOT, cached_sources


def test_all_source_parquets_read_together_in_registry_order():
    records = cached_sources()
    assert records
    output = ROOT / "output" / "transliterations"
    paths = [output / f"{record.id.lower()}.parquet" for record in records]
    expected = [
        json.loads(line)
        for record in records
        for line in (
            output / f"{record.id.lower()}.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]

    assert pq.read_table(paths).to_pylist() == expected
