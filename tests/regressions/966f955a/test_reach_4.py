# tests/regressions/966f955a/test_reach_4.py
"""Claim 3 (changed with its diff): a served file with one line not in its encoding is reported changed with no diff
(`diff_error`), though the parser reads it and reports that one line."""
from pathlib import Path

from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_a_changed_source_with_an_undecodable_line_has_its_diff():
    old = checks.SOURCES["ZL"].path.read_bytes()
    lines = old.split(b"\n")
    comment = next(i for i, line in enumerate(lines) if line.startswith(b"#") and i > 0)
    lines[comment] = lines[comment] + b" \xff"
    results = {r["id"]: r for r in upstream.check_upstream(checks.served({"ZL": b"\n".join(lines)}))}
    assert results["ZL"]["status"] == "changed"
    assert "diff" in results["ZL"], f"changed without its diff: {results['ZL'].get('diff_error')}"
