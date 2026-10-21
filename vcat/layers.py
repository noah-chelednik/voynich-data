"""The interpretive layers of the datasets and their attribution (roadmap item 2.8).

`data_sources/layers.yaml` lists every dataset field that records a classification rather than the transliterations'
text: the layer it belongs to, whether a source states it or VCAT judges it, where its values come from, whose
classification it is and its own license. The metadata builder publishes the table (the `layers` configuration); the suite
checks it against the datasets (tests/test_layers.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAYERS_YAML = ROOT / "data_sources" / "layers.yaml"

#: The fields of a layer's record, in the order the published table has them
LAYER_FIELDS = ("layer", "fields", "kind", "source", "attribution", "license")
#: What each field of a layer's record holds, as the card's field table states it
LAYER_FIELD_DESCRIPTIONS = {
    "layer": ("str", "The layer's name"),
    "fields": ("list[str]", "The dataset fields it fills, as `<dataset>:<field>`"),
    "kind": ("str", "`source` (a value a transliteration states) or `vcat` (VCAT's judgement)"),
    "source": ("str", "Where its values come from"),
    "attribution": ("str", "Whose classification it is"),
    "license": (
        "str",
        "The license of its values: `CC0-1.0` for a source's, `CC-BY-4.0` for VCAT's",
    ),
}
#: A layer is the source's (stated by a transliteration) or VCAT's (a judgement)
KINDS = ("source", "vcat")
#: The license of each kind: what a source states is CC0 by voynich.nu's statement; VCAT's judgements are CC-BY-4.0
LICENSE_OF_KIND = {"source": "CC0-1.0", "vcat": "CC-BY-4.0"}


#: The transliteration the published metadata is built from, which `{metadata_source}` in the registry names
PUBLISHED_METADATA_SOURCE = "ZL"
#: Whose hands a file's `$H` gives, which `{metadata_hands}` names: from IVTFF file version 1.7 the hands Lisa Fagin Davis
#: identified (IVTFF 2.0 Table 6); an older file defines `$H` itself, as Currier's hand (LSI, 1.5)
DAVIS_HANDS = "Lisa Fagin Davis's scribal hands, after Davis (2020)"
CURRIER_HANDS = "Prescott Currier's hands, as an IVTFF file older than version 1.7 defines `$H`"


def load_layers(
    path: Path | None = None,
    metadata_source: str = PUBLISHED_METADATA_SOURCE,
    metadata_hands: str = DAVIS_HANDS,
) -> list[dict[str, Any]]:
    """Every layer's record, in file order, for metadata built from `metadata_source` (a source id, or a file name for a
    file the registry does not list): `{metadata_source}` in a layer's source and attribution names it (review 7454c2f9
    finding 3). A record missing a field, of another kind, under a license its kind does not take, or named twice is an
    error."""
    path = LAYERS_YAML if path is None else path
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("layers"), list):
        raise ValueError(f"{path}: expected a mapping with a 'layers' list")
    records = []
    for entry in data["layers"]:
        missing = [name for name in LAYER_FIELDS if name not in entry]
        if missing:
            raise ValueError(f"{path}: layer {entry.get('layer')!r} lacks {missing}")
        for name in ("layer", "source", "attribution"):
            if not isinstance(entry[name], str) or not entry[name].strip():
                # a classification is attributed in words: null or empty is no attribution (reach bef641e7 gap 1)
                raise ValueError(
                    f"{path}: layer {entry.get('layer')!r} has no {name}: {entry[name]!r}"
                )
        if (
            not isinstance(entry["fields"], list)
            or not entry["fields"]
            or not all(isinstance(f, str) and f.strip() for f in entry["fields"])
        ):
            raise ValueError(
                f"{path}: layer {entry['layer']!r} names no fields: {entry['fields']!r}"
            )
        if entry["kind"] not in KINDS:
            raise ValueError(f"{path}: layer {entry['layer']!r} has kind {entry['kind']!r}")
        if entry["license"] != LICENSE_OF_KIND[entry["kind"]]:
            raise ValueError(
                f"{path}: layer {entry['layer']!r} ({entry['kind']}) has license {entry['license']!r}, "
                f"not {LICENSE_OF_KIND[entry['kind']]!r}"
            )
        record = {name: entry[name] for name in LAYER_FIELDS}
        for name in ("source", "attribution"):
            text = record[name].replace("{metadata_source}", metadata_source)
            record[name] = " ".join(text.replace("{metadata_hands}", metadata_hands).split())
        records.append(record)
    names = [r["layer"] for r in records]
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        raise ValueError(f"{path}: layers named more than once: {repeated}")
    fields = [f for r in records for f in r["fields"]]
    repeated = sorted({f for f in fields if fields.count(f) > 1})
    if repeated:
        raise ValueError(f"{path}: fields in more than one layer: {repeated}")
    return records


def metadata_source_name(source_path: str | Path) -> str:
    """The name a layer gives the transliteration at `source_path`: its registry id, else the file's name."""
    from vcat.sources import registered_source

    source = registered_source(source_path)
    return source.id if source else Path(source_path).name


def metadata_layer_names(source_path: str | Path) -> tuple[str, str]:
    """(metadata_source, metadata_hands): what the registry's placeholders name for metadata built from `source_path`: the transliteration
    (`metadata_source_name`) and whose hands its `$H` gives, by the format version its first line states (review
    69aa93cc finding 1). A file that cannot be read keeps the published default's hands."""
    import re

    from parsers.ivtff_parser import _format_older
    from vcat.sources import registered_source

    registered = registered_source(source_path)
    path = Path(source_path)
    if registered is not None and not path.is_file():
        path = registered.path
    hands = DAVIS_HANDS
    if path.is_file():
        with path.open("rb") as handle:
            first = handle.readline().decode("latin-1")
        version = re.match(r"#=IVTFF\s+\S+\s+(\d+\.\d+)", first)
        if version and _format_older(version.group(1), (1, 7)):
            hands = CURRIER_HANDS
    return metadata_source_name(source_path), hands


def layer_of(field: str) -> dict[str, Any] | None:
    """The layer a `<dataset>:<field>` belongs to, or None."""
    return next((r for r in load_layers() if field in r["fields"]), None)
