# tests/regressions/f6661c36/test_finding_2.py
import ast
import json
import re
from pathlib import Path

from validators.schema import validate_mismatch_index

ROOT = next(
    p for p in Path(__file__).resolve().parents
    if (p / "pyproject.toml").is_file()
)
CARD = ROOT / "huggingface/voynich-transcription-mismatch/README.md"


def test_documented_disagreement_filter_selects_current_rows():
    block = re.search(
        r"### Finding Uncertain Lines\s+```python\n(.*?)```",
        CARD.read_text(),
        re.S,
    )
    assert block is not None
    tree = ast.parse(block.group(1))
    assignment = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "mismatches"
            for target in node.targets
        )
    )
    expression = next(
        node for node in ast.walk(assignment.value)
        if isinstance(node, ast.Lambda)
    )
    predicate = eval(
        compile(ast.Expression(expression), "<dataset card>", "eval"),
        {"__builtins__": {}},
    )
    rows = [
        json.loads(line)
        for line in (ROOT / "output/mismatch_index.jsonl").read_text().splitlines()
    ]
    expected = {
        row["line_id"] for row in rows if row["status"] == "different"
    }
    assert expected, "Positive control: the data must contain disagreements"
    assert {
        row["line_id"] for row in rows if predicate(row)
    } == expected


def test_documented_data_instance_conforms_to_current_schema():
    block = re.search(
        r"### Data Instance\s+```json\n(.*?)```",
        CARD.read_text(),
        re.S,
    )
    assert block is not None
    valid, errors = validate_mismatch_index([json.loads(block.group(1))])
    assert valid, errors
