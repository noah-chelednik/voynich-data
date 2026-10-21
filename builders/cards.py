"""
The parts of the dataset cards that state the data (roadmap item 1.9, D8): rendered from the schema and the committed build
reports, never written by hand, so a card cannot state a number or a field the build does not produce.
`tests/test_cards.py` checks that each card holds exactly these renderings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validators.schema import load_schema

ROOT = Path(__file__).resolve().parent.parent


def _type(spec: dict[str, Any]) -> str:
    kind = spec.get("type", "")
    if isinstance(kind, list):
        return " or ".join(kind)
    if kind == "array":
        return f"array of {_type(spec.get('items', {})) or 'values'}"
    return str(kind)


def schema_field_table(schema: dict[str, Any]) -> str:
    """A Markdown table of every field the schema defines, in schema order, with its type and description."""
    lines = ["| Field | Type | Description |", "|---|---|---|"]
    for name, spec in schema["properties"].items():
        description = " ".join(str(spec.get("description", "")).split()).replace("|", "\\|")
        lines.append(f"| `{name}` | {_type(spec)} | {description} |")
    return "\n".join(lines)


def eva_statistics(report: dict[str, Any]) -> str:
    """The EVA dataset's totals, from its build report."""
    rows = [
        ("Pages", report["pages_with_lines"]),
        ("Lines (loci)", report["total_lines"]),
        ("Source loci", report["source_loci"]),
        ("Words (`word_count`, summed)", report["total_words"]),
        ("EVA characters (`char_count`, summed)", report["total_characters"]),
        ("Lines holding a high-ASCII code", report["lines_with_high_ascii"]),
    ]
    rows += [(f"`{kind}` lines", n) for kind, n in sorted(report["lines_by_type"].items())]
    rows += [
        (f"Pages of Currier language {lang}", n)
        for lang, n in sorted(report["pages_by_language"].items())
    ]
    return "\n".join(
        ["| Metric | Value |", "|---|---|"] + [f"| {name} | {value:,} |" for name, value in rows]
    )


def metadata_statistics(report: dict[str, Any]) -> str:
    """The metadata datasets' totals, from their build report."""
    rows = [
        ("Pages", report["total_pages"]),
        ("Folios", report["total_folios"]),
        ("Foldout folios", report["foldout_folios"]),
        ("Quires", report["total_quires"]),
        ("Quires with no missing folio", report["complete_quires"]),
        ("Bifolia", report["total_bifolia"]),
        ("Bifolia with one leaf in the source", report["incomplete_bifolia"]),
        ("Links from a page to Yale's images", report["total_page_canvases"]),
        ("Links to a canvas showing the page's side in part", report["partial_page_canvases"]),
    ]
    # the manifest the links come from: a URL and a hash, stated here from the report, not in the card's prose
    named = [
        ("Yale's IIIF manifest", f"<{report['iiif_manifest']}>"),
        ("Its SHA-256, when the canvases were read", f"`{report['iiif_manifest_sha256']}`"),
    ]
    rows += [(f"Pages in section `{s}`", n) for s, n in sorted(report["pages_by_section"].items())]
    rows += [
        (f"Pages of Currier language {lang}", n)
        for lang, n in sorted(report["pages_by_language"].items())
    ]
    return "\n".join(
        ["| Metric | Value |", "|---|---|"]
        + [f"| {name} | {value:,} |" for name, value in rows]
        + [f"| {name} | {value} |" for name, value in named]
    )


def committed_eva_report() -> dict[str, Any]:
    return dict(json.loads((ROOT / "output" / "eva_lines_build_report.json").read_text()))


def committed_metadata_report() -> dict[str, Any]:
    return dict(json.loads((ROOT / "output" / "metadata" / "metadata_report.json").read_text()))


# Every schema is read where the validators read it (`validators.schema.load_schema`, its SCHEMA_DIR), so a card
# describes the schema the rows are validated against, never a directory spelled again here (B-117, AB8 F4)
def eva_schema() -> dict[str, Any]:
    return load_schema("transcription_lines.schema.json")


def record_field_table(record_class: type, row: dict[str, Any]) -> str:
    """A Markdown table of a metadata record's fields, in the order of a committed row, each typed by the record
    class's annotation and described by its docstring (the Attributes section)."""
    import inspect
    import re

    doc = inspect.getdoc(record_class) or ""
    attributes = doc.split("Attributes:", 1)[1] if "Attributes:" in doc else ""
    described: dict[str, str] = {}
    current = None
    for line in attributes.splitlines():
        match = re.match(r"^    (\w+): (.*)$", line)
        if match:
            current = match.group(1)
            described[current] = match.group(2).strip()
        elif current and line.startswith("        ") and line.strip():
            described[current] += " " + line.strip()
        elif line.strip() and not line.startswith(" "):
            break

    annotations = {
        name: str(kind)
        for klass in reversed(record_class.__mro__)
        for name, kind in vars(klass).get("__annotations__", {}).items()
    }
    lines = ["| Field | Type | Description |", "|---|---|---|"]
    for name in row:
        description = described.get(name, "").replace("|", "\\|")
        lines.append(
            f"| `{name}` | `{annotations.get(name, '').replace(' | ', ' or ')}` | {description} |"
        )
    return "\n".join(lines)


