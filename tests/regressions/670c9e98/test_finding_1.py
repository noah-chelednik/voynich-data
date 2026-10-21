# tests/regressions/670c9e98/test_finding_1.py
import re
import shlex
from pathlib import Path


def test_ci_reaches_the_reviewer_proof_tree():
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/ci.yml").read_text()
    commands = re.findall(
        r"^\s*run:\s*(.*\bpytest\b.*)$", workflow, re.MULTILINE
    )
    assert commands, "No pytest command found in CI"
    for command in commands:
        roots = {
            arg.rstrip("/")
            for arg in shlex.split(command)
            if arg.rstrip("/") in {"tests", "tests/regressions"}
        }
        assert not roots or "tests/regressions" in roots, command
