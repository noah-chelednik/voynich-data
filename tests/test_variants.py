"""
The variant tables (roadmap item 2.7): `locus_variants` and `word_alignments` of the transliterations dataset, checked
against the per-source rows with this test's own reading of the rules in `vcat/variants.py` (its own word split, agreement,
majority baseline and Needleman-Wunsch), and the "not a consensus" statement of the docs and the card.
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

import pytest

from vcat import variants as vv
from vcat.profiles import apply_profile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "transliterations"
ORDER = json.loads((OUT / "transliterations_report.json").read_text())["source_order"]
SOURCES = {
    s: [json.loads(x) for x in (OUT / f"{s.lower()}.jsonl").read_text().splitlines()] for s in ORDER
}
LOCI = [json.loads(x) for x in (OUT / "locus_variants.jsonl").read_text().splitlines()]
ALIGNMENTS = [json.loads(x) for x in (OUT / "word_alignments.jsonl").read_text().splitlines()]


def own_words(text_raw: str) -> list[str]:
    return [w for w in re.split(r"[.,\s]+", apply_profile("analysis-v1", text_raw)) if w]


def own_alignment(frame: list[str], other: list[str]) -> list[tuple[str | None, str | None]]:
    """Needleman-Wunsch written again: costs 0/1/1/1; from the end, the diagonal first, then a deletion, then an insertion."""
    n, m = len(frame), len(other)
    d = [[i + j if i == 0 or j == 0 else 0 for j in range(m + 1)] for i in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(
                d[i - 1][j - 1] + (frame[i - 1] != other[j - 1]), d[i - 1][j] + 1, d[i][j - 1] + 1
            )
    out: list[tuple[str | None, str | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (frame[i - 1] != other[j - 1]):
            i, j = i - 1, j - 1
            out.insert(0, (frame[i], other[j]))
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            i -= 1
            out.insert(0, (frame[i], None))
        else:
            j -= 1
            out.insert(0, (None, other[j]))
    return out


@pytest.mark.parametrize(
    ("frame", "other", "expected"),
    [
        (["a", "b", "c"], ["a", "b", "c"], [("a", "a"), ("b", "b"), ("c", "c")]),
        (["a", "b", "c"], ["a", "x", "c", "d"], [("a", "a"), ("b", "x"), ("c", "c"), (None, "d")]),
        (["a", "b"], ["b"], [("a", None), ("b", "b")]),
        # from the end the diagonal is taken first, so the last words pair and the first is an insertion
        (["a"], ["x", "y"], [(None, "x"), ("a", "y")]),
        ([], ["x"], [(None, "x")]),
        (["a"], [], [("a", None)]),
    ],
)
def test_the_alignment_rule_on_stated_cases(frame, other, expected):
    assert vv.align(frame, other) == expected == own_alignment(frame, other)


def test_the_tables_are_the_rules_over_the_sources():
    loci, alignments = vv.variant_tables(SOURCES, ORDER)
    as_json = [json.loads(json.dumps(r, sort_keys=True)) for r in loci]
    assert as_json == LOCI
    assert [json.loads(json.dumps(r, sort_keys=True)) for r in alignments] == ALIGNMENTS


def test_every_locus_row_is_its_sources_read_again():
    """Readers, words, agreement, distinct readings and the majority baseline, recomputed here from the source rows."""
    by_id: dict[str, list[tuple[str, dict]]] = {}
    for source in ORDER:
        for row in SOURCES[source]:
            by_id.setdefault(row["line_id"], []).append((source, row))
    assert [row["line_id"] for row in LOCI] == list(by_id)
    for row in LOCI:
        held = by_id[row["line_id"]]
        assert row["present_in"] == list(dict.fromkeys(s for s, _ in held))
        eva = [r for _, r in held if r["alphabet"] == "EVA"]
        names = [
            f"{r['source']}.{r['transcriber']}" if r["transcriber"] else r["source"] for r in eva
        ]
        assert row["compared"] == names == [x["reader"] for x in row["readings"]]
        words = [own_words(r["text_raw"]) for r in eva]
        assert [x["words"] for x in row["readings"]] == words
        # and each reading's provenance is its source row's (reach 92b55594 gap 2)
        assert [
            (x["source"], x["transcriber"], x["locus_type"], x["source_line"])
            for x in row["readings"]
        ] == [(r["source"], r["transcriber"], r["locus_type"], r["source_line"]) for r in eva]
        pairs = list(combinations([tuple(w) for w in words], 2))
        assert row["agreement"] == (sum(a == b for a, b in pairs) / len(pairs) if pairs else None)
        assert row["distinct_readings"] == len({tuple(w) for w in words})
        counts = sorted(
            ((sum(tuple(v) == tuple(w) for v in words), tuple(w)) for w in words), reverse=True
        )
        top = counts[0][0] if counts else 0
        leaders = {w for c, w in counts if c == top}
        if not words or len(leaders) > 1:
            assert row["majority_baseline"] is None
        else:
            (best,) = leaders
            assert row["majority_baseline"]["words"] == list(best)
            assert row["majority_baseline"]["support"] == top
            assert row["majority_baseline"]["readers"] == [
                n for n, w in zip(names, words, strict=True) if tuple(w) == best
            ]


def test_only_eva_is_compared():
    other = {s for s in ORDER if SOURCES[s] and SOURCES[s][0]["alphabet"] != "EVA"}
    assert other, "the dataset holds sources in other alphabets"
    for row in LOCI:
        assert not {x["source"] for x in row["readings"]} & other
    # both sides of every alignment (reach 92b55594 gap 3)
    for row in ALIGNMENTS:
        assert (
            row["frame_reader"].split(".")[0] not in other
            and row["reader"].split(".")[0] not in other
        ), row


def test_every_alignment_is_its_two_readings_aligned_by_the_rule():
    loci = {row["line_id"]: row for row in LOCI}
    seen: dict[str, list[str]] = {}
    for row in ALIGNMENTS:
        locus = loci[row["line_id"]]
        words = {x["reader"]: x["words"] for x in locus["readings"]}
        frame = "ZL" if "ZL" in words else locus["compared"][0]
        assert row["frame_reader"] == frame
        pairs = own_alignment(words[frame], words[row["reader"]])
        assert row["frame_words"] == [f for f, _ in pairs]
        assert row["words"] == [w for _, w in pairs]
        assert row["operations"] == [
            (
                "insert"
                if f is None
                else "delete" if w is None else "match" if f == w else "substitute"
            )
            for f, w in pairs
        ]
        assert row["matches"] == row["operations"].count("match")
        assert row["word_agreement"] == (row["matches"] / len(pairs) if pairs else None)
        seen.setdefault(row["line_id"], []).append(row["reader"])
    for line_id, locus in loci.items():
        if locus["compared"]:
            frame = "ZL" if "ZL" in locus["compared"] else locus["compared"][0]
            assert seen.get(line_id, []) == [r for r in locus["compared"] if r != frame], line_id


def test_the_rows_meet_their_schemas():
    from validators.schema import validate_against_schema

    for name, rows in (("locus_variants", LOCI), ("word_alignments", ALIGNMENTS)):
        valid, problems = validate_against_schema(rows, f"{name}.schema.json")
        assert valid, problems[:5]


@pytest.mark.parametrize(
    "path",
    ["huggingface/voynich-transliterations/README.md", "docs/data_model.md"],
)
def test_the_tables_say_they_are_not_a_consensus(path):
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "not a consensus" in text.lower()
    assert "majority_baseline" in text and "never the default" in text
    for row in LOCI[:1]:
        assert not [k for k in row if "consensus" in k]


def test_the_schemas_list_the_builder_s_fields():
    from builders.build_variants import ALIGNMENT_FIELDS, LOCUS_FIELDS

    for name, fields in (("locus_variants", LOCUS_FIELDS), ("word_alignments", ALIGNMENT_FIELDS)):
        schema = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
        assert list(schema["properties"]) == list(fields)
        assert schema["required"] == list(fields) and schema["additionalProperties"] is False