def readme_datasets_table() -> str:
    """The README's table of the datasets this repository builds, with their row counts, from the committed output."""

    def count(path: Path) -> int:
        return sum(1 for _ in path.open(encoding="utf-8"))

    meta = ROOT / "output" / "metadata"
    trans = ROOT / "output" / "transliterations"
    # the readings are the source configs' rows; the variant tables (roadmap item 2.7) are counted on their own
    order = json.loads((trans / "transliterations_report.json").read_text(encoding="utf-8"))[
        "source_order"
    ]
    lines = [
        "| Dataset | Rows in this build | Description |",
        "|---|---|---|",
        f"| **voynich-eva** | {count(ROOT / 'output' / 'eva_lines.jsonl'):,} | One row per locus of the ZL transliteration |",
        f"| **voynich-manuscript-metadata** | {count(meta / 'pages.jsonl'):,} pages, "
        f"{count(meta / 'folios.jsonl'):,} folios, {count(meta / 'quires.jsonl'):,} quires | Page, folio and quire metadata |",
        f"| **voynich-transcription-mismatch** | {count(ROOT / 'output' / 'mismatch_index.jsonl'):,} | ZL against IT, one row per "
        "locus of either |",
        f"| **voynich-transliterations** | {sum(count(trans / f'{s.lower()}.jsonl') for s in order):,} readings; "
        f"{count(trans / 'locus_variants.jsonl'):,} loci and {count(trans / 'word_alignments.jsonl'):,} alignments in the "
        "variant tables | Every cached transliteration in one schema, one row per reading, one config per source; the "
        "variant tables (not a consensus) |",
    ]
    return "\n".join(lines)


def readme_sources_table() -> str:
    """The README's table of the cached sources, from data_sources/sources.yaml and the files themselves."""
    from parsers import IVTFFParser
    from vcat.sources import cached_sources, load_sources

    alphabets = {entry["id"]: entry.get("alphabet", "") for entry in load_sources()["cached"]}
    lines = [
        "| Source | Alphabet | Readings (locus lines) | Upstream version | Used by |",
        "|---|---|---|---|---|",
    ]
    for source in cached_sources():
        loci = sum(len(page.loci) for page in IVTFFParser().parse_file(source.path))
        used = next(e["used_by"] for e in load_sources()["cached"] if e["id"] == source.id)
        lines.append(
            f"| {source.id}: {source.name} | {alphabets[source.id]} | {loci:,} | {source.upstream_version} | "
            f"{', '.join(used) or 'not yet used'} |"
        )
    return "\n".join(lines)


def dataset_credits_table(dataset: str) -> str:
    """Every transliteration a dataset carries, with its transliterators and upstream version, from
    data_sources/sources.yaml: the credits its card and LICENSE tell users to cite (review 4c664493 finding 4).
    """
    from vcat.sources import load_sources

    registry = load_sources()
    sources = next(d for d in registry["datasets"] if d["name"] == dataset)["sources"]
    entries = {e["id"]: e for e in registry["cached"]}
    lines = [
        "| Source | Transliteration | Transliterators | Upstream version |",
        "|---|---|---|---|",
    ]
    for source in sources:
        e = entries[source]
        lines.append(
            f"| {source} | {e['name']} | {', '.join(e['authors'])} | {e['upstream_version']} |"
        )
    return "\n".join(lines)


def license_matrix() -> str:
    """The per-source license matrix of docs/SOURCES_LICENSE.md, from data_sources/sources.yaml."""
    from vcat.sources import cached_sources

    lines = [
        "| Source | File | License | Basis | Verified | Redistributed here | Used by |",
        "|---|---|---|---|---|---|---|",
    ]
    from vcat.sources import load_sources

    used = {e["id"]: e["used_by"] for e in load_sources()["cached"]}
    for s in cached_sources():
        basis = " ".join(s.license_basis.split())
        lines.append(
            f"| {s.id} | `{s.file}` | {s.license} | {basis} | {'yes' if s.license_verified else 'no'} | "
            f"{'yes' if s.redistributed else 'no'} | {', '.join(used[s.id]) or 'not yet used'} |"
        )
    return "\n".join(lines)


def dataset_license_table() -> str:
    """Each dataset's license, as its card states it, with the sources it derives from."""
    from vcat.sources import load_sources

    lines = ["| Dataset | Sources | VCAT annotations | Card license |", "|---|---|---|---|"]
    for d in load_sources()["datasets"]:
        text = (ROOT / d["card"] / "README.md").read_text(encoding="utf-8")
        license_line = next(line for line in text.splitlines() if line.startswith("license:"))
        lines.append(
            f"| {d['name']} | {', '.join(d['sources'])} | {'yes' if d['vcat_annotations'] else 'no'} | "
            f"`{license_line.split(':', 1)[1].strip()}` |"
        )
    return "\n".join(lines)


