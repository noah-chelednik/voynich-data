# tests/regressions/fc83f28e/test_finding_2.py
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_the_eva_section_is_described_one_way_wherever_it_is_described():
    """B-118 (clause 10): the schema now says the EVA `section` is a renaming of what the source states (the source's
    layer `section_name`), and asserts it is not called an interpretation. The EVA card's own field table renders that
    description; its Limitations and the data model's field table must not still tell users the opposite."""
    schema = json.loads(
        (ROOT / "schemas" / "transcription_lines.schema.json").read_text(encoding="utf-8")
    )
    assert "interpretation" not in schema["properties"]["section"]["description"]
    card = (ROOT / "huggingface" / "voynich-eva" / "README.md").read_text(encoding="utf-8")
    model = (ROOT / "docs" / "data_model.md").read_text(encoding="utf-8")
    model_row = next(line for line in model.splitlines() if line.startswith("| `section` |"))
    stale = [
        line
        for line in card.splitlines()
        if re.search(r"`section`", line) and "interpretation" in line
    ]
    assert stale == [], stale
    assert "interpretation" not in model_row, model_row
