# tests/regressions/07428068/test_finding_1.py
"""docs/reference_checks.md says "a parse that loses text, keeps markup in a reading, or keeps uncertain readings moves
these statistics away from what others measured" and "That VCAT's statistics agree with the literature within these
tolerances says the data is complete and cleanly read". For FG, keeping uncertain readings (diplomatic-v1, the damage
`uncertain-kept`) moves all three statistics TOWARD the published values and passes every FG check: no check of FG
fails on that damage."""
import re
from pathlib import Path

from tests import test_reference_checks as checks

ROOT = Path(__file__).resolve().parents[3]
CLAIMS = (
    "or keeps uncertain readings moves these statistics away from what others measured",
    "says the data is complete and cleanly read",
)


def test_every_source_fails_some_check_when_uncertain_readings_are_kept():
    doc = re.sub(r"\s+", " ", (ROOT / "docs" / "reference_checks.md").read_text(encoding="utf-8"))
    if not any(claim in doc for claim in CLAIMS):
        return
    blind = []
    for source in sorted({r["source"] for r in checks.REGISTRY["references"]}):
        refs = [r for r in checks.REGISTRY["references"] if r["source"] == source]
        damaged = checks._damaged(source, "uncertain-kept")
        if all(checks.within(damaged[r["measure"]], r) for r in refs):
            blind.append(source)
    assert not blind, f"uncertain readings kept pass every check of {blind}, which the document says they fail"
