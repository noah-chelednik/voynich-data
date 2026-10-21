# tests/regressions/966f955a/test_reach_3.py
"""Claim 2 (every other line compared): `_loci` numbers lines with `str.splitlines`, which also breaks at form feed,
NEL, U+2028 and others, while the parser breaks only at CR/LF; one such character shifts every later line, so locus
lines are compared as other lines and the lines before them drop out of both comparisons."""
from pathlib import Path

from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_a_form_feed_in_a_comment_changes_one_other_line():
    old = checks.SOURCES["ZL"].path.read_bytes()
    lines = old.decode("utf-8").split("\n")
    comment = next(i for i, line in enumerate(lines) if line.startswith("#") and i > 0)
    lines[comment] = lines[comment] + "\x0c"
    new = "\n".join(lines).encode("utf-8")
    diff = upstream.locus_diff(old, new).as_dict()
    assert (diff["added"], diff["removed"], diff["changed"]) == ([], [], [])
    # one comment line changed: one other line removed, one added
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 1), (
        diff["other_lines_added"],
        diff["other_lines_removed"],
    )
