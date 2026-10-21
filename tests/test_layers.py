"""
The attribution of the interpretive layers (roadmap item 2.8): `data_sources/layers.yaml`, published as the metadata
dataset's `layers` table, against the datasets' own fields, the registry's dataset licenses and the rows.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from vcat import layers as vl
from vcat.sources import load_sources

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
LAYERS = vl.load_layers()


def dataset_fields(dataset: str) -> set[str]:
    """Every field a dataset's rows hold, as `<dataset>:<field>` (metadata fields as `<table>.<field>`)."""
    if dataset == "voynich-eva":
        schema = json.loads((ROOT / "schemas" / "transcription_lines.schema.json").read_text())
        # and its word level (roadmap item 2.6), as `words.<field>`
        words = json.loads((ROOT / "schemas" / "eva_words.schema.json").read_text())
        return {f"{dataset}:{name}" for name in schema["properties"]} | {
            f"{dataset}:words.{name}" for name in words["properties"]
        }
    if dataset == "voynich-transcription-mismatch":
        schema = json.loads((ROOT / "schemas" / "mismatch_index.schema.json").read_text())
        return {f"{dataset}:{name}" for name in schema["properties"]}
    if dataset == "voynich-transliterations":
        # the per-source configs and the variant tables (roadmap item 2.7), as `<table>.<field>` for the latter
        schemas = ROOT / "schemas"
        source = json.loads((schemas / "transliteration_loci.schema.json").read_text())
        fields = {f"{dataset}:{name}" for name in source["properties"]}
        for table in ("locus_variants", "word_alignments"):
            spec = json.loads((schemas / f"{table}.schema.json").read_text())
            fields |= {f"{dataset}:{table}.{name}" for name in spec["properties"]}
        return fields
    if dataset != "voynich-manuscript-metadata":
        return set()  # no other dataset: a layer naming one names no field (reach bef641e7 gap 2)
    fields = set()
    for path in sorted((OUTPUT / "metadata").glob("*.jsonl")):
        row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        fields |= {f"{dataset}:{path.stem}.{name}" for name in row}
    return fields


def test_every_layer_field_is_a_field_of_its_dataset():
    for layer in LAYERS:
        for field in layer["fields"]:
            dataset = field.split(":", 1)[0]
            assert field in dataset_fields(dataset), (layer["layer"], field)


#: The fields of the datasets that record a classification, not the text: each must be in a layer (roadmap item 2.8)
CLASSIFYING = {
    "voynich-transliterations": {
        "locus_variants.agreement",
        "locus_variants.distinct_readings",
        "locus_variants.majority_baseline",
        "word_alignments.frame_reader",
        "word_alignments.operations",
        "word_alignments.matches",
        "word_alignments.word_agreement",
    },
    "voynich-eva": {
        "section",
        "illustration_type",
        "hand",
        "currier_language",
        "quire",
        "words.section",
        "words.hand",
        "words.currier_language",
        "words.quire",
    },
    "voynich-manuscript-metadata": {
        "pages.section",
        "page_canvases.canvas_id",
        "page_canvases.coverage",
        "pages.illustration_type",
        "pages.hand",
        "pages.currier_language",
        "pages.quire_id",
        "pages.quire_letter",
        "pages.page_in_quire",
        "pages.is_missing",
        "pages.is_foldout_panel",
        "folios.is_foldout",
        "bifolia.is_complete",
        "folios.quire_id",
        "folios.is_missing",
        "quires.quire_letter",
        "quires.is_complete",
        "bifolia.quire_id",
        "folios.section",
        "folios.currier_language",
        "quires.sections",
        "bifolia.bifolio_number",
        "page_orders.order",
    },
    "voynich-transcription-mismatch": {"status", "similarity_score"},
}


def test_every_classifying_field_is_attributed():
    attributed = {f for layer in LAYERS for f in layer["fields"]}
    for dataset, fields in CLASSIFYING.items():
        for field in fields:
            assert f"{dataset}:{field}" in attributed, f"{dataset}:{field}"


