# tests/regressions/49c77167/test_finding_3.py
from builders.build_eva_lines import build_eva_lines
from validators.verify_invariants import InvariantReport, check_page_count


def test_page_count_keeps_page_with_emitted_sibling_reading(tmp_path):
    source = tmp_path / "readings.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0;H> daiin\n"
        "<f1r.1,@Pz;C> otol\n",
        encoding="utf-8",
    )
    records, build = build_eva_lines(source, tmp_path)
    assert build.loss_problems() == []
    assert build.reported_loci == ["f1r:1"]

    checked = InvariantReport()
    check_page_count(
        [record.to_dict() for record in records],
        checked,
        source=source,
        reported=build.reported_loci,
    )
    assert checked.passed, checked.failures
