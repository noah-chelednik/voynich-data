# tests/regressions/06a3d8f8/test_finding_1.py
import pytest

from parsers import IVTFFParser
from vcat.profiles import apply_profile
from vcat.text_processing import clean_text_for_analysis
from validators.verify_invariants import (
    InvariantReport,
    check_text_clean_contract,
)


@pytest.mark.parametrize(
    "text_raw",
    ["da{c*t}y", "da{c!t}y", "da[{c*t!}:o]y"],
)
def test_analysis_removes_legacy_markers_inside_ligatures(text_raw):
    parser = IVTFFParser(strict=True)
    source = (
        "#=IVTFF Eva- 2.0 M 5\n"
        "<f1r> <! $Q=A $L=A $H=1 $I=H>\n"
        f"<f1r.1,@P0> {text_raw}\n"
    )
    pages = list(parser.parse_string(source))
    locus = next(locus for page in pages for locus in page.loci)
    assert not parser.warnings

    assert apply_profile("raw-v1", text_raw) == text_raw
    assert apply_profile("diplomatic-v1", text_raw) == text_raw
    for profile_id in ("analysis-v1", "no-uncertain-spaces-v1"):
        assert apply_profile(profile_id, "dac*t!y") == "dacty"
        assert apply_profile(profile_id, text_raw) == "dacty"

    clean = clean_text_for_analysis(locus.text)
    assert clean == "dacty"
    report = InvariantReport()
    check_text_clean_contract(
        [{"line_id": locus.locus_id, "text_raw": text_raw, "text_clean": clean}],
        report,
    )
    assert report.passed, report.failures
