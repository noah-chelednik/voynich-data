# tests/regressions/1c53841b/test_reach_1.py
import pytest

from tests import test_comparison as checks
from vcat import comparison as cmp


def test_real_verdict_predicate_rejects_lost_alternate_matches(monkeypatch):
    zl_it = (
        checks.loci("ZL3b-n.txt"),
        checks.loci("IT_ivtff_1a.txt"),
    )
    zl, it = zl_it
    checks.test_every_real_verdict_follows_its_rule(zl_it)

    original = cmp.compare
    assert any(
        original(zl[locus_id], it[locus_id])[0] == cmp.ALTERNATE_READING
        for locus_id in set(zl) & set(it)
    ), "Positive control: the sources must exercise alternate matches"

    def lose_alternate_matches(a, b, profile_name=cmp.COMPARISON_PROFILE):
        verdict, score = original(a, b, profile_name)
        if verdict == cmp.ALTERNATE_READING:
            return cmp.DIFFERENT, score
        return verdict, score

    monkeypatch.setattr(cmp, "compare", lose_alternate_matches)
    with pytest.raises(AssertionError):
        checks.test_every_real_verdict_follows_its_rule(zl_it)
