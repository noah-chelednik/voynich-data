# tests/regressions/966f955a/test_reach_2.py
"""Claim 2 (a line the parser does not read as a locus is still compared): a line not in the file's encoding is one
the parser reports and does not read as a locus, but `_loci` decodes the whole file at once, so the diff raises and
compares nothing."""
from pathlib import Path

import pytest

from parsers import IVTFFParser
from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_an_undecodable_line_is_compared_as_an_other_line(tmp_path):
    old = checks.SOURCES["ZL"].path.read_bytes()
    lines = old.split(b"\n")
    comment = next(i for i, line in enumerate(lines) if line.startswith(b"#") and i > 0)
    lines[comment] = lines[comment] + b" \xff"
    new = b"\n".join(lines)
    # the parser reads the file: the line is reported, not read as a locus
    path = tmp_path / "zl.txt"
    path.write_bytes(new)
    parser = IVTFFParser()
    list(parser.parse_file(path, encoding="utf-8"))
    assert any(w.line_number == comment + 1 for w in parser.warnings)
    try:
        diff = upstream.locus_diff(old, new).as_dict()
    except Exception as error:  # noqa: BLE001
        pytest.fail(f"the diff compared nothing: {type(error).__name__}: {error}")
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 1), diff
