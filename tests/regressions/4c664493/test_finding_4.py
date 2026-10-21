# tests/regressions/4c664493/test_finding_4.py
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

#: who transliterated each source, as data_sources/sources.yaml names it
TRANSLITERATORS = {
    "IT": "Takahashi",
    "IT2a": "Takahashi",
    "CD": "Currier",
    "FG": "First Study Group",
    "GC": "Claston",
    "VT": "Takahashi",
    "LSI": "Stolfi",
}


def test_the_eva_card_names_the_transliterators_its_license_tells_users_to_cite():
    registry = yaml.safe_load((ROOT / "data_sources" / "sources.yaml").read_text(encoding="utf-8"))
    eva = next(d for d in registry["datasets"] if d["name"] == "voynich-eva")
    license_text = (ROOT / "huggingface" / "voynich-eva" / "LICENSE").read_text(encoding="utf-8")
    assert "transliterators named in the dataset card" in license_text
    card = (ROOT / "huggingface" / "voynich-eva" / "README.md").read_text(encoding="utf-8")
    citation = card.split("## Citation", 1)[1]
    missing = sorted(
        s for s in eva["sources"] if s in TRANSLITERATORS and TRANSLITERATORS[s] not in citation
    )
    assert missing == []
