# tests/regressions/a17b6e30/test_reach_4.py
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_all_row_glyph_predicate_detects_deleted_uppercase(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "reach_structured_predicates", ROOT / "tests" / "test_structured_layer.py"
    )
    assert spec is not None and spec.loader is not None
    predicates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predicates)

    output = ROOT / "output"
    predicates.test_text_clean_keeps_every_glyph_and_word_boundary(output)

    rows = predicates.rows_of(output)
    target = next(row for row in rows if row["line_id"] == "f57v:3")
    assert "I" in target["text_raw"]
    assert "I" in target["text_clean"]
    target["text_clean"] = target["text_clean"].replace("I", "")

    monkeypatch.setattr(predicates, "rows_of", lambda _: rows)
    with pytest.raises(AssertionError):
        predicates.test_text_clean_keeps_every_glyph_and_word_boundary(output)
