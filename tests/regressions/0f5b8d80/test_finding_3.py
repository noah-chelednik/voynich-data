# tests/regressions/0f5b8d80/test_finding_3.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_readme_quick_load_shows_every_published_repository():
    """docs/PUBLISHING.md publishes four Hub repositories; the README's Hugging Face load section must show each."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = re.search(r"^### Quick Load \(from Hugging Face\)\n(.*?)(?=^## )", readme, re.S | re.M).group(1)
    publishing = (ROOT / "docs" / "PUBLISHING.md").read_text(encoding="utf-8")
    repos = sorted(set(re.findall(r"^\| `Ched-ai/([\w-]+)`", publishing, re.M)))
    assert len(repos) == 4, repos
    missing = [r for r in repos if f'"Ched-ai/{r}"' not in section]
    assert missing == [], missing
