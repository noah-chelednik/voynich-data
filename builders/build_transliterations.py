"""
Every transliteration in one schema (roadmap item 2.3)
======================================================

One row per reading of one locus in each cached transliteration (`data_sources/sources.yaml`, `cached`): its source, its
alphabet, Zandbergen's page and locus ids, the locus type, the transcriber of an interlinear source's reading, and the text
exactly as written, in the source's own alphabet. Nothing is normalized, mapped to another alphabet or compared: that is
for the profiles (EVA only), the mismatch index and the variant tables of item 2.7. The sources are not independent
(`docs/sources.md`, "How the sources depend on each other"), so agreement between rows of two sources is not confirmation.

Never silent (principle 3): every reading of every source is a row or is reported. A line the parser does not accept is
listed in the report with its id and reason; one the source's record lists as breaking IVTFF itself (LSI's four `44a`
loci) is expected there, and any other unaccounted reading fails the build before anything is written.

Outputs, in ``output/transliterations/``:

- ``<source>.jsonl`` and ``<source>.parquet``, one per cached source (lower-case id: ``zl``, ``lsi`` ...);
- ``transliterations_report.json``: per source its file, SHA-256, upstream version, alphabet, encoding, the counts and
  the reported lines and the lines kept with a warning (each with its line, id and reason);
- ``coverage_matrix.csv``: the readings each source has on each page (the coverage matrix of item 2.3).

Command line::

    python -m builders.build_transliterations
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from parsers import page_order_key
from parsers.ivtff_parser import IVTFFParser
from vcat.loss_accounting import account, census_source
from vcat.sources import (
    CachedSource,
    cached_sources,
    load_sources,
    nonconforming_lines,
    repo_relative,
    require_licensed,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "transliterations"
DATASET = "voynich-transliterations"
REPORT = "transliterations_report.json"
MATRIX = "coverage_matrix.csv"
#: The start of a locus line (`<page.number`), read without the parser
LOCUS_LINE_START = re.compile(r"^<[^<>.,;\s]+\.\d")


def arrow_schema() -> Any:
    """The Parquet schema of every source's file: the row schema's fields in its order, `transcriber` a nullable string."""
    import pyarrow as pa

    return pa.schema(
        [
            ("source", pa.string()),
            ("alphabet", pa.string()),
            ("page_id", pa.string()),
            ("line_number", pa.int64()),
            ("line_id", pa.string()),
            ("locus_type", pa.string()),
            ("transcriber", pa.string()),
            ("text_raw", pa.string()),
            ("source_line", pa.int64()),
        ]
    )


@dataclass(frozen=True)
class ReadingRecord:
    """One reading of one locus in one source, as written (schemas/transliteration_loci.schema.json)."""

    source: str
    alphabet: str
    page_id: str
    line_number: int
    line_id: str
    locus_type: str
    transcriber: str | None
    text_raw: str
    source_line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dataset_sources() -> list[CachedSource]:
    """The sources this dataset's record in data_sources/sources.yaml names, in that order: every cached source."""
    entry = next(d for d in load_sources()["datasets"] if d["name"] == DATASET)
    by_id = {source.id: source for source in cached_sources()}
    return [by_id[source_id] for source_id in entry["sources"]]


