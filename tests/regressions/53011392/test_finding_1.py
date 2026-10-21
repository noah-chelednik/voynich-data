# tests/regressions/53011392/test_finding_1.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_decision_5_says_the_cards_state_stability_only_if_every_card_does():
    """docs/decisions.md's Decision 5 status says at 1.0.0 'the schema is stable under STABILITY.md, and the cards say so'.
    Every published card (docs/PUBLISHING.md's repositories) must then state the stable schema under STABILITY.md."""
    text = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    block = re.search(r"^## Decision 5:.*?(?=^## Decision 6:|\Z)", text, re.S | re.M).group(0)
    status = re.search(r"^\*\*Status\*\*:(.*)$", block, re.M).group(1)
    if "the cards say so" not in status:
        return
    publishing = (ROOT / "docs" / "PUBLISHING.md").read_text(encoding="utf-8")
    repos = sorted(set(re.findall(r"^\| `Ched-ai/([\w-]+)`", publishing, re.M)))
    assert len(repos) == 4, repos
    silent = []
    for repo in repos:
        card = (ROOT / "huggingface" / repo / "README.md").read_text(encoding="utf-8")
        if not re.search(r"stable (schema|from 1\.0\.0)", card, re.I):
            silent.append(repo)
    assert silent == [], silent
