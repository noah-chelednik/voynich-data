# tests/regressions/9db38e3c/test_finding_9.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_readme_bibtex_names_the_citation_author():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    family = re.search(r"family-names: (\S+)", cff).group(1)
    bib = re.search(r"```bibtex\n(.*?)```", readme, re.S).group(1)
    assert family in bib, bib
