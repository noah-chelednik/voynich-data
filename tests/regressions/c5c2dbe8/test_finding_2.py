# tests/regressions/c5c2dbe8/test_finding_2.py
"""docs/reference_checks.md says of the tolerances "Each is small enough to fail on a known kind of damage, which the
suite shows by positive controls", and CHANGELOG.md that "Positive controls show each check fails on markup left in,
uncertain readings kept, or lost loci". Under exactly those three damages (raw-v1, diplomatic-v1, paragraph loci only),
fg-characters, fg-h2, cd-characters and cd-h2 still pass: their tolerances fail on no known damage."""
from pathlib import Path

from vcat import api
from vcat.reference import character_statistics, statistics, word_statistics, words_of
from tests import test_reference_checks as checks

ROOT = Path(__file__).resolve().parents[3]
DOC_CLAIM = "Each is small enough to fail on a known kind of damage"
LOG_CLAIM = "Positive controls show each check fails"


def _paragraphs_only(source):
    lines = api.load(source=source, unit="line")
    words = words_of([l["reading"] for l in lines if (l.get("locus_type") or "")[1:2] == "P"])
    return {**character_statistics(words), **word_statistics(words)}


def test_every_tolerance_the_documents_say_has_teeth_fails_on_a_named_damage():
    doc = (ROOT / "docs" / "reference_checks.md").read_text(encoding="utf-8")
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    claimed = DOC_CLAIM in doc or LOG_CLAIM in log
    if not claimed:
        return
    damaged = {}
    toothless = []
    for r in checks.REGISTRY["references"]:
        s = r["source"]
        if s not in damaged:
            damaged[s] = [statistics(s, "raw-v1"), statistics(s, "diplomatic-v1"), _paragraphs_only(s)]
        if all(checks.within(d[r["measure"]], r) for d in damaged[s]):
            toothless.append(r["id"])
    assert not toothless, f"documented as failing on a known damage, but pass all three: {toothless}"
