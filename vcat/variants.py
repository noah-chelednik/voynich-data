"""The variant tables (roadmap item 2.7): every EVA source's reading of each locus, side by side, with how far they agree,
and each reading's words aligned to one frame. Not a consensus: no reading is chosen, and none is corrected.

**Readers.** A reader is one source's transcription of a locus: a source (`ZL`, `IT`, ...) or, where a file holds several
transcribers of one locus, a source and its transcriber (`LSI.H`). Only sources in EVA are compared (`COMPARED_ALPHABET`);
the sources in other alphabets (Currier, FSG, v101) are named among those holding the locus, never compared: VCAT maps no
alphabet to another (DECISIONS Q82).

**Readings.** A reader's reading is its `text_raw` under the profile `analysis-v1` (`vcat/profiles.py`), cut into words by
the EVA tokenizer (`vcat/words.py`). Two readers agree on a locus when their word sequences are equal.

**Agreement of a locus.** `agreement` is the share of pairs of readers whose word sequences are equal (every pair counted
once; null for a locus with fewer than two readers); `distinct_readings` is how many different word sequences there are.

**Majority baseline.** `majority_baseline` is the word sequence more readers give than any other, with how many give it, or
null when two or more tie. It is a labelled baseline for comparison, never the default and never a reading of the locus:
readers are not independent (IT 2a revises IT; RF1b derives from ZL and GC; LSI holds several older transcriptions), so a
count of readers is not evidence.

**Word alignment.** Each reader's words are aligned to the words of the locus's frame reader: `ZL` where ZL holds the locus,
else the first reader in source order. The frame is a coordinate system, not a reference: an alignment says which words
stand in the same place, not which is right. The algorithm is Needleman-Wunsch global alignment on words with cost 0 for
equal words and 1 for a substitution, an insertion or a deletion; of the alignments of least cost, the traceback from the
end prefers, in order, the diagonal (a match or a substitution), a frame word with no reader word (a deletion), and a reader
word with no frame word (an insertion). `word_agreement` is the share of aligned pairs whose words are equal.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from vcat.profiles import apply_profile
from vcat.words import split_words

#: The only alphabet whose readings are compared (DECISIONS Q82: no mapping between alphabets)
COMPARED_ALPHABET = "EVA"
#: The reader the words are aligned to, where it holds the locus
FRAME_SOURCE = "ZL"
#: The profile a reading is taken under
PROFILE = "analysis-v1"

MATCH, SUBSTITUTE, DELETE, INSERT = "match", "substitute", "delete", "insert"


def reading_words(text_raw: str) -> list[str]:
    """A locus's words: its `text_raw` under the profile, cut by the EVA tokenizer."""
    return [word for word, _ in split_words(apply_profile(PROFILE, text_raw))]


def align(frame: list[str], other: list[str]) -> list[tuple[str | None, str | None]]:
    """The least-cost alignment of `other`'s words to `frame`'s (module docstring): pairs of (frame word, other word), a
    None where one side has no word."""
    n, m = len(frame), len(other)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diagonal = cost[i - 1][j - 1] + (0 if frame[i - 1] == other[j - 1] else 1)
            cost[i][j] = min(diagonal, cost[i - 1][j] + 1, cost[i][j - 1] + 1)
    pairs: list[tuple[str | None, str | None]] = []
    i, j = n, m
    while i or j:
        if (
            i
            and j
            and cost[i][j] == cost[i - 1][j - 1] + (0 if frame[i - 1] == other[j - 1] else 1)
        ):
            pairs.append((frame[i - 1], other[j - 1]))
            i, j = i - 1, j - 1
        elif i and cost[i][j] == cost[i - 1][j] + 1:
            pairs.append((frame[i - 1], None))
            i -= 1
        else:
            pairs.append((None, other[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def operation(pair: tuple[str | None, str | None]) -> str:
    frame_word, word = pair
    if frame_word is None:
        return INSERT
    if word is None:
        return DELETE
    return MATCH if frame_word == word else SUBSTITUTE


def reader_name(row: dict[str, Any]) -> str:
    return f"{row['source']}.{row['transcriber']}" if row.get("transcriber") else str(row["source"])


def variant_tables(
    rows_by_source: dict[str, list[dict[str, Any]]], source_order: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The locus variants and the word alignments of the transliterations' rows (`rows_by_source[source]`, each source's
    rows in its own order), loci in the order of their first appearance, sources in `source_order`.
    """
    loci: dict[str, dict[str, Any]] = {}
    for source in source_order:
        for row in rows_by_source.get(source, []):
            entry = loci.setdefault(
                row["line_id"],
                {
                    "page_id": row["page_id"],
                    "line_number": row["line_number"],
                    "present": [],
                    "readers": [],
                },
            )
            if source not in entry["present"]:
                entry["present"].append(source)
            if row["alphabet"] == COMPARED_ALPHABET:
                entry["readers"].append(row)
    variants: list[dict[str, Any]] = []
    alignments: list[dict[str, Any]] = []
    for line_id, entry in loci.items():
        readers = [
            {
                "reader": reader_name(row),
                "source": row["source"],
                "transcriber": row.get("transcriber"),
                "locus_type": row["locus_type"],
                "source_line": row["source_line"],
                "words": reading_words(row["text_raw"]),
            }
            for row in entry["readers"]
        ]
        sequences = [tuple(r["words"]) for r in readers]
        pairs = list(combinations(sequences, 2))
        counts: dict[tuple[str, ...], int] = {}
        for sequence in sequences:
            counts[sequence] = counts.get(sequence, 0) + 1
        ranked = sorted(counts.values(), reverse=True)
        majority = None
        if ranked and (len(ranked) == 1 or ranked[0] > ranked[1]):
            best = next(s for s in sequences if counts[s] == ranked[0])
            majority = {
                "words": list(best),
                "support": ranked[0],
                "readers": [
                    r["reader"] for r, s in zip(readers, sequences, strict=True) if s == best
                ],
            }
        variants.append(
            {
                "line_id": line_id,
                "page_id": entry["page_id"],
                "line_number": entry["line_number"],
                "present_in": entry["present"],
                "compared": [r["reader"] for r in readers],
                "readings": readers,
                "distinct_readings": len(counts),
                "agreement": (sum(1 for a, b in pairs if a == b) / len(pairs)) if pairs else None,
                "majority_baseline": majority,
            }
        )
        if not readers:
            continue
        frame = next(
            (r for r in readers if r["source"] == FRAME_SOURCE and not r["transcriber"]), readers[0]
        )
        for reader in readers:
            if reader is frame:
                continue
            aligned = align(frame["words"], reader["words"])
            matches = sum(1 for pair in aligned if operation(pair) == MATCH)
            alignments.append(
                {
                    "line_id": line_id,
                    "page_id": entry["page_id"],
                    "frame_reader": frame["reader"],
                    "reader": reader["reader"],
                    "frame_words": [f for f, _ in aligned],
                    "words": [w for _, w in aligned],
                    "operations": [operation(pair) for pair in aligned],
                    "matches": matches,
                    "word_agreement": (matches / len(aligned)) if aligned else None,
                }
            )
    return variants, alignments
