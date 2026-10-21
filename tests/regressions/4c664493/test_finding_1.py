# tests/regressions/4c664493/test_finding_1.py
from vcat import api, profiles
from vcat.words import split_words


def test_a_newer_analysis_version_is_not_served_the_v1_word_level(monkeypatch):
    """`profiles.py`: "A new rule never changes a published version: it is a new version (analysis-v2)". Once one
    exists, ZL's words under it must be cut from its own reading, not be the analysis-v1 word level."""
    v2 = profiles.Profile(
        "analysis",
        2,
        "analysis-v1 with ',' removed (a later analysis version)",
        dict(profiles._NO_UNCERTAIN_SPACES),
    )
    monkeypatch.setitem(profiles.PROFILES, v2.id, v2)
    lines = api.load(source="ZL", unit="line", profile="analysis-v2")
    expected = [word for line in lines for word, _space in split_words(line["reading"])]
    words = api.load(source="ZL", unit="word", profile="analysis-v2")
    assert [w["word"] for w in words] == expected
