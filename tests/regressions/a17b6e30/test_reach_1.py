# tests/regressions/a17b6e30/test_reach_1.py
import importlib.util
from pathlib import Path

from parsers import ivtff_markup as mk
from vcat import profiles as vp

ROOT = Path(__file__).resolve().parents[3]


def test_claimed_synthetic_profile_coverage_includes_unknown(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "reach_profile_predicates", ROOT / "tests" / "test_profiles.py"
    )
    assert spec is not None and spec.loader is not None
    predicates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predicates)

    seen = set()
    original = vp.Profile.render

    def observe(profile, tokens):
        seen.update(token.kind for token in tokens)
        return original(profile, tokens)

    monkeypatch.setattr(vp.Profile, "render", observe)
    predicates.test_every_kind_of_rule_meets_a_real_line()
    predicates.test_whitespace_wraps_and_tags()

    assert mk.UNKNOWN in seen, "No synthetic UNKNOWN token reached a profile"
