# tests/regressions/06fb787e/test_reach_1.py
import pytest

from parsers import IVTFFParser


@pytest.mark.parametrize(
    "bad",
    [
        "<f1r.2 @P0> otol",
        "<f1r.2,@P0 otol",
    ],
)
def test_malformed_locus_keeps_recoverable_id(bad):
    content = "<f1r>\n<f1r.1,@P0> daiin\n" + bad + "\n"

    with pytest.raises(ValueError, match=r"Line 3:"):
        list(IVTFFParser(strict=True).parse_string(content))

    parser = IVTFFParser()
    pages = list(parser.parse_string(content))
    assert [locus.locus_id for page in pages for locus in page.loci] == ["f1r:1"]
    assert [(w.line_number, w.line) for w in parser.warnings] == [(3, bad)]
    assert parser.warnings[0].locus_id == "f1r:2"
