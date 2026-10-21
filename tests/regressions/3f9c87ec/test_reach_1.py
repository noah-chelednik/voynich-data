# tests/regressions/3f9c87ec/test_reach_1.py
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_ci_checks import _skip_and_xfail_uses


def test_xfail_alone_fails_the_session(tmp_path):
    root = Path(__file__).resolve().parents[3]
    source = (
        "import pytest\n"
        "def test_probe():\n"
        "    getattr(pytest, 'xfail')('runtime probe')\n"
    )
    assert _skip_and_xfail_uses("tests/probe.py", source) == ([], [])

    shutil.copy2(root / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_probe.py").write_text(source, encoding="utf-8")

    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr
    assert "VCAT runs every test:" in output, output
    assert "was xfailed" in output, output
    assert result.returncode == pytest.ExitCode.TESTS_FAILED, output
