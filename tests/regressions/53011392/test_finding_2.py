# tests/regressions/53011392/test_finding_2.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_zenodo_freeze_step_says_what_to_do_with_the_0_1_0_date():
    doc = (ROOT / "docs" / "ZENODO_SETUP.md").read_text(encoding="utf-8")
    step = re.search(r"^1\. On GitHub, go to Releases.*?(?=^2\. )", doc, re.S | re.M).group(0)
    if "2026-01-17" in step:
        assert "2026-01-18" in step or re.search(r"\bdate\b", step), step
