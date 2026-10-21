# tests/regressions/5af7b31a/test_finding_2.py
"""Claims 4 and 5: "4 when the check itself failed". A failure of the check outside `main()` (its import of
`vcat.upstream`, at module level, outside the try) exits 1, the code of a change, so the workflow runs the issue step;
and a check that ends with any code outside 0-4 (killed: 137) fails no step, so the run passes."""
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from tests import test_upstream as checks

ROOT = Path(__file__).resolve().parents[3]


def test_a_check_that_fails_on_import_exits_4(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "check_upstream.py", tmp_path / "scripts" / "check_upstream.py")
    (tmp_path / "vcat").mkdir()
    (tmp_path / "vcat" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "vcat" / "upstream.py").write_text(
        "raise ImportError('No module named yaml')\n", encoding="utf-8"
    )
    done = subprocess.run(
        [sys.executable, "-I", str(tmp_path / "scripts" / "check_upstream.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "ImportError" in done.stderr, done.stderr
    assert done.returncode == 4, f"the check failed and exited {done.returncode}"


def runs(condition: str | None, status: str) -> bool:
    if condition is None:
        return True
    expr = (
        condition.replace("steps.check.outputs.status", repr(status))
        .replace("&&", " and ")
        .replace("||", " or ")
        .replace("always()", "True")
        .replace("success()", "True")
        .replace("failure()", "False")
    )
    expr = expr.replace("!=", "\x00").replace("!", " not ").replace("\x00", "!=")
    return bool(eval(expr))  # noqa: S307 - the workflow's own conditions


def test_a_check_killed_with_an_unexpected_code_fails_the_run():
    workflow = yaml.safe_load(checks.WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["check"]["steps"]
    check = next(s for s in steps if "scripts/check_upstream.py" in s.get("run", ""))
    after = steps[steps.index(check) + 1 :]
    failing = [
        s for s in after
        if runs(s.get("if"), "137") and "exit" in s.get("run", "") and "exit 0" not in s.get("run", "")
    ]
    assert failing, "the check ended with 137 (killed) and no step that runs fails the job"
