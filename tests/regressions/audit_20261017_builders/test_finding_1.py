# tests/regressions/audit_20261017_builders/test_finding_1.py
import importlib
import shlex
from pathlib import Path
from unittest.mock import patch

import yaml


def test_ci_builder_smoke_step_runs_checks():
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load(
        (root / ".github/workflows/ci.yml").read_text()
    )
    step = next(
        s for s in workflow["jobs"]["smoke-build"]["steps"]
        if s.get("name") == "Run EVA builder smoke test"
    )
    argv = shlex.split(step["run"])
    module = importlib.import_module("builders.build_eva_lines")

    if argv[1] == "-c":
        with patch.object(
            module, "build_eva_lines", return_value=([], None)
        ) as build, patch.object(
            module, "run_smoke_test", return_value=True
        ) as smoke:
            exec(argv[2], {})
        assert build.called
        assert smoke.called
    else:
        assert argv[1:3] == ["-m", "builders.build_eva_lines"]
        assert "--smoke-test" in argv
