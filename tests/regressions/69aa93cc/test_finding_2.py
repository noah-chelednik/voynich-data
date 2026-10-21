# tests/regressions/69aa93cc/test_finding_2.py
import pytest

from builders.build_metadata import (
    build_metadata_datasets,
    export_metadata,
    export_to_parquet,
)
from validators.validate_phase1_outputs import check_metadata
from vcat.sources import ROOT, source_file


@pytest.mark.parametrize("source_id", ["ZL", "CD"])
def test_metadata_accepts_warnings_for_emitted_loci(tmp_path, source_id):
    result = build_metadata_datasets(ROOT / source_file(source_id))

    if source_id == "CD":
        assert result.report.warnings
        assert result.report.reported_loci == []
        assert result.report.reported_pages == []

    output = tmp_path / "output"
    metadata = output / "metadata"
    export_metadata(result, metadata)
    export_to_parquet(result, metadata)

    problems = check_metadata(output)
    assert problems == [], problems
