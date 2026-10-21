# tests/regressions/1c53841b/test_reach_2.py
import copy
import json
from statistics import median

import pytest

from builders.build_mismatch_index import MismatchRecord, build_report
from tests import test_mismatch_index as checks


def test_report_uses_the_median_for_an_even_population():
    records = [
        MismatchRecord(
            page_id="f1r",
            line_number=number,
            line_id=f"f1r:{number}",
            status="different",
            comparison_profile="analysis-v1",
            similarity_score=score,
        )
        for number, score in enumerate((0.2, 0.8), start=1)
    ]
    report = build_report(records, {})
    scores = [record.similarity_score for record in records]
    assert report["different_similarity"]["median"] == median(scores)


@pytest.mark.parametrize("field", ["total_lines", "different_rate"])
def test_report_predicate_rejects_wrong_summary_fields(field):
    rows = [
        json.loads(line)
        for line in (checks.OUTPUT / "mismatch_index.jsonl").read_text().splitlines()
    ]
    report = json.loads((checks.OUTPUT / "mismatch_report.json").read_text())
    checks.test_report_counts_are_the_rows((rows, report))

    changed = copy.deepcopy(report)
    changed[field] += 1
    with pytest.raises(AssertionError):
        checks.test_report_counts_are_the_rows((rows, changed))
