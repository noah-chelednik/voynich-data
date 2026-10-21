# tests/regressions/audit_20261017_tests_r3/test_findings.py
import subprocess
from pathlib import Path

import pytest

from tests.test_ci_checks import _skip_and_xfail_uses


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)


@pytest.mark.parametrize(
    "source",
    [
        (
            "import unittest\n"
            "class TestProbe(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_bad(self):\n"
            "        self.assertTrue(False)\n"
        ),
        (
            "from unittest import TestCase, expectedFailure\n"
            "class TestProbe(TestCase):\n"
            "    @expectedFailure\n"
            "    def test_bad(self):\n"
            "        self.assertTrue(False)\n"
        ),
    ],
)
def test_f1_unittest_expected_failure_is_rejected(source):
    control = (
        "import pytest\n"
        "@pytest.mark.xfail\n"
        "def test_bad():\n"
        "    assert False\n"
    )
    assert any(_skip_and_xfail_uses("tests/probe.py", control))
    assert any(_skip_and_xfail_uses("tests/probe.py", source)), source


@pytest.mark.parametrize("status", [1, 127])
def test_f2_release_test_failure_stops_packaging(status):
    script = (ROOT / "scripts/release_phase1.sh").read_text()
    stage = script.split("# Step 4: Run tests", 1)[1]
    stage = stage.split("# Step 5: Package", 1)[0]

    def run_stage(code):
        program = (
            "set -euo pipefail\n"
            "YELLOW=''\n"
            "NC=''\n"
            f"python() {{ return {code}; }}\n"
            + stage
            + "\nprintf '%s\\n' PACKAGING_REACHED\n"
        )
        return subprocess.run(
            ["bash", "-c", program],
            capture_output=True,
            text=True,
            check=False,
        )

    control = run_stage(0)
    assert control.returncode == 0, control.stderr
    assert "PACKAGING_REACHED" in control.stdout

    failed = run_stage(status)
    assert failed.returncode != 0, failed.stdout
    assert "PACKAGING_REACHED" not in failed.stdout
