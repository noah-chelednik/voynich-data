"""
VCAT Builders Module
====================

Dataset builders for VCAT outputs.

This module provides builders that transform parsed transcription data
into standardized dataset formats suitable for publication on HuggingFace
and analysis.

Main functions:
    build_eva_lines: Build the EVA lines dataset from parsed IVTFF data
    build_metadata_datasets: Build page/folio/quire metadata datasets
    build_mismatch_index: Build cross-transcription comparison index
    run_smoke_test: Run validation smoke tests on the built dataset

Classes:
    LineRecord: Dataclass representing a single line in the dataset
    BuildReport: Dataclass containing build statistics and metadata
    PageRecord: Page-level metadata record
    FolioRecord: Folio-level metadata record
    QuireRecord: Quire-level metadata record
    MetadataBuildResult: Result from metadata build process
    MetadataBuildReport: Report from metadata build process
    MismatchRecord: Cross-transcription comparison record
    MismatchIndexBuilder: Builder for mismatch index

Example:
    >>> from builders import build_eva_lines, run_smoke_test
    >>> records, report = build_eva_lines(
    ...     source_path="data_sources/raw_sources/ZL3b-n.txt",
    ...     output_dir="output"
    ... )
    >>> len(records)
    4072
    >>> report.page_count
    226
    >>> run_smoke_test("output/eva_lines.parquet")
    True

    >>> from builders import build_metadata_datasets
    >>> result = build_metadata_datasets("ZL3b-n.txt", "output/metadata")
    >>> len(result.pages)
    226

    >>> from builders import build_mismatch_index
    >>> result = build_mismatch_index()
    >>> result['records_count']
    4072

Output formats:
    - Parquet: Efficient columnar format for analysis
    - JSONL: Human-readable line-delimited JSON
"""

from __future__ import annotations

# Re-export from parsers for convenience
from parsers import (
    FolioRecord,
    PageRecord,
    QuireRecord,
)

from .build_eva_lines import (
    BuildReport,
    LineRecord,
    build_eva_lines,
    run_smoke_test,
)
from .build_metadata import (
    MetadataBuildReport,
    MetadataBuildResult,
    build_metadata_datasets,
    export_metadata,
)
from .build_metadata import (
    export_to_parquet as export_metadata_to_parquet,
)
from .build_mismatch_index import (
    MismatchIndexBuilder,
    MismatchRecord,
    TranscriptionLine,
    build_mismatch_index,
)

__all__ = [
    # EVA Lines Builder
    "BuildReport",
    "LineRecord",
    "build_eva_lines",
    "run_smoke_test",
    # Metadata Builder
    "MetadataBuildReport",
    "MetadataBuildResult",
    "build_metadata_datasets",
    "export_metadata",
    "export_metadata_to_parquet",
    # Mismatch Index Builder
    "MismatchIndexBuilder",
    "MismatchRecord",
    "TranscriptionLine",
    "build_mismatch_index",
    # Metadata Records (from parsers)
    "PageRecord",
    "FolioRecord",
    "QuireRecord",
]
