# tests/regressions/d66fcb6d/test_finding_1.py
import shutil

from builders.build_metadata import build_metadata_datasets
from vcat.layers import load_layers
from vcat.sources import ROOT, registered_source, source_file


def test_layers_preserve_source_identity_after_renaming(tmp_path):
    original = ROOT / source_file("GC")
    renamed = tmp_path / source_file("ZL").name
    shutil.copyfile(original, renamed)

    registered = registered_source(renamed)
    assert registered is not None
    assert registered.id == "GC"

    result = build_metadata_datasets(renamed)
    assert any(row.order == "gc_file" for row in result.page_orders)

    assert result.tables()["layers"] == load_layers(metadata_source="GC")
