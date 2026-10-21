# tests/regressions/8dc8e2d0/test_finding_1.py
import pytest

from builders.build_eva_lines import build_eva_lines
from parsers import IVTFFParser


def test_slash_only_continuation_does_not_complete_a_wrap(tmp_path):
    prefix = (
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> daiin /\n"
    )

    control = IVTFFParser(strict=True)
    completed = list(control.parse_string(prefix + "/ ol\n"))
    assert completed[0].loci[0].text == "daiinol"

    content = prefix + "/\n"
    parser = IVTFFParser()
    pages = list(parser.parse_string(content))
    assert [locus for page in pages for locus in page.loci] == []
    assert [w.locus_id for w in parser.warnings if w.locus_id] == ["f1r:1"]

    with pytest.raises(ValueError, match="Line "):
        list(IVTFFParser(strict=True).parse_string(content))

    source = tmp_path / "slash-only.txt"
    source.write_text(content, encoding="utf-8")
    records, report = build_eva_lines(source, tmp_path)
    assert records == []
    assert report.reported_loci == ["f1r:1"]
    assert report.loss_problems() == []
