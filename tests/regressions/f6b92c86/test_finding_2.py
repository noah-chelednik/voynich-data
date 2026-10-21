# tests/regressions/f6b92c86/test_finding_2.py
import pytest

from parsers import IVTFFParser, parse_markup
from parsers.ivtff_markup import UNKNOWN


@pytest.mark.parametrize(
    "raw",
    ["a.<->b", "a<->,b", "a,<~>b", "a<~>.b"],
)
def test_drawing_marker_adjacency_is_rejected(raw):
    prefix = "#=IVTFF Eva- 2.0 M 5\n<f1r>\n<f1r.1,@P0> "

    for control in ("a<->b", "a<~>b"):
        assert not parse_markup(control).problems
        assert list(
            IVTFFParser(strict=True).parse_string(prefix + control + "\n")
        )[0].loci

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
