# tests/regressions/9db38e3c/test_finding_4.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def test_report_predicate_catches_a_report_publishing_lists_but_staging_drops(tmp_path, monkeypatch):
    """Claim 2's predicate must fail when the staging drops a report docs/PUBLISHING.md still lists."""
    from builders import stage_release as sr
    from tests import test_staging as ts

    text = (ROOT / "docs" / "PUBLISHING.md").read_text(encoding="utf-8")
    assert "`output/transliterations/coverage_matrix.csv`" in text  # PUBLISHING promises it
    reports = dict(sr.REPORTS)
    reports["voynich-transliterations"] = tuple(
        n for n in reports["voynich-transliterations"] if n != "coverage_matrix.csv"
    )
    monkeypatch.setattr(sr, "REPORTS", reports)
    staged = tmp_path / "staged"
    sr.stage(staged)
    assert not (staged / "voynich-transliterations" / "coverage_matrix.csv").exists()
    caught = False
    try:
        ts.test_every_repository_stages_its_build_reports(staged)
    except AssertionError:
        caught = True
    assert caught, "the predicate passed while a promised report was not staged"
