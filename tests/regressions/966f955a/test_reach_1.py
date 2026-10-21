# tests/regressions/966f955a/test_reach_1.py
"""Claim 2 (other lines changed): `locus_diff` counts other lines by set membership, so a line added that repeats a
line already in the file (or a removed copy of a repeated line) is counted as no change at all."""
from pathlib import Path

from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_a_repeated_other_line_added_is_counted():
    old = checks.SOURCES["ZL"].path.read_bytes()
    lines = old.decode("utf-8").split("\n")
    comment = next(i for i, line in enumerate(lines) if line.startswith("#") and i > 0)
    lines.insert(comment + 1, lines[comment])  # one comment line more, a copy of the one above it
    new = "\n".join(lines).encode("utf-8")
    assert new != old
    diff = upstream.locus_diff(old, new).as_dict()
    assert (diff["added"], diff["removed"], diff["changed"]) == ([], [], [])
    # the new file holds one line the old does not: an other line added
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 0), diff
