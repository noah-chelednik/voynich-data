# tests/regressions/audit_20261016_parsers/test_finding_2.py
from parsers import IVTFFParser


def test_extraction_preserves_ligature_glyphs_and_drawing_boundaries():
    parser = IVTFFParser()
    assert parser.extract_text("dlo{ct}o") == "dlocto"
    assert parser.extract_text("odar.{c'y}.shol") == "odar.c'y.shol"
    assert parser.extract_text("chckhy<~>oltchedy").split() == [
        "chckhy", "oltchedy"
    ]
    assert parser.extract_text("cthyd<->otar").split() == ["cthyd", "otar"]
