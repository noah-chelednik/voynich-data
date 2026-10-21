"""
Mismatch index builder (roadmap item 1.8)
=========================================

One row per locus id found in either of the two EVA transliterations, ZL (Zandbergen, ``ZL3b-n.txt``) and IT (Takahashi,
``IT_ivtff_1a.txt``): both raw texts, both readings under the named comparison profile, and the verdict of
``vcat.comparison.compare`` (``identical``, ``same_reading``, ``alternate_reading``, ``different``), or ``zl_only`` and
``it_only`` for a locus only one source has. The other cached sources (CD, FG, GC) use other alphabets and are recorded as
present or absent only; variant tables across all sources are roadmap item 2.7.

Never silent (principle 3, B-038): every parser warning of either source is in the report, and a locus the parser reported
instead of emitting is listed there, not dropped from the comparison unseen. The numbers in the report are the build's; the
README, the dataset card and the CHANGELOG quote them (the erratum of item 1.8).
"""

from __future__ import annotations

import hashlib
import json
import logging
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from parsers import page_order_key
from parsers.ivtff_parser import IVTFFParser, Locus
from vcat.comparison import AGREEING, COMPARISON_PROFILE, VERDICTS, compare
from vcat.loss_accounting import CACHE_DIR as LOSS_CACHE_DIR
from vcat.profiles import get_profile
from vcat.sources import load_sources, require_licensed, source_file

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = LOSS_CACHE_DIR
OUTPUT_DIR = PROJECT_ROOT / "output"

#: The two compared sources, and the others recorded as present or absent: every source the mismatch dataset's record in
#: data_sources/sources.yaml names, by its file there (AB2 F3, B-081), ZL and IT first.
_DATASET = next(
    d for d in load_sources()["datasets"] if d["name"] == "voynich-transcription-mismatch"
)
SOURCES = {sid.lower(): source_file(sid).name for sid in _DATASET["sources"]}
ZL_ONLY = "zl_only"
IT_ONLY = "it_only"
STATUSES = (*VERDICTS, ZL_ONLY, IT_ONLY)


@dataclass
class MismatchRecord:
    """The comparison of one locus id between ZL and IT."""

    page_id: str
    line_number: int
    line_id: str
    status: str
    comparison_profile: str
    zl_text_raw: str | None = None
    it_text_raw: str | None = None
    zl_reading: str | None = None
    it_reading: str | None = None
    zl_locus_type: str | None = None
    it_locus_type: str | None = None
    zl_source_line: int | None = None
    it_source_line: int | None = None
    similarity_score: float | None = None
    sources_present: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoadedSource:
    """One parsed source: its loci by id and what the parser reported."""

    source_id: str
    path: Path
    sha256: str
    loci: dict[str, Locus]
    warnings: list[str]
    reported_loci: list[str]


def load_source(source_id: str, cache_dir: Path) -> LoadedSource:
    """Parse one cached source (non-strict: every line the parser does not accept is a warning, never a skip)."""
    path = cache_dir / SOURCES[source_id]
    require_licensed(path)  # before it is read (S12)
    parser = IVTFFParser()
    emitted = [locus for page in parser.parse_file(path) for locus in page.loci]
    loci = {locus.locus_id: locus for locus in emitted}
    if len(loci) != len(emitted):
        # an interlinear source holds several readings of one id; the index compares one reading per source, so a
        # second reading would replace the first unseen (B-076, B-089): refuse instead
        counts = Counter(locus.locus_id for locus in emitted)
        repeated = sorted(locus_id for locus_id, n in counts.items() if n > 1)
        raise ValueError(
            f"{source_id}: repeated locus ids, one reading per id expected: {repeated[:5]}"
        )
    return LoadedSource(
        source_id=source_id,
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        loci=loci,
        warnings=[str(w) for w in parser.warnings],
        reported_loci=[w.locus_id for w in parser.warnings if w.locus_id],
    )


def _sort_key(line_id: str) -> tuple:
    page, number = line_id.rsplit(":", 1)
    return (*page_order_key(page), int(number))


def build_records(
    sources: dict[str, LoadedSource], profile_name: str = COMPARISON_PROFILE
) -> list[MismatchRecord]:
    """One record per locus id of ZL or IT, in page order then locus number."""
    profile = get_profile(profile_name)
    zl, it = sources["zl"].loci, sources["it"].loci
    records = []
    for line_id in sorted(set(zl) | set(it), key=_sort_key):
        a, b = zl.get(line_id), it.get(line_id)
        page_id, number = line_id.rsplit(":", 1)
        if a is not None and b is not None:
            status, similarity = compare(a.text_raw, b.text_raw, profile.id)
        else:
            status, similarity = (ZL_ONLY if a is not None else IT_ONLY), None
        records.append(
            MismatchRecord(
                page_id=page_id,
                line_number=int(number),
                line_id=line_id,
                status=status,
                comparison_profile=profile.id,
                zl_text_raw=a.text_raw if a else None,
                it_text_raw=b.text_raw if b else None,
                zl_reading=profile.apply(a.markup) if a else None,
                it_reading=profile.apply(b.markup) if b else None,
                zl_locus_type=a.locus_code if a else None,
                it_locus_type=b.locus_code if b else None,
                zl_source_line=a.source_line if a else None,
                it_source_line=b.source_line if b else None,
                similarity_score=round(similarity, 6) if similarity is not None else None,
                sources_present=[sid for sid, src in sources.items() if line_id in src.loci],
            )
        )
    return records


