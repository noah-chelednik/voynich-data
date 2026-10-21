# tests/regressions/471ee619/test_finding_4.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_readme_license_keeps_source_fields_cc0():
    """docs/SOURCES_LICENSE.md: with VCAT annotations a dataset is cc-by-4.0, "the source-derived fields stay CC0-1.0"."""
    assert "source-derived fields stay CC0-1.0" in (ROOT / "docs" / "SOURCES_LICENSE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    data = next(ln for ln in readme.splitlines() if ln.startswith("- **Data:**"))
    para = readme[readme.index(data):readme.index("- **The cached source files**")]
    assert "CC0-1.0" in para.split("so all four datasets are CC-BY-4.0", 1)[-1]
