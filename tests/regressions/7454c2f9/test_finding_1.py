# tests/regressions/7454c2f9/test_finding_1.py
import json
from pathlib import Path

import pytest

from vcat.layers import layer_of


@pytest.mark.parametrize(
    ("table", "field"),
    [
        ("pages", "is_foldout_panel"),
        ("folios", "is_foldout"),
        ("bifolia", "is_complete"),
    ],
)
def test_published_classification_has_a_layer(table, field):
    root = Path(__file__).resolve().parents[3]
    path = root / "output" / "metadata" / f"{table}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows and all(field in row for row in rows)

    qualified = f"voynich-manuscript-metadata:{table}.{field}"
    assert layer_of(qualified) is not None, qualified
