# tests/regressions/660862e9/test_reach_1.py
"""Claim 1 (B-114): a quire's total_lines is checked only against the candidate's own pages table, whose per-page
line_count no check ties to the source. Moving one line from a qA page to a qB page in pages.jsonl, and the same line
between the two quires' total_lines, leaves every report total unchanged and is accepted by both validators: the
quires' line counts are no longer their pages' (the source has the committed counts)."""
from tests.regressions.audit_20261018_validators_r3 import test_findings as checks


def test_quire_lines_moved_with_their_pages_line_counts_are_refused():
    out = checks.OUT
    committed = checks.rows(out / "metadata/pages.jsonl")
    pages = checks.rows(out / "metadata/pages.jsonl")
    quires = checks.rows(out / "metadata/quires.jsonl")
    a = next(p for p in pages if p["quire_id"] == "qA")
    b = next(p for p in pages if p["quire_id"] == "qB" and p["line_count"] > 0)
    a["line_count"] += 1
    b["line_count"] -= 1
    for q in quires:
        if q["quire_id"] == "qA":
            q["total_lines"] += 1
        if q["quire_id"] == "qB":
            q["total_lines"] -= 1
    # the candidate's quire and page line counts are no longer the committed build's, which the builder read from the
    # source
    assert pages != committed
    with checks.candidate(tables={"pages": pages, "quires": quires}):
        actual = checks.decisions()
    assert actual == (False, False), actual
