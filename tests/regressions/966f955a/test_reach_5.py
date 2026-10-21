# tests/regressions/966f955a/test_reach_5.py
"""Claim 4 (the diff command exits by whether the files differ): the whitespace between a locus identifier and its
text (the parser's `separator`, kept for the round trip) is in neither comparison, so two files that differ on a locus
line exit 0."""
from pathlib import Path

from scripts import source_diff as command
from tests import test_upstream as checks

ROOT = Path(__file__).resolve().parents[3]


def test_files_differing_in_a_locus_line_exit_1(tmp_path):
    old = checks.SOURCES["ZL"].path
    lines = old.read_bytes().decode("utf-8").split("\n")
    seven = next(i for i, line in enumerate(lines) if line.startswith("<f1r.7,"))
    ident, rest = lines[seven].split(">", 1)
    assert rest != rest.lstrip(" \t") and rest.lstrip(" \t")
    lines[seven] = ident + ">" + "  " + rest  # two spaces more before the text
    edited = tmp_path / "zl.txt"
    edited.write_bytes("\n".join(lines).encode("utf-8"))
    assert edited.read_bytes() != old.read_bytes()
    assert command.main([str(old), str(edited)]) == 1
