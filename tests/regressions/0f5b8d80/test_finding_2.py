# tests/regressions/0f5b8d80/test_finding_2.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_zenodo_freeze_step_does_not_ask_to_correct_before_a_publish_that_already_happened():
    """Step 1 says Zenodo archives the GitHub release and gives it a DOI on publish; it cannot then also ask to correct
    the record 'before publishing it there', and it must not leave the 0.1.0 date-released uncorrected."""
    doc = (ROOT / "docs" / "ZENODO_SETUP.md").read_text(encoding="utf-8")
    step = re.search(r"^1\. On GitHub, go to Releases.*?(?=^2\. )", doc, re.S | re.M).group(0)
    contradictory = "Zenodo archives it and gives it a DOI" in step and "before publishing it there" in step
    assert not contradictory, step
