"""
Metadata Dataset Builder
========================

Builder for creating manuscript metadata datasets from IVTFF transcription files.

This module creates three related datasets:
    - Pages dataset: Page-level metadata (one record per page)
    - Folios dataset: Folio-level metadata (one record per folio/leaf)
    - Quires dataset: Quire-level metadata (one record per gathering)

Example:
    >>> from builders import build_metadata_datasets
    >>> result = build_metadata_datasets("data_sources/cache/ZL3b-n.txt")
    >>> print(f"Pages: {len(result.pages)}, Folios: {len(result.folios)}, Quires: {len(result.quires)}")
    Pages: 226, Folios: 113, Quires: 20
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from parsers import (
    FolioRecord,
    IVTFFParser,
    MetadataExtractionResult,
    PageRecord,
    QuireRecord,
    extract_all_metadata,
)


@dataclass
class MetadataBuildReport:
    """Report from metadata dataset build process.

    Contains statistics and provenance information about the built datasets.
    """

    source_file: str
    source_hash: str
    build_timestamp: str
    build_version: str = "0.2.3"

    # Page stats
    total_pages: int = 0
    pages_with_text: int = 0
    pages_by_section: dict[str, int] = field(default_factory=dict)
    pages_by_language: dict[str, int] = field(default_factory=dict)
    pages_by_hand: dict[str, int] = field(default_factory=dict)

    # Folio stats
    total_folios: int = 0
    foldout_folios: int = 0
    missing_folios: int = 0

    # Quire stats
    total_quires: int = 0
    complete_quires: int = 0

    # Line stats
    total_lines: int = 0
    total_labels: int = 0

    # Output info
    output_dir: str = ""
    pages_file: str = ""
    folios_file: str = ""
    quires_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class MetadataBuildResult:
    """Result of metadata dataset build process.

    Contains the extracted metadata and build report.
    """

    pages: list[PageRecord]
    folios: list[FolioRecord]
    quires: list[QuireRecord]
    report: MetadataBuildReport

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "folios": [f.to_dict() for f in self.folios],
            "quires": [q.to_dict() for q in self.quires],
            "report": self.report.to_dict(),
        }


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        filepath: Path to the file

    Returns:
        First 12 characters of SHA256 hash
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:12]


def build_metadata_datasets(
    source_path: str | Path,
    output_dir: str | Path | None = None,
) -> MetadataBuildResult:
    """Build metadata datasets from an IVTFF transcription file.

    Extracts page, folio, and quire metadata from the given transcription
    file and optionally exports to JSONL format.

    Args:
        source_path: Path to the IVTFF transcription file
        output_dir: Optional output directory for JSONL files

    Returns:
        MetadataBuildResult with extracted metadata and build report
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Compute source hash
    source_hash = compute_file_hash(source_path)

    # Parse IVTFF file
    parser = IVTFFParser()
    pages = list(parser.parse_file(source_path))

    # Extract metadata
    metadata_result = extract_all_metadata(
        pages, source_file=source_path.name, source_hash=source_hash
    )

    # Build report
    report = _build_report(
        metadata_result,
        source_path=source_path,
        source_hash=source_hash,
    )

    result = MetadataBuildResult(
        pages=metadata_result.pages,
        folios=metadata_result.folios,
        quires=metadata_result.quires,
        report=report,
    )

    # Export if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        export_metadata(result, output_dir)

        # Update report with output info
        result.report.output_dir = str(output_dir)
        result.report.pages_file = str(output_dir / "pages.jsonl")
        result.report.folios_file = str(output_dir / "folios.jsonl")
        result.report.quires_file = str(output_dir / "quires.jsonl")

    return result


def _build_report(
    metadata: MetadataExtractionResult,
    source_path: Path,
    source_hash: str,
) -> MetadataBuildReport:
    """Build a metadata build report.

    Args:
        metadata: Extracted metadata result
        source_path: Path to source file
        source_hash: SHA256 hash of source file

    Returns:
        MetadataBuildReport with statistics
    """
    # Count pages with text
    pages_with_text = sum(1 for p in metadata.pages if p.has_text)

    # Count by section
    pages_by_section: dict[str, int] = {}
    for p in metadata.pages:
        section = p.section.value if p.section else "unknown"
        pages_by_section[section] = pages_by_section.get(section, 0) + 1

    # Count by language
    pages_by_language: dict[str, int] = {}
    for p in metadata.pages:
        lang = p.currier_language or "unknown"
        pages_by_language[lang] = pages_by_language.get(lang, 0) + 1

    # Count by hand
    pages_by_hand: dict[str, int] = {}
    for p in metadata.pages:
        hand = p.hand or "unknown"
        pages_by_hand[hand] = pages_by_hand.get(hand, 0) + 1

    # Count folios
    foldout_folios = sum(1 for f in metadata.folios if f.is_foldout)
    missing_folios = sum(1 for f in metadata.folios if f.is_missing)

    # Count quires
    complete_quires = sum(1 for q in metadata.quires if q.is_complete)

    # Total lines and labels
    total_lines = sum(p.line_count for p in metadata.pages)
    total_labels = sum(p.label_count for p in metadata.pages)

    return MetadataBuildReport(
        source_file=source_path.name,
        source_hash=source_hash,
        build_timestamp=datetime.now(UTC).isoformat(),
        total_pages=len(metadata.pages),
        pages_with_text=pages_with_text,
        pages_by_section=pages_by_section,
        pages_by_language=pages_by_language,
        pages_by_hand=pages_by_hand,
        total_folios=len(metadata.folios),
        foldout_folios=foldout_folios,
        missing_folios=missing_folios,
        total_quires=len(metadata.quires),
        complete_quires=complete_quires,
        total_lines=total_lines,
        total_labels=total_labels,
    )


