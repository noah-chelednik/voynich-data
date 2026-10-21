# tests/regressions/bef641e7/test_reach_3.py
import json

import pytest

from tests import test_layers as checks
from vcat import layers as vl


@pytest.mark.parametrize(
    ("table", "field"),
    [
        ("pages", "quire_letter"),
        ("folios", "quire_id"),
        ("quires", "quire_letter"),
        ("bifolia", "quire_id"),
        ("quires", "is_complete"),
    ],
)
def test_published_classification_has_an_attributed_layer(table, field):
    checks.test_every_classifying_field_is_attributed()

    path = checks.OUTPUT / "metadata" / f"{table}.jsonl"
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows and all(field in row for row in rows)

    qualified = f"voynich-manuscript-metadata:{table}.{field}"
    assert vl.layer_of(qualified) is not None, qualified