def build_report(records: list[MismatchRecord], sources: dict[str, LoadedSource]) -> dict[str, Any]:
    """The build's own numbers: counts per status, agreement over the loci both sources have, and every parser warning."""
    counts = Counter(r.status for r in records)
    both = sum(counts[v] for v in VERDICTS)
    agreeing = sum(counts[v] for v in AGREEING)
    different = [
        r.similarity_score
        for r in records
        if r.status == "different" and r.similarity_score is not None
    ]
    return {
        "comparison_profile": records[0].comparison_profile if records else COMPARISON_PROFILE,
        "total_lines": len(records),
        "status_counts": {status: counts.get(status, 0) for status in STATUSES},
        "both_present": both,
        "agreeing": agreeing,
        "agreement_rate": agreeing / both if both else None,
        "different_rate": counts["different"] / both if both else None,
        "different_similarity": {
            "count": len(different),
            "median": statistics.median(different) if different else None,
        },
        "sources": {
            sid: {
                "file": src.path.name,
                "sha256": src.sha256,
                "loci_emitted": len(src.loci),
                "reported_loci": src.reported_loci,
                "warnings": src.warnings,
            }
            for sid, src in sources.items()
        },
    }


#: What each verdict means, for the erratum table.
VERDICT_LABELS = {
    "identical": "identical text (`text_raw` equal)",
    "same_reading": "same reading (word sequences equal under the profile)",
    "alternate_reading": "same reading for some choice among the alternates",
    "different": "different",
}


def erratum_table(report: dict[str, Any]) -> str:
    """The mismatch erratum's table and summary, rendered from the build report: the README, the dataset card and the
    CHANGELOG carry this text exactly, and the suite re-renders it from the committed report (item 1.8).
    """
    both = report["both_present"]
    counts = report["status_counts"]

    def share(n: int) -> str:
        return f"{100 * n / both:.1f}%"

    lines = [
        f"| Verdict, ZL against IT, profile `{report['comparison_profile']}` | Loci | Share of the {both:,} loci both hold |",
        "|---|---|---|",
    ]
    for verdict, label in VERDICT_LABELS.items():
        lines.append(f"| {label} | {counts[verdict]:,} | {share(counts[verdict])} |")
    median = report["different_similarity"]["median"]
    lines += [
        "",
        f"Agreement (identical, same reading, or an alternate's reading): {report['agreeing']:,} of {both:,} loci "
        f"({share(report['agreeing'])}). Different: {counts['different']:,} ({share(counts['different'])}), with a median "
        f"similarity of {median:.3f} among them. ZL only: {counts['zl_only']:,}; IT only: {counts['it_only']:,}.",
    ]
    return "\n".join(lines)


class MismatchIndexBuilder:
    """The builder as an object (the interface before item 1.8, kept): load sources one by one, then build.

    Every parser warning of a loaded source is logged at WARNING level and kept in ``stats["warnings"]`` under its source
    id, so a rejected locus is never accepted silently (AP4 F2, B-038).
    """

    def __init__(self, cache_dir: Path | None = None, output_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.sources: dict[str, LoadedSource] = {}
        self.stats: dict[str, Any] = {"sources_loaded": [], "warnings": {}}

    def load_transcription(self, source_id: str) -> bool:
        """Parse one cached source; True when it was read (its warnings are logged and recorded, never dropped)."""
        if source_id not in SOURCES or not (self.cache_dir / SOURCES[source_id]).exists():
            logger.warning("mismatch index: source %s not found in %s", source_id, self.cache_dir)
            return False
        source = load_source(source_id, self.cache_dir)
        self.sources[source_id] = source
        self.stats["sources_loaded"].append(source_id)
        self.stats["warnings"][source_id] = source.warnings
        for warning in source.warnings:
            logger.warning("%s: %s", source_id, warning)
        return True

    def build(self) -> list[MismatchRecord]:
        """Load every source not yet loaded and build the records."""
        for source_id in SOURCES:
            if source_id not in self.sources:
                self.load_transcription(source_id)
        if "zl" not in self.sources or "it" not in self.sources:
            raise ValueError("the mismatch index needs both ZL and IT")
        return build_records(self.sources)


def build_mismatch_index(
    cache_dir: Path | None = None, output_dir: Path | None = None
) -> dict[str, Any]:
    """Build `mismatch_index.jsonl`, its Parquet copy and `mismatch_report.json` into output_dir."""
    cache_dir = cache_dir or CACHE_DIR
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = {sid: load_source(sid, cache_dir) for sid in SOURCES}
    records = build_records(sources)
    report = build_report(records, sources)
    # The rows are checked against their schema before anything is written (B-023)
    from validators.schema import validate_mismatch_index

    valid, errors = validate_mismatch_index([r.to_dict() for r in records])
    if not valid:
        raise ValueError(f"mismatch rows break their schema: {errors[:5]}")
    jsonl = output_dir / "mismatch_index.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    import pyarrow as pa
    import pyarrow.parquet as pq

    pq.write_table(
        pa.Table.from_pylist([r.to_dict() for r in records]), output_dir / "mismatch_index.parquet"
    )
    (output_dir / "mismatch_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for sid, src in sources.items():
        for warning in src.warnings:
            logger.warning("%s: %s", sid, warning)
    return {"records": len(records), "report": report}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    result = build_mismatch_index()
    print(json.dumps(result["report"]["status_counts"], indent=2))
