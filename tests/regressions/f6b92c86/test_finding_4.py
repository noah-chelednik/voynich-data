# tests/regressions/f6b92c86/test_finding_4.py
import re
import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_ci_does_not_override_configured_testpaths():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    commands = re.findall(
        r"^\s*(?:run:\s*)?((?:python(?:3)?\s+-m\s+)?pytest\b[^\n]*)$",
        workflow,
        flags=re.MULTILINE,
    )
    assert commands, "No pytest invocation found in the workflow"

    for command in commands:
        arguments = shlex.split(command)
        pytest_arguments = arguments[arguments.index("pytest") + 1:]
        assert not {"tests", "tests/"}.intersection(pytest_arguments)
