"""
`docs/decisions.md` is the decision log the README links (AD2 F2, B-079): an entry whose contract the data model replaced is
marked Superseded or Revised, naming what replaced it, so no Active entry contradicts the current contract.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")


def entry(number: int) -> str:
    match = re.search(rf"^## Decision {number}: .*?(?=^## )", LOG, re.S | re.M)
    assert match, number
    return match.group(0)


def status(number: int) -> str:
    match = re.search(r"^\*\*Status\*\*: (\w+)", entry(number), re.M)
    assert match, number
    return match.group(1)


def test_the_stolfi_comparison_policy_is_superseded():
    assert status(2) == "Superseded"
    assert "IT" in entry(2) and "docs/data_model.md" in entry(2)


def test_the_text_field_contract_is_revised_to_the_data_model():
    assert status(4) == "Revised"
    assert (
        "`text_raw`" in entry(4) and "analysis-v1" in entry(4) and "docs/data_model.md" in entry(4)
    )


def test_no_active_entry_names_the_raw_text_field_as_text():
    """An Active entry may not call `text` the raw field: `text_raw` is (docs/data_model.md)."""
    for number in map(int, re.findall(r"^## Decision (\d+):", LOG, re.M)):
        if status(number) == "Active":
            assert "`text` (raw)" not in entry(number), number
            assert "raw text with markup in `text`" not in entry(number), number
