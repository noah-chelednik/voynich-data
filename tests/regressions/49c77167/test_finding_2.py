# tests/regressions/49c77167/test_finding_2.py
import pytest

from builders.build_eva_lines import build_eva_lines


@pytest.mark.parametrize("tail", ["", "<f1r.2,+P0> otol\n"])
def test_broken_wrap_is_reported_instead_of_emitted(tmp_path, tail):
    source = tmp_path / "broken-wrap.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> daiin /\n"
        + tail,
        encoding="utf-8",
    )

    records, report = build_eva_lines(source, tmp_path)

    assert "f1r:1" not in {record.line_id for record in records}
    assert report.reported_loci == ["f1r:1"]
    assert any("f1r:1" in warning for warning in report.warnings)
    assert report.loss_problems() == []
