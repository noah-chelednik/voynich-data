# tests/regressions/06fb787e/test_reach_2.py
import pytest

from parsers import IVTFFParser


def test_malformed_page_header_keeps_recoverable_id():
    bad = "<f2r"
    content = "<f1r>\n<f1r.1,@P0> daiin\n" + bad + "\n"

    with pytest.raises(ValueError, match=r"Line 3:"):
        list(IVTFFParser(strict=True).parse_string(content))

    parser = IVTFFParser()
    pages = list(parser.parse_string(content))
    assert [page.page_id for page in pages] == ["f1r"]
    assert [(w.line_number, w.line) for w in parser.warnings] == [(3, bad)]
    assert parser.warnings[0].page_id == "f2r"
