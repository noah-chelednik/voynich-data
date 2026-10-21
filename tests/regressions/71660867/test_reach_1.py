# tests/regressions/71660867/test_reach_1.py
from collections import Counter

from tests import test_words as checks
from vcat import eva_charset


def test_count_predicate_reaches_every_committed_line(monkeypatch):
    original = eva_charset.validate_eva_text
    seen = []

    def observe(text, *args, **kwargs):
        seen.append(text)
        return original(text, *args, **kwargs)

    monkeypatch.setattr(eva_charset, "validate_eva_text", observe)
    checks.test_one_tokenizer_counts_every_line()

    expected = Counter(line["text_raw"] for line in checks.LINES)
    missing = expected - Counter(seen)
    assert not missing, "The line-validator comparison omitted committed inputs"
