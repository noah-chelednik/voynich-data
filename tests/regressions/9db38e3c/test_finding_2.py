# tests/regressions/9db38e3c/test_finding_2.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_readme_of_release_1_0_0_does_not_say_the_hub_holds_0_2_3():
    """The README says "This is release 1.0.0"; its Hub load section must not describe the Hub rows as 0.2.3's."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "This is release 1.0.0" in readme
    assert "the published 0.2.3 rows" not in readme
