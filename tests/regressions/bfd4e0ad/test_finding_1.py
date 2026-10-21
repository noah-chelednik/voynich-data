# tests/regressions/bfd4e0ad/test_finding_1.py
"""Claim 2: "every other line added or removed, a repeated or moved one too". Two comment lines of ZL that lie in one
gap between loci (after the <f1v> header: "# herbal", "# Currier's language A, hand 1") swapped: the parser attaches
them to f1v.1 in the other order, so the data differs, but the diff names nothing: no locus, no other line, nothing
moved. The issue body of such a change reads all zeros."""
from pathlib import Path

from parsers import IVTFFParser
from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_two_comment_lines_swapped_in_one_gap_are_named(tmp_path):
    old_path = checks.SOURCES["ZL"].path
    old = old_path.read_bytes()
    lines = old.split(b"\n")
    header = next(i for i, line in enumerate(lines) if line.startswith(b"<f1v>"))
    a, b = header + 1, header + 2
    assert lines[a].startswith(b"#") and lines[b].startswith(b"#") and lines[a] != lines[b]
    lines[a], lines[b] = lines[b], lines[a]
    new = b"\n".join(lines)
    assert new != old
    edited = tmp_path / "zl.txt"
    edited.write_bytes(new)

    def comments(path: Path) -> list[str]:
        page = next(p for p in IVTFFParser().parse_file(path, encoding="utf-8") if p.page_id == "f1v")
        return page.comments + [c for locus in page.loci for c in locus.comments]

    # positive control: the data differs (the comments come out in another order)
    assert comments(old_path) != comments(edited)
    diff = upstream.locus_diff(old, new).as_dict()
    named = (
        diff["added"] or diff["removed"] or diff["changed"] or diff["moved"]
        or diff["other_lines_added"] or diff["other_lines_removed"]
    )
    assert named, diff
