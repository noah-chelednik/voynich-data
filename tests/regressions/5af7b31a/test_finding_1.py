# tests/regressions/5af7b31a/test_finding_1.py
"""Claims 2 and 4: two ZL files that differ only in the order of two locus lines (f1r.2 and f1r.3 swapped) hold
different data (the parser emits the page's loci in another order), but the diff names nothing and the diff command
exits 0, the code for files that do not differ."""
from pathlib import Path

from parsers import IVTFFParser
from scripts import source_diff as command
from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def test_two_files_differing_in_line_order_exit_1(tmp_path):
    old = checks.SOURCES["ZL"].path
    lines = old.read_bytes().split(b"\n")
    two = next(i for i, line in enumerate(lines) if line.startswith(b"<f1r.2,"))
    assert lines[two + 1].startswith(b"<f1r.3,")
    lines[two], lines[two + 1] = lines[two + 1], lines[two]
    edited = tmp_path / "zl.txt"
    edited.write_bytes(b"\n".join(lines))
    assert edited.read_bytes() != old.read_bytes()

    def order(path: Path) -> list[int]:
        page = next(p for p in IVTFFParser().parse_file(path, encoding="utf-8") if p.page_id == "f1r")
        return [locus.locus_number for locus in page.loci]

    # the data differs: the page's loci come out in another order
    assert order(old)[:3] != order(edited)[:3]
    diff = upstream.locus_diff(old.read_bytes(), edited.read_bytes()).as_dict()
    assert command.main([str(old), str(edited)]) == 1, diff
