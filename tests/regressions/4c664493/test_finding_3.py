# tests/regressions/4c664493/test_finding_3.py
import subprocess

from tests import test_staging as checks


def test_the_0_2_3_predicate_runs_in_a_clone_without_a_local_main(monkeypatch):
    """CI (`.github/workflows/ci.yml`, actions/checkout@v4, fetch-depth 1) checks out only the pushed ref: no local
    `main`. The 0.2.3 configurations are a fixed historical fact and must be checkable from the committed tree."""
    real = subprocess.run

    def single_branch_clone(args, *rest, **kwargs):
        if (
            isinstance(args, (list, tuple))
            and args
            and args[0] == "git"
            and any(str(a) == "main" or str(a).startswith("main:") for a in args)
        ):
            empty = "" if kwargs.get("text") else b""
            return subprocess.CompletedProcess(args, 128, stdout=empty, stderr=empty)
        return real(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", single_branch_clone)
    checks.test_the_published_configurations_are_the_0_2_3_cards()
