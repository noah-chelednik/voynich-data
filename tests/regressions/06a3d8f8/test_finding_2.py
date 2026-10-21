# tests/regressions/06a3d8f8/test_finding_2.py
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "text_clean",
    ["Dacty,al.dyok@192;.ol", "da{cty,al.dyok@192;.ol"],
)
def test_charset_predicate_detects_disabled_charset_checker(
    tmp_path, monkeypatch, text_clean
):
    spec = importlib.util.spec_from_file_location(
        "review_06a3d8f8_profile_predicates",
        ROOT / "tests" / "test_profiles.py",
    )
    assert spec is not None and spec.loader is not None
    predicates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predicates)

    predicate = (
        predicates.test_charset_invariant_accepts_only_the_sources_own_glyphs
    )
    predicate(tmp_path / "enabled", text_clean, False)

    monkeypatch.setattr(
        predicates.inv, "check_text_clean_contract", lambda *_: None
    )
    with pytest.raises(AssertionError):
        predicate(tmp_path / "disabled", text_clean, False)
