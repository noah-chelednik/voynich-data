# tests/regressions/3d607506/test_finding_1.py
from pathlib import Path

import yaml

from vcat.sources import load_sources


def test_variant_dataset_declares_its_vcat_annotations():
    root = Path(__file__).resolve().parents[3]
    dataset = next(
        entry
        for entry in load_sources()["datasets"]
        if entry["name"] == "voynich-transliterations"
    )
    card_dir = root / dataset["card"]
    text = (card_dir / "README.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(text.split("---", 2)[1])
    configurations = {entry["config_name"] for entry in metadata["configs"]}

    assert {"locus_variants", "word_alignments"} <= configurations
    assert dataset["vcat_annotations"] is True
    assert metadata["license"] == "cc-by-4.0"
    assert "Creative Commons Attribution 4.0 International (CC-BY-4.0)" in (
        card_dir / "LICENSE"
    ).read_text(encoding="utf-8")
