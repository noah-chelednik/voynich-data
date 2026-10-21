# tests/regressions/7454c2f9/test_finding_3.py
import re

from builders.build_metadata import build_metadata_datasets
from vcat.sources import ROOT, source_file


def test_gc_metadata_does_not_receive_exclusively_zl_provenance():
    source = ROOT / source_file("GC")
    result = build_metadata_datasets(source)
    assert result.report.source_file == source.name
    assert any(row.order == "gc_file" for row in result.page_orders)

    field = "voynich-manuscript-metadata:page_orders.order"
    layers = [
        row for row in result.tables()["layers"]
        if field in row["fields"]
    ]
    assert layers

    for layer in layers:
        provenance = layer["source"] + " " + layer["attribution"]
        words = set(re.findall(r"[A-Za-z0-9_]+", provenance))
        assert "ZL" not in words or "GC" in words, provenance
