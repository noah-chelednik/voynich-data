# tests/regressions/cad4bcad/test_finding_3.py
import json
import re
from pathlib import Path


def test_documented_word_count_rule_holds_or_is_corrected():
    root = Path(__file__).resolve().parents[3]
    doc = (root / "docs/data_model.md").read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in (root / "output/eva_lines.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows
    mismatches = [
        row["line_id"]
        for row in rows
        if row["word_count"]
        != len([word for word in re.split(r"[.,]", row["text_clean"]) if word])
    ]
    unqualified_claims = [
        "`word_count` counts the units between `.` and `,` in `text_clean`",
        "| `word_count` | integer | units of `text_clean` separated by `.` or `,` |",
    ]
    still_stated = [claim for claim in unqualified_claims if claim in doc]
    assert not (mismatches and still_stated), (still_stated, mismatches)
