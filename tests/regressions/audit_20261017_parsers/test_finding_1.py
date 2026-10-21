from pathlib import Path
import shlex
import yaml

def test_ci_test_step_reaches_configured_proof_trees():
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    command = next(
        step["run"]
        for step in workflow["jobs"]["test"]["steps"]
        if step.get("name") == "Run tests"
    )
    args = shlex.split(command)
    explicit_test_roots = {
        arg.rstrip("/") for arg in args if arg.rstrip("/") in {"tests", "tests/regressions"}
    }
    assert not explicit_test_roots or "tests/regressions" in explicit_test_roots
