# tests/regressions/d4385eb4/test_reach_1.py
import pytest

import vcat
from tests import test_api as gate


def test_every_source_predicate_rejects_missing_zl_analysis_words(monkeypatch):
    original_load = vcat.load

    def broken_load(*args, **kwargs):
        if (
            kwargs.get("source", "ZL") == "ZL"
            and kwargs.get("unit", "line") == "word"
            and kwargs.get("profile", "analysis-v1") == "analysis-v1"
        ):
            return []
        return original_load(*args, **kwargs)

    monkeypatch.setattr(vcat, "load", broken_load)

    with pytest.raises(AssertionError):
        gate.test_every_source_s_lines_and_words_under_a_profile(
            "ZL", "analysis-v1"
        )
