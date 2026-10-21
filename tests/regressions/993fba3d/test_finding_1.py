# tests/regressions/993fba3d/test_finding_1.py
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _line_ids(name):
    path = ROOT / "output" / "transliterations" / name
    return {json.loads(ln)["line_id"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def test_sources_doc_vt_section_does_not_say_vt_differs_only_in_unreadable_characters():
    """docs/sources.md's dependency table now says VT lacks some of IT2a's loci, but its VT section (the provenance the
    transliterations card sends readers to) still says VT differs from IT2a "only in details related to unreadable
    characters", with nothing qualifying it; the data hold IT2a loci VT lacks."""
    assert _line_ids("it2a.jsonl") - _line_ids("vt.jsonl")  # the fact the card and the table now state
    doc = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    vt = re.search(r"^### VT:.*?(?=^### )", doc, re.S | re.M).group(0)
    assert "only in details related to unreadable" not in vt or "loci" in vt, vt
