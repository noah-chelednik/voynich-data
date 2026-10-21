# tests/regressions/471ee619/test_finding_5.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _ids(name):
    path = ROOT / "output" / "transliterations" / name
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_sources_doc_dependency_table_matches_the_data():
    """docs/sources.md, to which the transliterations card sends readers for provenance, still says VT differs from IT2a
    only in unreadable characters and that LSI's C readings are CD's transliteration; the data say otherwise."""
    vt = {r["line_id"] for r in _ids("vt.jsonl")}
    it2a = {r["line_id"] for r in _ids("it2a.jsonl")}
    lsi_c = {r["line_id"] for r in _ids("lsi.jsonl") if r["transcriber"] == "C"}
    cd = {r["line_id"] for r in _ids("cd.jsonl")}
    assert it2a - vt and lsi_c - cd  # the facts the card now states
    doc = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    assert "differs from IT2a only in unreadable characters" not in doc
    assert "LSI's `C` readings are the same transliteration" not in doc
