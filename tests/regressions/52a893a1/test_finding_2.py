# tests/regressions/52a893a1/test_finding_2.py
import json

from builders.build_metadata import (
    build_metadata_datasets,
    export_metadata,
    export_to_parquet,
)
from parsers import IVTFFParser
from validators.validate_phase1_outputs import check_metadata
from vcat.sources import ROOT, source_file


def test_emitted_locus_warning_cannot_justify_a_rejected_page(tmp_path):
    source = ROOT / source_file("CD")
    parser = IVTFFParser()
    pages = list(parser.parse_file(source))
    retained = [
        warning
        for warning in parser.warnings
        if warning.emitted_id
        and warning.page_id is None
        and warning.locus_id is None
    ]
    assert retained
    identifier = retained[0].emitted_id
    assert identifier in {
        locus.locus_id for page in pages for locus in page.loci
    }
    assert identifier not in {page.page_id for page in pages}

    result = build_metadata_datasets(source)
    assert result.report.reported_pages == []

    output = tmp_path / "output"
    metadata = output / "metadata"
    export_metadata(result, metadata)
    export_to_parquet(result, metadata)
    assert check_metadata(output) == []

    report_path = metadata / "metadata_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["reported_pages"] = [identifier]
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert check_metadata(output), (
        "An emitted locus was accepted as a rejected page"
    )
