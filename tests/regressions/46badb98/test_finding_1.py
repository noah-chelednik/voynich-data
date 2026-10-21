# tests/regressions/46badb98/test_finding_1.py
import pytest

from parsers import IVTFFParser, parse_markup
from parsers.ivtff_markup import UNKNOWN


@pytest.mark.parametrize(
    "raw",
    [
        "qokedy. /\n/ <->daiin",
        "qokedy<-> /\n/ ,daiin",
        "qokedy, /\r\n/ <~>daiin",
        "qokedy<~> /\r\n/ .daiin",
    ],
)
def test_drawing_adjacency_is_checked_across_wraps(raw):
    prefix = "#=IVTFF Eva- 2.0 M 5\n<f1r>\n<f1r.1,@P0> "

    for control in ("qokedy /\n/ <->daiin", "qokedy<~> /\n/ daiin"):
        assert not parse_markup(control).problems
        pages = list(
            IVTFFParser(strict=True).parse_string(prefix + control + "\n")
        )
        assert pages[0].loci

    markup = parse_markup(raw)
    assert markup.raw == raw
    assert markup.problems
    assert any(token.kind == UNKNOWN for token in markup.tokens)

    with pytest.raises(ValueError, match="undefined markup"):
        list(IVTFFParser(strict=True).parse_string(prefix + raw + "\n"))

    parser = IVTFFParser()
    pages = list(parser.parse_string(prefix + raw + "\n"))
    assert not any(page.loci for page in pages)
    assert [warning.locus_id for warning in parser.warnings] == ["f1r:1"]
