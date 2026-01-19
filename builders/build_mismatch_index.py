"""
Mismatch Index Builder for VCAT.

Compares transcription sources to identify disagreements and create
a cross-transcription alignment dataset.

Primary comparison: ZL (Zandbergen-Landini) vs IT (Takahashi) - both EVA-based
Secondary tracking: CD, FG, GC presence/absence
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from parsers.ivtff_parser import IVTFFParser

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "data_sources" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class TranscriptionLine:
    """A single line from a transcription."""

    page_id: str
    line_number: int
    line_id: str
    text_raw: str
    text_clean: str
    source_id: str


@dataclass
class MismatchRecord:
    """Record of comparison between transcription sources for a single line."""

    # Identifiers
    page_id: str
    line_number: int
    line_id: str

    # Primary comparison (EVA-based: ZL vs IT)
    zl_text: str | None = None
    it_text: str | None = None

    # Secondary transcriptions (presence/absence + text)
    cd_text: str | None = None  # Currier alphabet
    fg_text: str | None = None  # FSG alphabet
    gc_text: str | None = None  # v101 alphabet

    # Comparison results
    status: str = (
        "unknown"  # exact_match, normalized_match, content_mismatch, missing_some, zl_only, it_only
    )
    eva_agreement: bool | None = None
    similarity_score: float | None = None

    # Source tracking
    sources_present: list[str] = field(default_factory=list)
    sources_missing: list[str] = field(default_factory=list)

    # Notes
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MismatchIndexBuilder:
    """Builder for transcription mismatch index."""

    # Transcription configs
    TRANSCRIPTION_CONFIGS = {
        "zl": {
            "file": "ZL3b-n.txt",
            "name": "Zandbergen-Landini",
            "alphabet": "eva",
            "is_eva": True,
        },
        "it": {
            "file": "IT_ivtff_1a.txt",
            "name": "Takahashi",
            "alphabet": "eva",
            "is_eva": True,
        },
        "cd": {
            "file": "CD2a-n.txt",
            "name": "Currier-DImpero",
            "alphabet": "currier",
            "is_eva": False,
        },
        "fg": {
            "file": "FG2a-n.txt",
            "name": "Friedman-Study-Group",
            "alphabet": "fsg",
            "is_eva": False,
        },
        "gc": {
            "file": "GC2a-n.txt",
            "name": "Glen-Claston",
            "alphabet": "v101",
            "is_eva": False,
        },
    }

    def __init__(self, cache_dir: Path | None = None, output_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.parser = IVTFFParser()

        # Storage for parsed transcriptions: {source_id: {line_id: TranscriptionLine}}
        self.transcriptions: dict[str, dict[str, TranscriptionLine]] = {}

        # All unique line_ids across all sources
        self.all_line_ids: set[str] = set()

        # Statistics
        self.stats: dict[str, Any] = {
            "sources_loaded": [],
            "total_lines": 0,
            "exact_matches": 0,
            "normalized_matches": 0,
            "content_mismatches": 0,
            "zl_only_lines": 0,
            "it_only_lines": 0,
            "both_eva_present": 0,
            "per_source_counts": {},
        }

    def load_transcription(self, source_id: str) -> bool:
        """Load a single transcription file."""
        config = self.TRANSCRIPTION_CONFIGS.get(source_id)
        if not config:
            logger.error(f"Unknown source_id: {source_id}")
            return False

        filepath = self.cache_dir / config["file"]
        if not filepath.exists():
            logger.warning(f"Transcription file not found: {filepath}")
            return False

        try:
            # Parse the file
            pages = self.parser.parse_file(filepath)

            # Index by line_id
            lines_dict: dict[str, TranscriptionLine] = {}
            for page in pages:
                for locus in page.loci:
                    line_id = locus.locus_id  # Already formatted as page_id:locus_number

                    line = TranscriptionLine(
                        page_id=locus.page_id,
                        line_number=locus.locus_number,
                        line_id=line_id,
                        text_raw=locus.raw_locator,
                        text_clean=locus.text,
                        source_id=source_id,
                    )
                    lines_dict[line_id] = line
                    self.all_line_ids.add(line_id)

            self.transcriptions[source_id] = lines_dict
            self.stats["sources_loaded"].append(source_id)
            self.stats["per_source_counts"][source_id] = len(lines_dict)

            logger.info(f"Loaded {source_id}: {len(lines_dict)} lines from {config['file']}")
            return True

        except Exception as e:
            logger.error(f"Failed to parse {source_id}: {e}")
            return False

    def load_all_transcriptions(self) -> int:
        """Load all available transcription files."""
        loaded = 0
        for source_id in self.TRANSCRIPTION_CONFIGS:
            if self.load_transcription(source_id):
                loaded += 1
        return loaded

    @staticmethod
    def normalize_eva_text(text: str) -> str:
        """Normalize EVA text for comparison.

        Removes:
        - Uncertain markers (?, !)
        - Editorial markers (<>, {}, [])
        - Multiple spaces
        - Leading/trailing whitespace
        """
        if not text:
            return ""

        # Remove uncertainty markers
        normalized = text.replace("?", "").replace("!", "").replace("*", "")

        # Remove editorial markers content
        import re

        normalized = re.sub(r"<[^>]*>", "", normalized)  # <...>
        normalized = re.sub(r"\{[^}]*\}", "", normalized)  # {...}
        normalized = re.sub(r"\[[^\]]*\]", "", normalized)  # [...]

        # Normalize spaces
        normalized = " ".join(normalized.split())

        return normalized.strip()

    @staticmethod
    def compute_similarity(text1: str, text2: str) -> float:
        """Compute similarity ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def compare_eva_lines(
        self, zl_text: str | None, it_text: str | None
    ) -> tuple[str, bool | None, float | None]:
        """Compare two EVA transcriptions.

        Returns:
            tuple of (status, eva_agreement, similarity_score)
        """
        if zl_text is None and it_text is None:
            return "both_missing", None, None

        if zl_text is None:
            return "zl_missing", None, None

        if it_text is None:
            return "it_missing", None, None

        # Exact match
        if zl_text == it_text:
            return "exact_match", True, 1.0

        # Normalized comparison
        zl_norm = self.normalize_eva_text(zl_text)
        it_norm = self.normalize_eva_text(it_text)

        if zl_norm == it_norm:
            return "normalized_match", True, 1.0

        # Compute similarity
        similarity = self.compute_similarity(zl_norm, it_norm)

        # High similarity threshold
        if similarity >= 0.95:
            return "high_similarity", True, similarity

        return "content_mismatch", False, similarity

    def build_record(self, line_id: str) -> MismatchRecord:
        """Build a mismatch record for a single line_id."""
        # Parse line_id
        parts = line_id.split(":")
        page_id = parts[0]
        line_number = int(parts[1]) if len(parts) > 1 else 0

        # Get text from each transcription
        zl_line = self.transcriptions.get("zl", {}).get(line_id)
        it_line = self.transcriptions.get("it", {}).get(line_id)
        cd_line = self.transcriptions.get("cd", {}).get(line_id)
        fg_line = self.transcriptions.get("fg", {}).get(line_id)
        gc_line = self.transcriptions.get("gc", {}).get(line_id)

        # Build record
        record = MismatchRecord(
            page_id=page_id,
            line_number=line_number,
            line_id=line_id,
            zl_text=zl_line.text_clean if zl_line else None,
            it_text=it_line.text_clean if it_line else None,
            cd_text=cd_line.text_clean if cd_line else None,
            fg_text=fg_line.text_clean if fg_line else None,
            gc_text=gc_line.text_clean if gc_line else None,
        )

        # Track source presence
        for src_id in ["zl", "it", "cd", "fg", "gc"]:
            if self.transcriptions.get(src_id, {}).get(line_id):
                record.sources_present.append(src_id)
            else:
                record.sources_missing.append(src_id)

        # Compare EVA sources
        status, agreement, similarity = self.compare_eva_lines(record.zl_text, record.it_text)
        record.status = status
        record.eva_agreement = agreement
        record.similarity_score = similarity

        # Add notes
        if status == "content_mismatch" and similarity is not None and similarity < 0.5:
            record.notes.append(f"Low similarity: {similarity:.2%}")

        return record

    def build(self) -> list[MismatchRecord]:
        """Build the complete mismatch index."""
        logger.info("Building mismatch index...")

        # Load all transcriptions
        loaded = self.load_all_transcriptions()
        logger.info(f"Loaded {loaded} transcription sources")

        if "zl" not in self.transcriptions:
            raise ValueError("ZL (primary) transcription is required")

        # Build records for all line_ids
        records: list[MismatchRecord] = []

        for line_id in sorted(self.all_line_ids):
            record = self.build_record(line_id)
            records.append(record)

            # Update statistics
            if record.status == "exact_match":
                self.stats["exact_matches"] += 1
            elif record.status == "normalized_match":
                self.stats["normalized_matches"] += 1
            elif record.status == "high_similarity":
                self.stats["high_similarity_matches"] = (
                    self.stats.get("high_similarity_matches", 0) + 1
                )
            elif record.status == "content_mismatch":
                self.stats["content_mismatches"] += 1
            elif record.status == "zl_missing":
                self.stats["it_only_lines"] += 1
            elif record.status == "it_missing":
                self.stats["zl_only_lines"] += 1

            if record.zl_text and record.it_text:
                self.stats["both_eva_present"] += 1

        self.stats["total_lines"] = len(records)

        logger.info(f"Built mismatch index with {len(records)} records")
        return records

    def export_jsonl(self, records: list[MismatchRecord], output_path: Path | None = None) -> Path:
        """Export records to JSONL format."""
        output_path = output_path or (self.output_dir / "mismatch_index.jsonl")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        logger.info(f"Exported {len(records)} records to {output_path}")
        return output_path

    def export_report(self, output_path: Path | None = None) -> Path:
        """Export build statistics report."""
        output_path = output_path or (self.output_dir / "mismatch_report.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate additional statistics
        total_agreeing = (
            self.stats["exact_matches"]
            + self.stats["normalized_matches"]
            + self.stats.get("high_similarity_matches", 0)
        )
        report = {
            **self.stats,
            "total_agreeing": total_agreeing,
            "agreement_rate": (
                total_agreeing / self.stats["both_eva_present"]
                if self.stats["both_eva_present"] > 0
                else 0
            ),
            "eva_coverage": {
                "zl": self.stats["per_source_counts"].get("zl", 0),
                "it": self.stats["per_source_counts"].get("it", 0),
                "both": self.stats["both_eva_present"],
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Exported report to {output_path}")
        return output_path

    def generate_summary_stats(self) -> dict[str, Any]:
        """Generate summary statistics for dataset card."""
        total = self.stats["total_lines"]
        both_eva = self.stats["both_eva_present"]
        total_agreeing = (
            self.stats["exact_matches"]
            + self.stats["normalized_matches"]
            + self.stats.get("high_similarity_matches", 0)
        )

        return {
            "total_lines": total,
            "eva_both_present": both_eva,
            "eva_exact_match": self.stats["exact_matches"],
            "eva_normalized_match": self.stats["normalized_matches"],
            "eva_high_similarity_match": self.stats.get("high_similarity_matches", 0),
            "eva_content_mismatch": self.stats["content_mismatches"],
            "eva_total_agreeing": total_agreeing,
            "eva_agreement_rate": (
                f"{(total_agreeing / both_eva * 100):.1f}%" if both_eva > 0 else "N/A"
            ),
            "lines_zl_only": self.stats["zl_only_lines"],
            "lines_it_only": self.stats["it_only_lines"],
            "sources_loaded": self.stats["sources_loaded"],
            "per_source_line_counts": self.stats["per_source_counts"],
        }


def build_mismatch_index(
    cache_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Main entry point for building mismatch index.

    Returns:
        Dictionary with build results and paths
    """
    logging.basicConfig(level=logging.INFO)

    builder = MismatchIndexBuilder(cache_dir=cache_dir, output_dir=output_dir)

    # Build index
    records = builder.build()

    # Export
    jsonl_path = builder.export_jsonl(records)
    report_path = builder.export_report()
    summary = builder.generate_summary_stats()

    return {
        "success": True,
        "records_count": len(records),
        "output_jsonl": str(jsonl_path),
        "output_report": str(report_path),
        "summary": summary,
    }


if __name__ == "__main__":
    result = build_mismatch_index()
    print(json.dumps(result, indent=2))
