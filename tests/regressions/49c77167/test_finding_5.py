# tests/regressions/49c77167/test_finding_5.py
import pytest

from builders.build_eva_lines import build_eva_lines


@pytest.mark.parametrize(
    "bad",
    ["<f1r.2 @P0> otol", "<f1r.2,@P0 otol"],
)
def test_recovered_locus_is_accounted_by_builder(tmp_path, bad):
    source = tmp_path / "recoverable.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> daiin\n"
        + bad
        + "\n",
        encoding="utf-8",
    )

    records, report = build_eva_lines(source, tmp_path)

    assert {record.line_id for record in records} == {"f1r:1"}
    assert report.reported_loci == ["f1r:2"]
    assert report.loci_reported == len(report.reported_loci)
    assert report.loss_problems() == []
