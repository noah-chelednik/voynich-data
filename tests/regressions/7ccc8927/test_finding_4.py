# tests/regressions/7ccc8927/test_finding_4.py
import re
import shlex
from pathlib import Path


def test_ci_does_not_collect_only_the_primary_test_tree():
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    commands = re.findall(r"(?m)^\s*run:\s*(.*\bpytest\b.*)$", workflow)
    assert commands
    for command in commands:
        words = shlex.split(command)
        arguments = words[words.index("pytest") + 1 :]
        primary_only = any(word.rstrip("/") == "tests" for word in arguments)
        includes_proofs = any(
            word.rstrip("/") == "tests/regressions" for word in arguments
        )
        assert not primary_only or includes_proofs, command
