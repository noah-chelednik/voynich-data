# tests/regressions/71df94e6/test_finding_2.py
"""A folio row's total_lines and section are compared with nothing: moving one line between two folios' total_lines
and giving f1 another section, every other table left as built, is accepted by both validators, though the folios'
lines are then not their pages' (which gate 5 ties to the source) and f1's section is not the documented range's."""
from tests.regressions.audit_20261018_validators_r3 import test_findings as checks


def test_folio_lines_and_section_not_their_pages_are_refused():
    out = checks.OUT
    folios = checks.rows(out / "metadata/folios.jsonl")
    pages = checks.rows(out / "metadata/pages.jsonl")
    f1 = next(f for f in folios if f["folio_id"] == "f1")
    f2 = next(f for f in folios if f["folio_id"] == "f2")
    assert f1["total_lines"] == sum(p["line_count"] for p in pages if p["folio_id"] == "f1")
    f1["total_lines"] += 1
    f2["total_lines"] -= 1
    f1["section"]["value"] = "recipes"
    with checks.candidate(tables={"folios": folios}):
        actual = checks.decisions()
    assert actual == (False, False), actual
