"""
VCAT Parsers Module
===================

Parsers for Voynich manuscript transcription file formats.

This module provides parsers for:
    - IVTFF (Intermediate Voynich Transliteration File Format) files
      used by voynich.nu and other sources
    - Manuscript metadata extraction from IVTFF page headers

Main classes:
    IVTFFParser: Parser for IVTFF format transcription files
    Page: Represents a parsed manuscript page with metadata
    Locus: Represents a single text locus (line of text)
    PageVariables: Page-level metadata from IVTFF headers

    MetadataParser: Parser for extracting structured metadata
    PageRecord: Page-level metadata record
    FolioRecord: Folio-level metadata record
    QuireRecord: Quire-level metadata record

Convenience functions:
    parse_ivtff: Parse an IVTFF file and return pages
    extract_all_metadata: Extract all metadata from parsed pages

Example:
    >>> from parsers import parse_ivtff, extract_all_metadata
    >>> pages = list(parse_ivtff("path/to/transcription.txt"))
    >>> len(pages)
    226
    >>> pages[0].page_id
    'f1r'
    >>> pages[0].loci[0].text
    'fachys.ykal.ar.ataiin...'
    >>> metadata = extract_all_metadata(pages)
    >>> len(metadata.folios)
    113

Format specification: http://www.voynich.nu/software/ivtt/IVTFF_format.pdf
"""

from __future__ import annotations

from .ivtff_parser import (
    IVTFFParser,
    Locus,
    LocusPosition,
    LocusType,
    Page,
    PageVariables,
    parse_ivtff,
)
from .metadata_parser import (
    FOLDOUT_PAGES,
    MISSING_FOLIOS,
    SECTION_MAPPING,
    FolioRecord,
    IllustrationType,
    ManuscriptSection,
    MetadataExtractionResult,
    MetadataParser,
    PageRecord,
    QuireRecord,
    UncertainValue,
    extract_all_metadata,
)

__all__ = [
    # IVTFF Parser
    "IVTFFParser",
    "Locus",
    "LocusPosition",
    "LocusType",
    "Page",
    "PageVariables",
    "parse_ivtff",
    # Metadata Parser
    "MetadataParser",
    "PageRecord",
    "FolioRecord",
    "QuireRecord",
    "UncertainValue",
    "ManuscriptSection",
    "IllustrationType",
    "MetadataExtractionResult",
    "extract_all_metadata",
    "SECTION_MAPPING",
    "FOLDOUT_PAGES",
    "MISSING_FOLIOS",
]
