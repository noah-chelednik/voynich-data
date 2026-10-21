# tests/regressions/7454c2f9/test_finding_7.py
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("relative", "superseded_claim"),
    [
        (
            "docs/data_model.md",
            "a sheet with one leaf lost its conjugate",
        ),
        (
            "huggingface/voynich-manuscript-metadata/README.md",
            "a sheet with one leaf lost its conjugate",
        ),
        (
            "docs/data_model.md",
            "like `section` in the EVA rows, they are interpretations "
            "and move to attributed layers in roadmap items 2.5 and 2.8.",
        ),
    ],
)
def test_current_docs_remove_superseded_interpretations(
    relative, superseded_claim
):
    root = Path(__file__).resolve().parents[3]
    text = " ".join((root / relative).read_text().split())
    assert superseded_claim not in text
