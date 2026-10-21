# tests/regressions/f6b92c86/test_finding_3.py
from parsers import parse_markup
from vcat import validate_eva_text
from vcat.text_processing import clean_text_for_analysis


def test_free_comment_braces_do_not_change_eva_compound_counts():
    plain = "c{h}edy"
    commented = "c<!{>{h}edy"

    assert not parse_markup(plain).problems
    assert not parse_markup(commented).problems
    assert clean_text_for_analysis(plain) == clean_text_for_analysis(commented)

    expected = validate_eva_text(plain, strict=True)
    actual = validate_eva_text(commented, strict=True)

    assert expected.compound_counts
    assert expected.is_valid and actual.is_valid
    assert actual.compound_counts == expected.compound_counts
    assert actual.char_frequencies == expected.char_frequencies
    assert actual.word_count == expected.word_count
