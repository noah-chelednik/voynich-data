# tests/regressions/471ee619/test_finding_3.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_changelog_unreleased_link_starts_at_the_last_release():
    """The [Unreleased] compare link names the last release as its base; the CHANGELOG's own headings and summary (and
    pyproject.toml) make that 0.2.3, while the link still compares from v0.2.1."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    assert f"## [{version}]" in text  # the release has its entry
    link = re.search(r"^\[Unreleased\]: (\S+)$", text, re.M).group(1)
    assert link.endswith(f"/compare/v{version}...HEAD"), link
