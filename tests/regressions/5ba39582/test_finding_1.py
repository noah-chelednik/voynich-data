# tests/regressions/5ba39582/test_finding_1.py
import shlex
from pathlib import Path

import yaml


def test_ci_does_not_exclude_reviewer_proofs():
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load(
        (root / ".github/workflows/ci.yml").read_text()
    )
    command = next(
        step["run"]
        for step in workflow["jobs"]["test"]["steps"]
        if step.get("name") == "Run tests"
    )
    argv = shlex.split(command)
    assert "pytest" in argv
    arguments = argv[argv.index("pytest") + 1:]
    assert not {"tests", "tests/"}.intersection(arguments), (
        "The positional tests/ path excludes tests/regressions; "
        "use pytest.ini's configured testpaths."
    )
