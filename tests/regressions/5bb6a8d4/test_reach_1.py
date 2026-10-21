# tests/regressions/5bb6a8d4/test_reach_1.py
from parsers.ivtff_markup import UNKNOWN, parse_markup


def test_undefined_alternate_arity_is_reported_without_losing_text():
    allowed = parse_markup("[a:o:e]")
    assert not allowed.problems

    text = "[a:o:e:y]"
    markup = parse_markup(text)

    assert markup.raw == text
    assert markup.problems, "IVTFF Table 10 allows two or three readings."
    assert any(token.kind == UNKNOWN for token in markup.tokens)
