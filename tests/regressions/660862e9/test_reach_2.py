# tests/regressions/660862e9/test_reach_2.py
"""Claim 1 (B-114): a quire's sections are checked only against the candidate's own pages table, whose per-page
section no check ties to the source (pages_by_section is counted from the same table). Swapping the sections of a qA
page and a herbal_b page of another quire, with both quires' sections recomputed, is accepted by both validators."""
from tests.regressions.audit_20261018_validators_r3 import test_findings as checks


def test_quire_sections_swapped_with_their_pages_sections_are_refused():
    out = checks.OUT
    pages = checks.rows(out / "metadata/pages.jsonl")
    quires = checks.rows(out / "metadata/quires.jsonl")
    a = next(p for p in pages if p["quire_id"] == "qA" and p["section"]["value"] == "herbal_a")
    c = next(p for p in pages if p["quire_id"] != "qA" and p["section"]["value"] == "herbal_b")
    a["section"]["value"], c["section"]["value"] = "herbal_b", "herbal_a"
    by_quire = {}
    for p in pages:
        by_quire.setdefault(p["quire_id"], set()).add(p["section"]["value"])
    before = {q["quire_id"]: q["sections"] for q in quires}
    for q in quires:
        q["sections"] = sorted(by_quire[q["quire_id"]])
    assert before["qA"] != next(q["sections"] for q in quires if q["quire_id"] == "qA")
    with checks.candidate(tables={"pages": pages, "quires": quires}):
        actual = checks.decisions()
    assert actual == (False, False), actual
