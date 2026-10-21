# tests/regressions/9db38e3c/test_finding_1.py
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_release_cards_do_not_call_their_schema_pre_1_0():
    """At version 1.0.0 no card published by the release may say its schema is pre-1.0 and may change before 1.0."""
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert int(version.split(".")[0]) >= 1
    stale = []
    for card in sorted((ROOT / "huggingface").glob("*/README.md")):
        for number, line in enumerate(card.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(r"Pre-1\.0 schema|before the 1\.0 release", line):
                stale.append(f"{card.relative_to(ROOT)}:{number}")
    assert stale == [], stale
