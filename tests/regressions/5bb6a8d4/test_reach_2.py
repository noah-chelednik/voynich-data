# tests/regressions/5bb6a8d4/test_reach_2.py
import pytest

from builders.build_eva_lines import build_eva_lines
from parsers import IVTFFParser


HEADER = "#=IVTFF Eva- 2.0 M\n<f1r>\n"


@pytest.mark.parametrize("strict", [True, False])
def test_undefined_alternate_reaches_parser_rejection(strict):
    valid = HEADER + "<f1r.1,@P0> qo[a:o:e]dy\n"
    assert list(IVTFFParser(strict=strict).parse_string(valid))[0].loci

    invalid = HEADER + "<f1r.1,@P0> qo[a:o:e:y]dy\n"
    parser = IVTFFParser(strict=strict)

    if strict:
        with pytest.raises(ValueError, match="undefined markup"):
            list(parser.parse_string(invalid))
    else:
        pages = list(parser.parse_string(invalid))
        assert [warning.locus_id for warning in parser.warnings] == ["f1r:1"]
        assert not any(page.loci for page in pages)


def test_undefined_alternate_is_reported_by_the_builder(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        HEADER
        + "<f1r.1,@P0> qokedy\n"
        + "<f1r.2,+P0> qo[a:o:e:y]dy\n",
        encoding="utf-8",
    )

    records, report = build_eva_lines(source, tmp_path / "out")

    assert report.reported_loci == ["f1r:2"]
    assert [record.line_id for record in records] == ["f1r:1"]
    assert not report.loss_problems()
