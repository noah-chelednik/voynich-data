# tests/regressions/9db38e3c/test_finding_7.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def test_stage_release_docstrings_name_the_reports():
    """The staging now copies build reports and stops on a missing one; its module and `stage` docstrings must say so."""
    from builders import stage_release as sr

    assert "report" in sr.__doc__.split("\n\n")[0]
    assert "report" in sr.stage.__doc__
