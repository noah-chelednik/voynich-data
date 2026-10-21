# tests/regressions/09e1ca3c/test_finding_3.py
import pytest

from parsers import IVTFFParser, parse_markup
from parsers.ivtff_markup import UNKNOWN


def test_inline_comment_length_limit_reaches_parser_rejection():
    # IVTFF 2.0 Table 11 limit, not a corpus-count expectation.
    limit = 80
    allowed = "<!" + "x" * (limit - len("<!>")) + ">"
    oversized = "<!" + "x" * (limit + 1 - len("<!>")) + ">"
    prefix = "#=IVTFF Eva- 2.0 M 5\n<f1r>\n<f1r.1,@P0> "

    assert not parse_markup("a" + allowed + "b").problems
    control = list(
        IVTFFParser(strict=True).parse_string(prefix + "a" + allowed + "b\n")
    )
    assert control[0].loci[0].locus_id == "f1r:1"

    raw = "a" + oversized + "b"
    markup = parse_markup(raw)
    assert markup.raw == raw
    assert markup.problems
    assert any(token.kind == UNKNOWN for token in markup.tokens)

    with pytest.raises(ValueError, match="undefined markup"):
        list(IVTFFParser(strict=True).parse_string(prefix + raw + "\n"))

    parser = IVTFFParser()
    pages = list(parser.parse_string(prefix + raw + "\n"))
    assert not any(page.loci for page in pages)
    assert any(warning.locus_id == "f1r:1" for warning in parser.warnings)
