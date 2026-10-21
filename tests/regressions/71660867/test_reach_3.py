# tests/regressions/71660867/test_reach_3.py
from copy import deepcopy

import pytest

from tests import test_words as checks


def test_paragraph_predicates_reject_an_omitted_interior_line(monkeypatch):
    checks.test_paragraphs_are_the_source_s_marks()
    checks.test_labels_and_unmarked_lines_are_in_no_paragraph()

    lines = {line["line_id"]: line for line in checks.LINES}
    target = next(
        row
        for row in checks.WORDS
        if row["paragraph_id"] is not None
        and row["line_in_paragraph"] > 1
        and not {"<%>", "<$>"}.intersection(lines[row["line_id"]]["markers"])
    )
    paragraph_id = target["paragraph_id"]
    line_id = target["line_id"]
    position = target["line_in_paragraph"]
    changed = deepcopy(checks.WORDS)

    for row in changed:
        if row["paragraph_id"] != paragraph_id:
            continue
        if row["line_id"] == line_id:
            row["paragraph_id"] = None
            row["line_in_paragraph"] = None
            row["paragraph_initial"] = False
            row["paragraph_final"] = False
        elif row["line_in_paragraph"] > position:
            row["line_in_paragraph"] -= 1

    monkeypatch.setattr(checks, "WORDS", changed)

    with pytest.raises(AssertionError):
        checks.test_paragraphs_are_the_source_s_marks()
        checks.test_labels_and_unmarked_lines_are_in_no_paragraph()
