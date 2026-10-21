# tests/regressions/d4385eb4/test_reach_6.py
import pytest

from tests import test_layers as layer_gate
from tests import test_sources as source_gate


def test_claimed_license_predicates_reject_card_registry_disagreement(
    tmp_path, monkeypatch
):
    dataset = next(
        entry
        for entry in source_gate.SOURCES["datasets"]
        if entry["name"] == "voynich-eva"
    )
    assert source_gate.expected_card_license(dataset) == "cc-by-4.0"

    card = tmp_path / dataset["card"]
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\nlicense: cc0-1.0\nlicense_link: LICENSE\n---\n",
        encoding="utf-8",
    )
    (card / "LICENSE").write_text(
        source_gate.LICENSE_NAMES["cc0-1.0"] + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(source_gate, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        layer_gate.test_a_dataset_has_vcat_annotations_exactly_when_a_vcat_layer_fills_it()
        source_gate.test_each_card_license_file_names_the_card_license(dataset)
