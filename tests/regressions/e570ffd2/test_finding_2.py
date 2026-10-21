# tests/regressions/e570ffd2/test_finding_2.py
"""Claim 4: the diff command exits "0 for the same bytes, 1 otherwise". A file with a repeated locus key, diffed
against itself (the same bytes), is refused by an uncaught ValueError, so Python exits 1: the exit code that means
"the files differ". A caller reading the exit status (the release's source diff report, Q95 (d)) cannot tell a
refusal from a difference."""
import subprocess
import sys
from pathlib import Path

from tests import test_upstream as checks

ROOT = Path(__file__).resolve().parents[3]


def test_a_refused_file_against_itself_does_not_exit_as_differing(tmp_path):
    lines = checks.zl_lines()
    seven = next(i for i, line in enumerate(lines) if line.startswith("<f1r.7,"))
    lines.insert(seven + 1, lines[seven])
    path = tmp_path / "repeated.txt"
    path.write_bytes("\n".join(lines).encode("utf-8"))
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "source_diff.py"), str(path), str(path)],
        capture_output=True,
        text=True,
    )
    assert "two loci" in done.stderr  # control: the refusal fired
    assert done.returncode not in (0, 1), done.returncode
