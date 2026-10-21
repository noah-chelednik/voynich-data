# tests/regressions/6ca5c86f/test_finding_1.py
import pytest

from parsers import IVTFFParser
from parsers.ivtff_roundtrip import rebuild_source


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
@pytest.mark.parametrize("padding", [" ", "\t"])
def test_slash_only_continuation_preserves_trailing_whitespace(ending, padding):
    prefix = ending.join([
        "#=IVTFF Eva- 2.0 M 5",
        "<f1r>",
        "<f1r.1,@P0> ",
    ])
    control = ending.join(["da /", "/", "/ iin"])
    control_pages = list(
        IVTFFParser(strict=True).parse_string(prefix + control + ending)
    )
    assert control_pages[0].loci[0].text == "daiin"

    raw = ending.join(["da /", "/" + padding, "/ iin"])
    content = prefix + raw + ending
    for strict in (False, True):
        parser = IVTFFParser(strict=strict)
        pages = list(parser.parse_string(content))
        assert not parser.warnings, [str(w) for w in parser.warnings]
        loci = [locus for page in pages for locus in page.loci]
        assert [(locus.locus_id, locus.text) for locus in loci] == [
            ("f1r:1", "daiin")
        ]
        assert loci[0].text_raw == raw
        assert rebuild_source(parser.document) == content.encode("utf-8")
