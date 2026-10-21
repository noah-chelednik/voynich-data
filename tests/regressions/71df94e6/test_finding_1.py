# tests/regressions/71df94e6/test_finding_1.py
"""Claim 1 (B-114): the quire check takes each quire's members from the source's headers, never from the pages table,
and nothing compares a metadata page's quire_id with its header's $Q. A pages table that moves f1r (header $Q=A) into
qB, its quire_id and quire_letter changed and every other table left as built, is accepted by both validators: qA's
published membership (folio_ids f1..f8, page_count 16) is no longer the pages that name qA in pages.jsonl (15), and qB's
is not the 15 that name qB."""
from tests.regressions.audit_20261018_validators_r3 import test_findings as checks


def test_a_page_moved_to_another_quire_in_the_pages_table_is_refused():
    out = checks.OUT
    pages = checks.rows(out / "metadata/pages.jsonl")
    quires = {q["quire_id"]: q for q in checks.rows(out / "metadata/quires.jsonl")}
    page = next(p for p in pages if p["page_id"] == "f1r")
    assert page["quire_id"] == "qA"
    page["quire_id"], page["quire_letter"] = "qB", "B"
    # the quires table now disagrees with the pages table on which pages each quire holds
    naming_qa = sum(1 for p in pages if p["quire_id"] == "qA")
    assert naming_qa != quires["qA"]["page_count"], (naming_qa, quires["qA"]["page_count"])
    with checks.candidate(tables={"pages": pages}):
        actual = checks.decisions()
    assert actual == (False, False), actual
