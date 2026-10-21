"""The word level of the EVA dataset (roadmap item 2.6): one row per word of the EVA lines (`output/eva_lines.jsonl`), cut
by the one EVA tokenizer (`vcat/words.py`), with its position in its line and its paragraph and the line's hand, Currier
language, section and quire.

The paragraphs are the source's: a paragraph runs from the line whose locus carries the paragraph start `<%>` to the line
that carries its end `<$>` (IVTFF 2.0 section 6.9: "the decision where paragraphs begin and end is made by the
transcriber"), among the lines of generic type `P`, on one page. A line outside every such pair (ZL's free-floating `Pb`
lines on f68r1 and f84v), a label, a circle or a radius is in no paragraph: its paragraph fields are null.

    python -m builders.build_eva_words          # from output/eva_lines.jsonl into output/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from vcat.words import split_words

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
LINES = "eva_lines.jsonl"
WORDS = "eva_words.jsonl"
REPORT = "eva_words_report.json"

#: The fields of a word row, in order, with their type and what they hold (the schema and the card are checked against it)
WORD_FIELDS: dict[str, tuple[str, str]] = {
    "word_id": (
        "string",
        "The word's id: its line's `line_id`, a period and its position in the line (`f1r:1.3`)",
    ),
    "line_id": ("string", "The line (locus) it is in, as in the lines config"),
    "page_id": ("string", "The page"),
    "line_index": ("integer", "The line's position on its page, as in the lines config"),
    "word_index": ("integer", "The word's position in its line, from 1"),
    "word": (
        "string",
        "The word: a run of the line's `text_clean` between word spaces (`vcat/words.py`)",
    ),
    "space_after": (
        "string or null",
        "The space after it: `certain` (`.`), `uncertain` (`,`), or null for the last word of the line",
    ),
    "line_initial": ("boolean", "Whether it is the first word of its line"),
    "line_final": ("boolean", "Whether it is the last word of its line"),
    "paragraph_id": (
        "string or null",
        "The source's paragraph it is in (`<page>.p<n>`, the n-th on the page), or null outside every paragraph",
    ),
    "line_in_paragraph": (
        "integer or null",
        "Its line's position in the paragraph, from 1; null outside one",
    ),
    "paragraph_initial": ("boolean", "Whether it is the first word of its paragraph"),
    "paragraph_final": ("boolean", "Whether it is the last word of its paragraph"),
    "line_type": (
        "string",
        "The line's type, as in the lines config (`paragraph`, `label`, `circle`, `radius`)",
    ),
    "locus_type": ("string", "The line's IVTFF locus code, as in the lines config (`@P0`)"),
    "hand": ("string or null", "The line's hand (`$H`), as in the lines config"),
    "currier_language": (
        "string or null",
        "The line's Currier language (`$L`), as in the lines config",
    ),
    "section": ("string or null", "The line's section, as in the lines config"),
    "quire": ("string or null", "The line's quire (`$Q`), as in the lines config"),
}

START, END = "<%>", "<$>"


def word_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every word of the lines, in line order then word order, with its positional features."""
    rows: list[dict[str, Any]] = []
    paragraph: list[dict[str, Any]] | None = None  # the word rows of the open paragraph
    paragraph_id: str | None = None
    line_in_paragraph = 0
    page = None
    counter = 0
    for line in lines:
        if line["page_id"] != page:
            page, counter, paragraph, paragraph_id, line_in_paragraph = (
                line["page_id"],
                0,
                None,
                None,
                0,
            )
        is_text = str(line.get("locus_type", ""))[1:2] == "P"
        markers = line.get("markers") or []
        if is_text and START in markers:
            counter += 1
            paragraph, paragraph_id, line_in_paragraph = [], f"{page}.p{counter}", 0
        in_paragraph = is_text and paragraph is not None
        if in_paragraph:
            line_in_paragraph += 1
        words = split_words(str(line.get("text_clean", "")))
        for index, (word, space) in enumerate(words, start=1):
            row = {
                "word_id": f"{line['line_id']}.{index}",
                "line_id": line["line_id"],
                "page_id": line["page_id"],
                "line_index": line["line_index"],
                "word_index": index,
                "word": word,
                "space_after": space,
                "line_initial": index == 1,
                "line_final": index == len(words),
                "paragraph_id": paragraph_id if in_paragraph else None,
                "line_in_paragraph": line_in_paragraph if in_paragraph else None,
                "paragraph_initial": False,
                "paragraph_final": False,
                "line_type": line.get("line_type"),
                "locus_type": line.get("locus_type"),
                "hand": line.get("hand"),
                "currier_language": line.get("currier_language"),
                "section": line.get("section"),
                "quire": line.get("quire"),
            }
            rows.append(row)
            if in_paragraph and paragraph is not None:
                paragraph.append(row)
        if in_paragraph and END in markers and paragraph is not None:
            if paragraph:
                paragraph[0]["paragraph_initial"] = True
                paragraph[-1]["paragraph_final"] = True
            paragraph, paragraph_id, line_in_paragraph = None, None, 0
    return rows


def build_report(
    lines_path: Path, lines: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """The build's provenance and totals: the lines file it read, by SHA-256, and what the rows hold."""
    return {
        "lines_file": lines_path.name,
        "lines_sha256": hashlib.sha256(lines_path.read_bytes()).hexdigest(),
        "tokenizer": "vcat/words.py",
        "total_words": len(rows),
        "lines": len(lines),
        "lines_without_words": len(lines) - len({r["line_id"] for r in rows}),
        "paragraphs": len({r["paragraph_id"] for r in rows if r["paragraph_id"]}),
        "words_in_paragraphs": sum(1 for r in rows if r["paragraph_id"]),
        "uncertain_spaces": sum(1 for r in rows if r["space_after"] == "uncertain"),
    }


def build(output_dir: Path = OUTPUT, parquet: bool = True) -> dict[str, Any]:
    """Build the words from `<output_dir>/eva_lines.jsonl` into the same directory; return the report."""
    lines_path = output_dir / LINES
    lines = [
        json.loads(line)
        for line in lines_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = word_rows(lines)
    with (output_dir / WORDS).open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            )
    if parquet:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pq.write_table(pa.Table.from_pylist(rows), output_dir / WORDS.replace(".jsonl", ".parquet"))
    report = build_report(lines_path, lines, rows)
    (output_dir / REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--no-parquet", action="store_true")
    args = parser.parse_args(argv)
    report = build(args.output_dir, parquet=not args.no_parquet)
    print(
        f"{report['total_words']} words in {report['lines'] - report['lines_without_words']} lines, "
        f"{report['paragraphs']} paragraphs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
