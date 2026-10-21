# tests/regressions/471ee619/test_finding_2.py
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_metadata_card_page_id_examples_are_pages_of_the_dataset():
    """Gate 9 clause 7 replaces the nonexistent example f85v3 in the cards' rendered field tables; the metadata card's
    pages table still offers it, and the dataset it describes has no such page."""
    pages = {
        json.loads(ln)["page_id"]
        for ln in (ROOT / "output" / "metadata" / "pages.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }
    assert "f86v3" in pages and "f1r" in pages  # positive control
    card = (ROOT / "huggingface" / "voynich-manuscript-metadata" / "README.md").read_text(encoding="utf-8")
    row = next(ln for ln in card.splitlines() if ln.startswith("| `page_id` |"))
    examples = re.findall(r'"(f[^"]*)"', row)
    assert examples, row
    missing = [e for e in examples if e not in pages]
    assert not missing, f"example page ids not in the dataset: {missing}"
