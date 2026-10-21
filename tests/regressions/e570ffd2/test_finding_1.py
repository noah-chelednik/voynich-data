# tests/regressions/e570ffd2/test_finding_1.py
"""docs/upstream_tracking.md says the workflow "runs every Monday". GitHub disables a scheduled workflow in a public
repository after 60 days with no repository activity, and the run then stops with no failed run and no issue. A quiet
data repository is exactly that case, so the weekly check can stop with nothing in the repository showing it. The
document should say so (or the workflow should guard against it)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_the_document_says_when_the_weekly_schedule_stops():
    doc = (ROOT / "docs" / "upstream_tracking.md").read_text(encoding="utf-8")
    assert "60 days" in doc, "the weekly-schedule claim omits GitHub's inactivity disablement"
