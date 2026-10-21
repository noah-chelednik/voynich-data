# tests/regressions/cf1c8c6e/test_reach_7.py
import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize("percentage", ["42 %", "42\u00a0%"])
def test_spaced_corpus_percentages_are_rejected(monkeypatch, percentage):
    checks.test_alphabet_document_types_no_corpus_percentages()
    changed = (
        checks.EVA_DOC
        + f"\nThe glyph `a` accounts for {percentage} of corpus glyphs.\n"
    )
    monkeypatch.setattr(checks, "EVA_DOC", changed)

    with pytest.raises(AssertionError):
        checks.test_alphabet_document_types_no_corpus_percentages()
