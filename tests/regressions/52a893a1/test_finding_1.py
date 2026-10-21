# tests/regressions/52a893a1/test_finding_1.py
import shutil

from builders.build_metadata import build_metadata_datasets
from vcat.layers import load_layers
from vcat.sources import ROOT, registered_source, source_file


def test_completed_build_keeps_provenance_after_input_cleanup(tmp_path):
    original = ROOT / source_file("GC")
    temporary = tmp_path / source_file("ZL").name
    shutil.copyfile(original, temporary)

    identity = registered_source(temporary)
    assert identity is not None
    assert identity.id == "GC"

    result = build_metadata_datasets(temporary)
    assert any(row.order == "gc_file" for row in result.page_orders)
    expected = load_layers(metadata_source="GC")

    # Cleanup precedes the first serialization of the completed result.
    temporary.unlink()

    assert result.tables()["layers"] == expected