def committed_transliterations_report() -> dict[str, Any]:
    """The transliterations dataset's build report, as committed (output/transliterations)."""
    path = ROOT / "output" / "transliterations" / "transliterations_report.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def transliterations_schema() -> dict[str, Any]:
    return load_schema("transliteration_loci.schema.json")


def transliterations_statistics(report: dict[str, Any]) -> str:
    """One row per source of the transliterations dataset, from its build report: the coverage at a glance (item 2.3);
    the page-by-page matrix is output/transliterations/coverage_matrix.csv."""
    lines = [
        "| Source | Config | Alphabet | Rows (readings) | Pages | Transcribers | Lines reported, not emitted |",
        "|---|---|---|---|---|---|---|",
    ]
    for source_id in report["source_order"]:
        entry = report["sources"][source_id]
        transcribers = ", ".join(entry["transcribers"]) or "none"
        lines.append(
            f"| {source_id} | `{source_id.lower()}` | {entry['alphabet']} | {entry['rows']:,} | {entry['pages']:,} | "
            f"{transcribers} | {len(entry['reported']):,} |"
        )
    return "\n".join(lines)


def mismatch_schema() -> dict[str, Any]:
    return load_schema("mismatch_index.schema.json")


def layers_table(layers: list[dict[str, Any]]) -> str:
    """The interpretive layers and their attribution (roadmap item 2.8), from data_sources/layers.yaml."""
    lines = [
        "| Layer | Kind | Fields | Attribution | License |",
        "|---|---|---|---|---|",
    ]
    for layer in layers:
        kind = "VCAT's judgement" if layer["kind"] == "vcat" else "the source's"
        fields = ", ".join(f"`{f}`" for f in layer["fields"])
        attribution = " ".join(str(layer["attribution"]).split()).replace("|", "\\|")
        lines.append(
            f"| `{layer['layer']}` | {kind} | {fields} | {attribution} | `{layer['license']}` |"
        )
    return "\n".join(lines)


def layers_field_table() -> str:
    """The fields of the `layers` configuration (vcat.layers.LAYER_FIELD_DESCRIPTIONS), in the record's order."""
    from vcat.layers import LAYER_FIELD_DESCRIPTIONS, LAYER_FIELDS

    lines = ["| Field | Type | Description |", "|---|---|---|"]
    for name in LAYER_FIELDS:
        kind, description = LAYER_FIELD_DESCRIPTIONS[name]
        lines.append(f"| `{name}` | `{kind}` | {description} |")
    return "\n".join(lines)


def page_canvases_field_table() -> str:
    """The fields of the `page_canvases` configuration (vcat.iiif.LINK_FIELD_DESCRIPTIONS), in the record's order."""
    from vcat.iiif import LINK_FIELD_DESCRIPTIONS, LINK_FIELDS

    lines = ["| Field | Type | Description |", "|---|---|---|"]
    for name in LINK_FIELDS:
        kind, description = LINK_FIELD_DESCRIPTIONS[name]
        lines.append(f"| `{name}` | `{kind}` | {description} |")
    return "\n".join(lines)


def words_schema() -> dict[str, Any]:
    return load_schema("eva_words.schema.json")


def committed_words_report() -> dict[str, Any]:
    """The word level's build report, as committed (output/eva_words_report.json)."""
    return dict(json.loads((ROOT / "output" / "eva_words_report.json").read_text(encoding="utf-8")))


def words_statistics(report: dict[str, Any]) -> str:
    """The word level's totals (roadmap item 2.6), from its build report."""
    rows = [
        ("Words", report["total_words"]),
        ("Lines holding a word", report["lines"] - report["lines_without_words"]),
        ("Paragraphs (the source's `<%>` to `<$>`)", report["paragraphs"]),
        ("Words in a paragraph", report["words_in_paragraphs"]),
        ("Words followed by an uncertain space", report["uncertain_spaces"]),
    ]
    return "\n".join(
        ["| Metric | Value |", "|---|---|"] + [f"| {name} | {value:,} |" for name, value in rows]
    )


def variants_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    """The schemas of the variant tables (roadmap item 2.7): locus variants, word alignments."""
    return tuple(  # type: ignore[return-value]
        load_schema(f"{n}.schema.json") for n in ("locus_variants", "word_alignments")
    )


def committed_variants_report() -> dict[str, Any]:
    path = ROOT / "output" / "transliterations" / "variants_report.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def variants_statistics(report: dict[str, Any]) -> str:
    """The variant tables' totals (roadmap item 2.7), from their report."""
    rows = [
        ("Loci (any source)", report["loci"]),
        ("Loci with two or more EVA readers", report["loci_compared"]),
        ("Loci where every EVA reader gives the same words", report["loci_all_agree"]),
        ("Loci with no majority baseline (a tie)", report["loci_without_majority"]),
        (
            "Word alignments (one per locus per reader other than the frame reader)",
            report["alignments"],
        ),
    ]
    return "\n".join(
        ["| Metric | Value |", "|---|---|"] + [f"| {name} | {value:,} |" for name, value in rows]
    )