def export_metadata(result: MetadataBuildResult, output_dir: Path) -> None:
    """Export metadata to JSONL files.

    Creates three JSONL files:
        - pages.jsonl: Page-level metadata
        - folios.jsonl: Folio-level metadata
        - quires.jsonl: Quire-level metadata
        - metadata_report.json: Build report

    Args:
        result: MetadataBuildResult to export
        output_dir: Directory to write output files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export pages
    pages_path = output_dir / "pages.jsonl"
    with open(pages_path, "w", encoding="utf-8") as f:
        for page in result.pages:
            f.write(json.dumps(page.to_dict(), ensure_ascii=False) + "\n")

    # Export folios
    folios_path = output_dir / "folios.jsonl"
    with open(folios_path, "w", encoding="utf-8") as f:
        for folio in result.folios:
            f.write(json.dumps(folio.to_dict(), ensure_ascii=False) + "\n")

    # Export quires
    quires_path = output_dir / "quires.jsonl"
    with open(quires_path, "w", encoding="utf-8") as f:
        for quire in result.quires:
            f.write(json.dumps(quire.to_dict(), ensure_ascii=False) + "\n")

    # Export report
    report_path = output_dir / "metadata_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result.report.to_dict(), f, indent=2, ensure_ascii=False)


def export_to_parquet(result: MetadataBuildResult, output_dir: Path) -> None:
    """Export metadata to Parquet files.

    Creates three Parquet files:
        - pages.parquet: Page-level metadata
        - folios.parquet: Folio-level metadata
        - quires.parquet: Quire-level metadata

    Args:
        result: MetadataBuildResult to export
        output_dir: Directory to write output files
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:
        raise ImportError(
            "pyarrow is required for Parquet export. Install with: pip install pyarrow"
        ) from e

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export pages
    pages_data = [_flatten_page_dict(p.to_dict()) for p in result.pages]
    pages_table = pa.Table.from_pylist(pages_data)
    pq.write_table(pages_table, output_dir / "pages.parquet")

    # Export folios
    folios_data = [_flatten_folio_dict(f.to_dict()) for f in result.folios]
    folios_table = pa.Table.from_pylist(folios_data)
    pq.write_table(folios_table, output_dir / "folios.parquet")

    # Export quires
    quires_data = [q.to_dict() for q in result.quires]
    quires_table = pa.Table.from_pylist(quires_data)
    pq.write_table(quires_table, output_dir / "quires.parquet")


def _flatten_page_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested section dict for Parquet export."""
    result = dict(d)
    if isinstance(result.get("section"), dict):
        section = result.pop("section")
        result["section_value"] = section.get("value")
        result["section_attribution"] = section.get("attribution")
        result["section_confidence"] = section.get("confidence")
        result["section_disputed"] = section.get("disputed")
    return result


def _flatten_folio_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested section dict for Parquet export."""
    result = dict(d)
    if isinstance(result.get("section"), dict):
        section = result.pop("section")
        result["section_value"] = section.get("value")
        result["section_attribution"] = section.get("attribution")
        result["section_confidence"] = section.get("confidence")
        result["section_disputed"] = section.get("disputed")
    # Convert list to string for Parquet compatibility
    if "verso_page_ids" in result:
        result["verso_page_ids"] = (
            ",".join(result["verso_page_ids"]) if result["verso_page_ids"] else ""
        )
    return result


if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="Build metadata datasets from IVTFF transcription files"
    )
    arg_parser.add_argument(
        "source",
        help="Path to IVTFF transcription file",
    )
    arg_parser.add_argument(
        "-o",
        "--output",
        default="output/metadata",
        help="Output directory (default: output/metadata)",
    )
    arg_parser.add_argument(
        "--parquet",
        action="store_true",
        help="Also export to Parquet format",
    )

    args = arg_parser.parse_args()

    print(f"Building metadata datasets from: {args.source}")
    result = build_metadata_datasets(args.source, args.output)

    print("\nBuild complete:")
    print(f"  Pages: {result.report.total_pages}")
    print(f"  Folios: {result.report.total_folios}")
    print(f"  Quires: {result.report.total_quires}")
    print(f"  Total lines: {result.report.total_lines}")
    print(f"\nOutput written to: {args.output}")

    if args.parquet:
        export_to_parquet(result, Path(args.output))
        print("Parquet files also exported")

    print("\nLanguage distribution:")
    for lang, count in sorted(result.report.pages_by_language.items()):
        print(f"  {lang}: {count} pages")

    print("\nSection distribution:")
    for section, count in sorted(result.report.pages_by_section.items()):
        print(f"  {section}: {count} pages")