def build_source(source: CachedSource) -> tuple[list[ReadingRecord], dict[str, Any]]:
    """The rows of one source and its report entry. Raises when a reading is unaccounted, or when the parser rejects a
    line the source's record does not list as breaking IVTFF."""
    require_licensed(source.path)  # before anything is read (S12)
    parser = IVTFFParser()
    pages = list(parser.parse_file(source.path))
    alphabet = _alphabet(source)  # once: it reads the registry
    rows = [
        ReadingRecord(
            source=source.id,
            alphabet=alphabet,
            page_id=page.page_id,
            line_number=locus.locus_number,
            line_id=locus.locus_id,
            locus_type=locus.locus_code,
            transcriber=locus.transcriber or None,
            text_raw=locus.text_raw,
            source_line=locus.source_line,
        )
        for page in pages
        for locus in page.loci
    ]
    rejected = [w for w in parser.warnings if w.emitted_id is None]
    expected = nonconforming_lines(source.path)
    # a rejection is expected only when its own line is listed, with its id: a line the record does not list never
    # matches, whatever its id (reach 0dea398a gap 3: an unlisted line with no id once matched a missing entry)
    unexpected = [
        w
        for w in rejected
        if w.line_number not in expected or expected[w.line_number] != w.locus_id
    ]
    if unexpected or sorted(w.line_number for w in rejected) != sorted(expected):
        raise ValueError(
            f"{source.id}: the parser rejected lines its record does not list: "
            f"{[(w.line_number, w.locus_id, w.reason) for w in unexpected][:5]}"
        )
    loss = account(
        census_source(source.path),
        [row.line_id for row in rows],
        [page.page_id for page in pages],
        reported_loci=[w.locus_id for w in rejected if w.locus_id],
    )
    if not loss.complete:
        raise ValueError(f"{source.id}: {loss.problems()}")
    # Every locus line of the file is exactly one row or one reported line, by its line number: counting ids alone
    # would let one reading of a locus stand in for another (reach 0dea398a gap 2)
    text = source.path.read_text(encoding=source.encoding, errors="surrogateescape")
    locus_lines = [n for n, line in enumerate(text.splitlines(), 1) if LOCUS_LINE_START.match(line)]
    accounted = sorted([row.source_line for row in rows] + [w.line_number for w in rejected])
    if accounted != locus_lines:
        missing = sorted(set(locus_lines) - set(accounted))[:5]
        repeated = sorted(n for n in set(accounted) if accounted.count(n) > 1)[:5]
        raise ValueError(
            f"{source.id}: locus lines not one row each: missing {missing}, repeated {repeated}"
        )
    entry = {
        "file": repo_relative(source.path),
        "sha256": hashlib.sha256(source.path.read_bytes()).hexdigest(),
        "upstream_version": source.upstream_version,
        "alphabet": alphabet,
        "encoding": source.encoding,
        "source_loci": loss.source_loci,
        "rows": len(rows),
        "pages": len({row.page_id for row in rows}),
        "transcribers": sorted({row.transcriber for row in rows if row.transcriber}),
        "reported": [
            {"line": w.line_number, "id": w.locus_id, "reason": w.reason} for w in rejected
        ],
        "kept_with_warning": len(parser.warnings) - len(rejected),
        # each line kept with a warning, as the reported ones are: its line, the id of the row it became and the
        # parser's reason (B-102, AB6 F2: only their count was kept)
        "kept": [
            {"line": w.line_number, "id": w.emitted_id, "reason": w.reason}
            for w in parser.warnings
            if w.emitted_id is not None
        ],
    }
    return rows, entry


def _alphabet(source: CachedSource) -> str:
    entry = next(e for e in load_sources()["cached"] if e["id"] == source.id)
    return str(entry["alphabet"])


def coverage_matrix(rows_by_source: dict[str, list[ReadingRecord]]) -> str:
    """The coverage matrix as CSV: one row per page (in manuscript order), one column per source, each cell the number of
    readings that source has on that page (0 when none)."""
    counts: dict[str, dict[str, int]] = {}
    for source_id, rows in rows_by_source.items():
        for row in rows:
            counts.setdefault(row.page_id, {}).setdefault(source_id, 0)
            counts[row.page_id][source_id] += 1
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["page_id", *rows_by_source])
    for page_id in sorted(counts, key=page_order_key):
        writer.writerow([page_id, *(counts[page_id].get(s, 0) for s in rows_by_source)])
    return out.getvalue()


def build_transliterations(output_dir: Path | None = None) -> dict[str, Any]:
    """Build every source's rows, the report and the coverage matrix into output_dir (default output/transliterations)."""
    output_dir = output_dir or OUTPUT_DIR
    rows_by_source: dict[str, list[ReadingRecord]] = {}
    report: dict[str, Any] = {"dataset": DATASET, "sources": {}, "source_order": []}
    for source in dataset_sources():
        rows, entry = build_source(source)
        rows_by_source[source.id] = rows
        report["sources"][source.id] = entry
        report["source_order"].append(
            source.id
        )  # the registry's order (the JSON's keys are sorted)
    # Every row is checked against its schema before anything is written (B-023)
    from validators.schema import validate_against_schema

    for source_id, rows in rows_by_source.items():
        valid, errors = validate_against_schema(
            [r.to_dict() for r in rows], "transliteration_loci.schema.json"
        )
        if not valid:
            raise ValueError(f"{source_id}: rows break their schema: {errors[:5]}")
    output_dir.mkdir(parents=True, exist_ok=True)
    import pyarrow as pa
    import pyarrow.parquet as pq

    for source_id, rows in rows_by_source.items():
        name = source_id.lower()
        with open(output_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        # one Arrow schema for every source's file, so they read together in any order (review 8589fcb7 finding 1: an
        # inferred schema typed `transcriber` null where no reading has one)
        table = pa.Table.from_pylist([r.to_dict() for r in rows], schema=arrow_schema())
        pq.write_table(table, output_dir / f"{name}.parquet")
    (output_dir / MATRIX).write_text(coverage_matrix(rows_by_source), encoding="utf-8")
    (output_dir / REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # and the variant tables over these rows (roadmap item 2.7), so one build makes every config of the dataset
    from builders.build_variants import build as build_variants

    build_variants(output_dir)
    return report


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    result = build_transliterations()
    for source_id, entry in result["sources"].items():
        print(
            f"{source_id}: {entry['rows']} rows, {entry['pages']} pages, {len(entry['reported'])} reported"
        )
