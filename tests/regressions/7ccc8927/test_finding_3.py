# tests/regressions/7ccc8927/test_finding_3.py
import json
from collections import Counter

import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize(
    ("field", "row_field"),
    [
        ("pages_by_language", "currier_language"),
        ("pages_by_section", "section"),
    ],
)
def test_page_distributions_are_not_described_as_row_totals(field, row_field):
    report = json.loads(
        (checks.OUTPUT / "eva_lines_build_report.json").read_text(
            encoding="utf-8"
        )
    )
    rows = [
        json.loads(line)
        for line in (checks.OUTPUT / "eva_lines.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows
    row_totals = dict(Counter(row[row_field] or "unknown" for row in rows))
    table = checks.tables(
        checks.section("The build report (`output/eva_lines_build_report.json`)")
    )[0]
    description = next(
        cells[-1] for cells in table if f"`{field}`" in cells[0]
    )
    assert (
        report[field] == row_totals
        or "totals over the rows" not in description
    ), (field, description, report[field], row_totals)
