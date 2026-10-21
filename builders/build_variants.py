"""The variant tables of the transliterations dataset (roadmap item 2.7): `locus_variants` (one row per locus id, every EVA
reader's words side by side, the agreement, the labelled majority baseline) and `word_alignments` (one row per locus per
reader, its words aligned to the frame reader's), built from the committed per-source rows (`output/transliterations/`) by
the rules of `vcat/variants.py`. Not a consensus.

    python -m builders.build_variants          # from output/transliterations/ into the same directory
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from vcat import variants as vv

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "output" / "transliterations"
LOCI = "locus_variants.jsonl"
ALIGNMENTS = "word_alignments.jsonl"
REPORT = "variants_report.json"


#: The fields of a `locus_variants` row, in order: (JSON type, what it holds); the schema is written from them
LOCUS_FIELDS: dict[str, tuple[Any, str]] = {
    "line_id": ("string", "The locus id (`<page>:<locus>`), as in each source's config"),
    "page_id": ("string", "The page"),
    "line_number": ("integer", "The locus number on the page"),
    "present_in": ("array", "Every source holding the locus, in any alphabet, in source order"),
    "compared": (
        "array",
        "The readers compared: the EVA sources holding it, one per transcriber where a file has several",
    ),
    "readings": (
        "array",
        "Each compared reader's reading: reader, source, transcriber, locus type, source line, words",
    ),
    "distinct_readings": ("integer", "How many different word sequences the readers give"),
    "agreement": (
        ["number", "null"],
        "The share of pairs of readers giving the same words; null for fewer than two",
    ),
    "majority_baseline": (
        ["object", "null"],
        "A labelled baseline, never the default and not a reading: the words more readers give than any other, with "
        "their support and readers; null on a tie",
    ),
}
#: The fields of a `word_alignments` row, in order
ALIGNMENT_FIELDS: dict[str, tuple[Any, str]] = {
    "line_id": ("string", "The locus id"),
    "page_id": ("string", "The page"),
    "frame_reader": (
        "string",
        "The reader aligned to: ZL where it holds the locus, else the first reader",
    ),
    "reader": ("string", "The reader aligned"),
    "frame_words": (
        "array",
        "The frame's words, position by position; null where the reader has a word the frame lacks",
    ),
    "words": (
        "array",
        "The reader's words in the same positions; null where the frame has a word the reader lacks",
    ),
    "operations": (
        "array",
        "Each position's operation: `match`, `substitute`, `delete` or `insert`",
    ),
    "matches": ("integer", "How many positions hold equal words"),
    "word_agreement": (
        ["number", "null"],
        "`matches` over the positions; null when neither has a word",
    ),
}


def schema(title: str, fields: dict[str, tuple[Any, str]]) -> dict[str, Any]:
    """The skeleton of a table's JSON schema, from its field list (the committed schemas add the item types and bounds;
    `tests/test_variants.py` checks their fields are these, in order)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        "type": "object",
        "required": list(fields),
        "additionalProperties": False,
        "properties": {
            name: {"type": kind, "description": text} for name, (kind, text) in fields.items()
        },
    }


def _write(path: Path, rows: list[dict[str, Any]], parquet: bool) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            )
    if parquet:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pq.write_table(pa.Table.from_pylist(rows), path.with_suffix(".parquet"))


def build(directory: Path = DIRECTORY, parquet: bool = True) -> dict[str, Any]:
    """Build both tables from `<directory>/<source>.jsonl` (the sources the transliterations report lists, in its order)
    into the same directory; return the report."""
    # the source order chooses each locus's readers' order and its fallback frame, so the report records it and the hash
    # of the file it came from (review 26ba5c94 finding 1)
    control = (directory / "transliterations_report.json").read_bytes()
    order = json.loads(control.decode("utf-8"))["source_order"]
    files = {source: directory / f"{source.lower()}.jsonl" for source in order}
    # each file read once: the rows and the hash the report gives come from the same bytes (review 3d607506 finding 3)
    raw = {source: path.read_bytes() for source, path in files.items()}
    rows = {
        source: [json.loads(x) for x in data.decode("utf-8").splitlines() if x.strip()]
        for source, data in raw.items()
    }
    loci, alignments = vv.variant_tables(rows, order)
    _write(directory / LOCI, loci, parquet)
    _write(directory / ALIGNMENTS, alignments, parquet)
    compared = sorted(
        {row["alphabet"] for rows_ in rows.values() for row in rows_} & {vv.COMPARED_ALPHABET}
    )
    report = {
        "profile": vv.PROFILE,
        "tokenizer": "vcat/words.py",
        "algorithm": "Needleman-Wunsch on words: match 0, substitution 1, insertion 1, deletion 1; ties: diagonal, "
        "deletion, insertion (vcat/variants.py)",
        "frame_source": vv.FRAME_SOURCE,
        "source_order": order,
        "source_order_file": {
            "file": "transliterations_report.json",
            "sha256": hashlib.sha256(control).hexdigest(),
        },
        "compared_alphabets": compared,
        "inputs": {
            source: {"file": path.name, "sha256": hashlib.sha256(raw[source]).hexdigest()}
            for source, path in files.items()
        },
        "loci": len(loci),
        # compared: two readers or more, which is when an agreement is defined
        "loci_compared": sum(1 for row in loci if row["agreement"] is not None),
        "loci_all_agree": sum(1 for row in loci if row["agreement"] == 1),
        "loci_without_majority": sum(
            1 for row in loci if row["compared"] and row["majority_baseline"] is None
        ),
        "alignments": len(alignments),
    }
    (directory / REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--directory", type=Path, default=DIRECTORY)
    parser.add_argument("--no-parquet", action="store_true")
    args = parser.parse_args(argv)
    report = build(args.directory, parquet=not args.no_parquet)
    print(
        f"{report['loci']} loci, {report['loci_compared']} compared, {report['alignments']} alignments"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
