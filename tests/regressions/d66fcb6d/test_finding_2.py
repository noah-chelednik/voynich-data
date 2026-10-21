# tests/regressions/d66fcb6d/test_finding_2.py
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from builders.build_metadata import (
    build_metadata_datasets,
    export_metadata,
    export_to_parquet,
)
from parsers.metadata_parser import SPANNING_PAGES
from validators.validate_phase1_outputs import check_metadata


@pytest.mark.parametrize(
    "removed_folio",
    [folio for folio, _side in SPANNING_PAGES["fRos"]],
)
def test_population_requires_every_folio_of_a_spanning_page(
    tmp_path, removed_folio
):
    source = tmp_path / "spanning.ivtff"
    source.write_text(
        "#=IVTFF Eva- 2.0\n"
        "<fRos> <! $Q=N $B=1 $I=C >\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    metadata = output / "metadata"

    result = build_metadata_datasets(source)
    # Keep this temporary source resolvable by the standalone validator.
    result.report.source_file = str(source.resolve())
    export_metadata(result, metadata)
    export_to_parquet(result, metadata)
    assert check_metadata(output) == []

    folios_path = metadata / "folios.jsonl"
    rows = [
        json.loads(line)
        for line in folios_path.read_text(encoding="utf-8").splitlines()
    ]
    assert {row["folio_id"] for row in rows} == {
        folio for folio, _side in SPANNING_PAGES["fRos"]
    }
    retained = [
        row for row in rows if row["folio_id"] != removed_folio
    ]
    assert len(retained) < len(rows)

    folios_path.write_text(
        "".join(json.dumps(row) + "\n" for row in retained),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(retained),
        metadata / "folios.parquet",
    )
    report_path = metadata / "metadata_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["total_folios"] = len(retained)
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert check_metadata(output), (
        f"Missing spanning-page folio {removed_folio} passed validation"
    )
