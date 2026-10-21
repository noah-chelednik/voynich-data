"""
The root `conftest.py` makes the no-skip, no-xfail policy hold at run time (DECISIONS Q56, AT4 F1): a probe suite using the
repository's conftest fails every test that skips or xfails, however it does so, and passes a test that runs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROBE = """
import unittest
import pytest

def test_runs():
    assert True

def test_skip_call():
    pytest.skip("x")

@pytest.mark.xfail(reason="x")
def test_xfail_marker():
    assert False

@pytest.mark.parametrize("value", [])
def test_empty_parameters(value):
    pass

class TestUnittest(unittest.TestCase):
    def test_skip_test(self):
        self.skipTest("x")

    @unittest.expectedFailure
    def test_expected_failure(self):
        self.fail("x")
"""


def test_skipped_and_xfailed_outcomes_fail(tmp_path: Path):
    shutil.copy2(ROOT / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "test_probe.py").write_text(PROBE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rA", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    out = result.stdout
    assert result.returncode != 0, out
    assert "PASSED test_probe.py::test_runs" in out, out
    for name in (
        "test_skip_call",
        "test_xfail_marker",
        "TestUnittest::test_skip_test",
        "TestUnittest::test_expected_failure",
    ):
        assert f"FAILED test_probe.py::{name}" in out, (name, out)
    # an empty parameter set fails collection under pytest.ini, and is a failure here at the latest
    assert "skipped" not in out.splitlines()[-1] and "xfailed" not in out.splitlines()[-1], out
