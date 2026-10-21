# tests/regressions/06fb787e/test_reach_3.py
from builders.build_eva_lines import build_eva_lines
from parsers import IVTFFParser


def test_warned_reading_id_survives_an_emitted_reading(tmp_path):
    source = tmp_path / "readings.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0\n"
        "<f1r>\n"
        "<f1r.1,@P0;H> daiin\n"
        "<f1r.1,@Pz;C> otol\n",
        encoding="utf-8",
    )

    parser = IVTFFParser()
    list(parser.parse_file(source))
    warned_ids = {w.locus_id for w in parser.warnings if w.locus_id}
    assert warned_ids == {"f1r:1"}

    records, report = build_eva_lines(source, tmp_path)
    assert {record.line_id for record in records} == {"f1r:1"}
    assert any("f1r:1" in warning for warning in report.warnings)
    assert set(report.reported_loci) == warned_ids
    assert report.source_loci == report.loci_emitted + report.loci_reported
