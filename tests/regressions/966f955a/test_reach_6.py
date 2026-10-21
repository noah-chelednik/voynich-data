# tests/regressions/966f955a/test_reach_6.py
"""Claim 5 (the workflow fails on an unreachable source): when one source changed and another is unreachable the check
exits 1, so only the issue step runs; the failing step is conditioned on exit 2 and the run passes."""
from pathlib import Path

import yaml

from scripts import check_upstream as command
from tests import test_upstream as checks
from vcat import upstream

ROOT = Path(__file__).resolve().parents[3]


def runs(step: dict, status: int) -> bool:
    condition = step.get("if")
    if condition is None or condition == "always()":
        return True
    prefix = "steps.check.outputs.status == "
    assert condition.startswith(prefix), condition
    return condition[len(prefix):] == f"'{status}'"


def test_an_unreachable_source_fails_the_run_even_when_another_changed(tmp_path, monkeypatch):
    new, _ = checks.edited_zl()
    fetcher = checks.served({"ZL": new}, down={"IT"})
    monkeypatch.setattr(command, "check_upstream", lambda: upstream.check_upstream(fetcher))
    status = command.main(["--report", str(tmp_path / "r.json"), "--markdown", str(tmp_path / "r.md")])
    results = {r["id"]: r["status"] for r in upstream.check_upstream(fetcher)}
    assert results["IT"] == "unreachable"
    workflow = yaml.safe_load(checks.WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["check"]["steps"]
    check = next(s for s in steps if "scripts/check_upstream.py" in s.get("run", ""))
    after = steps[steps.index(check) + 1 :]
    failing = [s for s in after if runs(s, status) and "exit 1" in s.get("run", "")]
    assert failing, f"IT is unreachable, the check exits {status}, and no step that runs fails the job"
