# tests/regressions/8e09e8e7/test_reach_2.py
import pytest

from parsers import IVTFFParser
from parsers.ivtff_roundtrip import rebuild_source


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    ("variable", "attribute"),
    [
        ("Q", "quire"),
        ("P", "page_in_quire"),
        ("F", "folio"),
        ("B", "bifolio"),
        ("I", "illustration"),
        ("L", "language"),
        ("H", "hand"),
        ("C", "cluster"),
        ("X", "extraneous"),
    ],
)
def test_every_text_tag_variable_starts_unset(variable, attribute, strict):
    header = f"<! ${variable}=@>"
    content = (
        "#=IVTFF Eva- 2.0\n"
        f"<f1r> {header}\n"
        "<f1r.1,@P0> daiin\n"
    )
    parser = IVTFFParser(strict=strict)
    pages = list(parser.parse_string(content))
    page = next(page for page in pages if page.page_id == "f1r")

    assert parser.warnings == []
    assert page.header_raw == header
    assert rebuild_source(parser.document) == content.encode("utf-8")
    assert getattr(page.variables, attribute) is None