def test_a_dataset_has_vcat_annotations_exactly_when_a_vcat_layer_fills_it():
    """The registry's dataset licenses follow from the layers: VCAT's judgements make a dataset's card CC-BY-4.0."""
    vcat = {
        f.split(":", 1)[0] for layer in LAYERS if layer["kind"] == "vcat" for f in layer["fields"]
    }
    # `voynich-eva` folds every other dataset's tables in as configurations (roadmap item 2.9), so it holds VCAT's
    # annotations exactly when a dataset it folds does
    from builders.stage_release import EVA_CONFIGS

    folded = {
        "metadata/": "voynich-manuscript-metadata",
        "mismatch_index": "voynich-transcription-mismatch",
        "transliterations/": "voynich-transliterations",
    }
    builds = [build for _path, build, _what in EVA_CONFIGS.values()]
    if any(folded[key] in vcat for key in folded if any(b.startswith(key) for b in builds)):
        vcat.add("voynich-eva")
    for dataset in load_sources()["datasets"]:
        assert dataset["vcat_annotations"] == (dataset["name"] in vcat), dataset["name"]


def test_each_kind_takes_its_license():
    for layer in LAYERS:
        assert layer["license"] == vl.LICENSE_OF_KIND[layer["kind"]], layer["layer"]
        assert str(layer["attribution"]).strip() and str(layer["source"]).strip()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda e: e.update(kind="consensus"), "kind"),
        (lambda e: e.update(license="CC0-1.0"), "license"),
        (lambda e: e.pop("attribution"), "lacks"),
    ],
)
def test_the_registry_refuses_a_malformed_layer(tmp_path: Path, change, message: str):
    data = yaml.safe_load(vl.LAYERS_YAML.read_text(encoding="utf-8"))
    entry = next(e for e in data["layers"] if e["kind"] == "vcat")
    change(entry)
    path = tmp_path / "layers.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        vl.load_layers(path)


def test_the_published_layers_are_the_registry():
    rows = [
        json.loads(line) for line in (OUTPUT / "metadata" / "layers.jsonl").read_text().splitlines()
    ]
    assert rows == LAYERS


def test_vcat_judgements_say_whose_they_are():
    """The metadata sections, VCAT's judgement, carry `attribution: vcat` in every row."""
    for stem in ("pages", "folios"):
        rows = [
            json.loads(line)
            for line in (OUTPUT / "metadata" / f"{stem}.jsonl").read_text().splitlines()
        ]
        assert {row["section"]["attribution"] for row in rows if row["section"]} == {"vcat"}, stem


def test_one_leaf_in_a_partial_source_is_not_a_loss():
    """Built from CD, which omits leaves the manuscript keeps, a one-leaf sheet claims no loss (B-106)."""
    from parsers import IVTFFParser
    from parsers.metadata_parser import extract_all_metadata
    from vcat.sources import source_file

    result = extract_all_metadata(list(IVTFFParser().parse_file(ROOT / source_file("CD"))))
    single = [b for b in result.bifolia if len(b.folio_ids) == 1]
    assert single
    for sheet in single:
        assert not sheet.is_complete
        assert all("lost" not in note for note in sheet.notes), sheet


@pytest.mark.parametrize("value", [1, 0, "false", ""])
def test_the_validators_refuse_a_completeness_that_is_not_boolean(tmp_path: Path, value):
    """`is_complete` is a Boolean; a string or an integer stored the same in both formats still fails (B-107)."""
    import shutil

    import pyarrow as pa
    import pyarrow.parquet as pq

    from validators.validate_phase1_outputs import check_metadata

    shutil.copytree(OUTPUT / "metadata", tmp_path / "output" / "metadata")
    meta = tmp_path / "output" / "metadata"
    rows = [json.loads(line) for line in (meta / "bifolia.jsonl").read_text().splitlines()]
    # every row the same type, so the Parquet can hold it: True and False become the value and its opposite
    opposite = {1: 0, 0: 1, "false": "", "": "false"}[value]
    changed = deepcopy(rows)
    for row in changed:
        row["is_complete"] = value if row["is_complete"] else opposite
    (meta / "bifolia.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in changed), encoding="utf-8"
    )
    pq.write_table(pa.Table.from_pylist(changed), meta / "bifolia.parquet")
    assert any("Boolean" in p or "lists" in p for p in check_metadata(tmp_path / "output"))
