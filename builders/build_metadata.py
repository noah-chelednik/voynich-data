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
    >>> len(result.pages) == result.report.total_pages
    True
"""

from __future__ import annotations

import hashlib
import json
import sys
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
from parsers.metadata_parser import BifolioRecord, PageOrderRecord
from vcat.iiif import load_canvases, page_links
from vcat.layers import load_layers, metadata_layer_names
from vcat.sources import ROOT, registered_source, repo_relative, require_licensed, source_file

DEFAULT_SOURCE = source_file("ZL")  # from data_sources/sources.yaml (B-081)


def _package_version() -> str:
    """The package version, from its one definition (`vcat.__version__`, kept equal to pyproject.toml by the suite)."""
    from vcat import __version__

    return __version__


@dataclass
class MetadataBuildReport:
    """Report from metadata dataset build process.

    Contains statistics and provenance information about the built datasets.
    """

    source_file: str
    source_hash: str
    build_timestamp: str
    build_version: str = field(default_factory=lambda: _package_version())

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

    # Physical structure (roadmap item 2.5): bifolia from the page headers' $Q and $B, and the named page orders
    total_bifolia: int = 0
    incomplete_bifolia: int = 0
    page_orders: list[str] = field(default_factory=list)

    # Line stats
    total_lines: int = 0
    total_labels: int = 0

    # Lines the parser did not accept (AP2 F1, DECISIONS Q27): each warning, and the loci and
    # pages it reported instead of emitting
    warnings: list[str] = field(default_factory=list)
    reported_loci: list[str] = field(default_factory=list)
    reported_pages: list[str] = field(default_factory=list)

    # Output info
    output_dir: str = ""
    pages_file: str = ""
    folios_file: str = ""
    quires_file: str = ""
    bifolia_file: str = ""
    page_orders_file: str = ""
    layers_file: str = ""
    page_canvases_file: str = ""

    # Links to Yale's images (roadmap item 2.4): the manifest the canvases were read from, and the page-to-canvas links
    iiif_manifest: str = ""
    iiif_manifest_sha256: str = ""
    total_page_canvases: int = 0
    partial_page_canvases: int = 0

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
    bifolia: list[BifolioRecord] = field(default_factory=list)
    page_orders: list[PageOrderRecord] = field(default_factory=list)
    #: The transliteration this build read, which its layers name (`metadata_layer_names`): the registry finds it by
    #: identity and bytes before name, so a renamed copy keeps its own (review d66fcb6d finding 1); None means the
    #: report's file name
    source_path: Path | None = None
    #: The links and the layers as the build made them, kept so every export of the result writes the same rows,
    #: whatever happens to the input or the canvas extract afterwards (review 2e53e1c4 finding 2, B-111); None means
    #: computed when the tables are asked for (a result assembled by hand)
    page_canvases: list[dict[str, Any]] | None = None
    layers: list[dict[str, Any]] | None = None

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        """Each exported table by its file stem, as rows: what the JSONL holds and, with the same structure, the Parquet
        (B-095: no table is flattened, so each Parquet file holds exactly its JSONL's rows)."""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "folios": [f.to_dict() for f in self.folios],
            "quires": [q.to_dict() for q in self.quires],
            "bifolia": [b.to_dict() for b in self.bifolia],
            "page_orders": [o.to_dict() for o in self.page_orders],
            # who each classification is attributed to and its license (roadmap item 2.8; data_sources/layers.yaml)
            # naming the transliteration this build read (review 7454c2f9 finding 3)
            # each page's links to Yale's images of it (roadmap item 2.4; vcat/iiif.py)
            "page_canvases": (
                self.page_canvases
                if self.page_canvases is not None
                else page_links([p.page_id for p in self.pages], load_canvases()["canvases"])
            ),
            "layers": (
                self.layers
                if self.layers is not None
                else load_layers(
                    None, *metadata_layer_names(self.source_path or self.report.source_file)
                )
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {**self.tables(), "report": self.report.to_dict()}


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
    require_licensed(source_path)  # before anything is read or written (S12)

    # Compute source hash
    source_hash = compute_file_hash(source_path)

    # Parse IVTFF file
    parser = IVTFFParser()
    pages = list(parser.parse_file(source_path))

    # Extract metadata
    registered = registered_source(source_path)  # names its file order (review 020f7450 finding 1)
    metadata_result = extract_all_metadata(
        pages,
        source_file=source_path.name,
        source_hash=source_hash,
        source_id=registered.id if registered else None,
        source_name=registered.name if registered else None,
    )

    # Build report
    report = _build_report(
        metadata_result,
        source_path=source_path,
        source_hash=source_hash,
    )
    report.warnings = [f"parser: {w}" for w in parser.warnings]
    report.reported_loci = [w.locus_id for w in parser.warnings if w.locus_id]
    report.reported_pages = [w.page_id for w in parser.warnings if w.page_id]

    result = MetadataBuildResult(
        pages=metadata_result.pages,
        folios=metadata_result.folios,
        quires=metadata_result.quires,
        bifolia=metadata_result.bifolia,
        page_orders=metadata_result.page_orders,
        report=report,
        source_path=source_path,
    )
    canvases = load_canvases()
    links = page_links([p.page_id for p in result.pages], canvases["canvases"])
    # the build's own links and layers, kept: an export later writes these, not a fresh reading (review 2e53e1c4 finding 2,
    # B-111)
    result.page_canvases = links
    result.layers = load_layers(None, *metadata_layer_names(source_path))
    report.iiif_manifest = canvases["manifest"]
    report.iiif_manifest_sha256 = canvases["manifest_sha256"]
    report.total_page_canvases = len(links)
    report.partial_page_canvases = sum(1 for link in links if link["coverage"] == "part")

    # Export if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # export_metadata records the output paths in the report before writing it, so the persisted
        # report is the one returned (AB1 F6, B-071), relative to the repository
        export_metadata(result, output_dir)

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
        section_key: str = p.section.value if (p.section and p.section.value) else "unknown"
        pages_by_section[section_key] = pages_by_section.get(section_key, 0) + 1

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
        total_bifolia=len(metadata.bifolia),
        incomplete_bifolia=sum(1 for b in metadata.bifolia if not b.is_complete),
        page_orders=sorted({o.order for o in metadata.page_orders}),
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

    # The report records this export's destinations, whoever calls it (AB2 F4, B-082)
    result.report.output_dir = repo_relative(output_dir)
    result.report.pages_file = repo_relative(output_dir / "pages.jsonl")
    result.report.folios_file = repo_relative(output_dir / "folios.jsonl")
    result.report.quires_file = repo_relative(output_dir / "quires.jsonl")
    result.report.bifolia_file = repo_relative(output_dir / "bifolia.jsonl")
    result.report.page_orders_file = repo_relative(output_dir / "page_orders.jsonl")
    result.report.layers_file = repo_relative(output_dir / "layers.jsonl")
    result.report.page_canvases_file = repo_relative(output_dir / "page_canvases.jsonl")

    for stem, rows in result.tables().items():
        with open(output_dir / f"{stem}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

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

    # Every table with its JSONL rows' own structure: nested values stay nested, nothing is dropped (B-095: the
    # flattened copies lost a section's alternatives and could not be checked against the JSONL)
    for stem, rows in result.tables().items():
        pq.write_table(pa.Table.from_pylist(rows), output_dir / f"{stem}.parquet")


def main(argv: list[str] | None = None) -> int:
    """Build the metadata datasets; the exit status is 1 when the parser did not accept a source line.

    With no arguments it builds from the cached ZL file into output/metadata, as the README says (D8).
    """
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="Build metadata datasets from IVTFF transcription files"
    )
    arg_parser.add_argument(
        "source",
        nargs="?",
        default=str(DEFAULT_SOURCE),
        help="Path to IVTFF transcription file (default: data_sources/cache/ZL3b-n.txt)",
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

    args = arg_parser.parse_args(argv)
    # Relative paths are relative to the repository, as for the EVA builder
    source = Path(args.source) if Path(args.source).is_absolute() else ROOT / args.source
    output = Path(args.output) if Path(args.output).is_absolute() else ROOT / args.output

    print(f"Building metadata datasets from: {repo_relative(source)}")
    result = build_metadata_datasets(source, output)

    print("\nBuild complete:")
    print(f"  Pages: {result.report.total_pages}")
    print(f"  Folios: {result.report.total_folios}")
    print(f"  Quires: {result.report.total_quires}")
    print(f"  Total lines: {result.report.total_lines}")
    print(f"\nOutput written to: {repo_relative(output)}")

    if args.parquet:
        export_to_parquet(result, output)
        print("Parquet files also exported")

    print("\nLanguage distribution:")
    for lang, count in sorted(result.report.pages_by_language.items()):
        print(f"  {lang}: {count} pages")

    print("\nSection distribution:")
    for section, count in sorted(result.report.pages_by_section.items()):
        print(f"  {section}: {count} pages")

    # Lines the parser did not accept fail the command, after the report is written (Q27)
    if result.report.warnings:
        print(f"\n{len(result.report.warnings)} source line(s) not accepted:")
        for warning in result.report.warnings:
            print(f"  - {warning}")
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
