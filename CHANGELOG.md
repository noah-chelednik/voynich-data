# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

## [1.0.0] - 2026-01-18

### Added - Mismatch Index (Phase 5)
- **Mismatch Index Builder** (`builders/build_mismatch_index.py`): Cross-transcription comparison
  - `MismatchRecord`: Line-by-line comparison across 5 transcription sources
  - `MismatchIndexBuilder`: Builder class for constructing the index
  - `TranscriptionLine`: Representation of a single line from any transcription
  - Comparison of EVA-based transcriptions (ZL vs IT) with similarity scoring
  - Presence/absence tracking for Currier, FSG, and v101 transcriptions
  - Normalization logic for robust comparison (removes uncertainty markers)
  - Statistics generation for dataset card
  
- **Multi-Transcription Support**: Now parses and compares 5 transcription sources:
  - ZL (Zandbergen-Landini, EVA) - 4,072 lines - Primary reference
  - IT (Takahashi, EVA) - 4,069 lines - Secondary EVA
  - CD (Currier/D'Imperio) - 2,154 lines - Currier alphabet
  - FG (Friedman Study Group) - 3,980 lines - FSG alphabet
  - GC (Glen Claston, v101) - 4,070 lines - High-granularity

- **Mismatch Index Tests** (`tests/test_mismatch_index.py`): 26 comprehensive tests
  - Normalization tests
  - Similarity computation tests
  - Line comparison tests (exact, normalized, mismatch, missing)
  - Integration tests with mock transcriptions
  - Output validation tests

- **HuggingFace Export Structure**: Complete export directories
  - `huggingface/voynich-eva-transcription/` - EVA transcription dataset
  - `huggingface/voynich-manuscript-metadata/` - Metadata (pages, folios, quires)
  - `huggingface/voynich-transcription-mismatch/` - Mismatch index
  - Full dataset cards (README.md) for each dataset

### Changed
- Builders module now exports mismatch index builder

### Mismatch Index Statistics
- Total lines: 4,072
- EVA both present: 4,069
- Exact matches: 901 (22.1%)
- Normalized matches: 293 (7.2%)
- High similarity (≥95%): 2,220 (54.6%)
- Content mismatches: 655 (16.1%)
- **Total EVA agreement rate: 83.9%**

### Milestone: Horizon 1 Complete
- ✅ EVA transcription dataset (4,072 lines)
- ✅ Metadata dataset (226 pages, 102 folios, 18 quires)
- ✅ Mismatch index (4,072 comparison records)
- ✅ HuggingFace export structure with dataset cards
- ✅ 350+ tests passing
- ✅ Ready for GitHub + HuggingFace publication

## [0.2.3] - 2026-01-18

### Added
- **Metadata Parser** (`parsers/metadata_parser.py`): Complete metadata extraction system
  - `PageRecord`: Page-level metadata with section, language, hand, illustration type
  - `FolioRecord`: Folio-level metadata aggregating pages
  - `QuireRecord`: Quire-level metadata aggregating folios
  - `UncertainValue`: Structured representation for disputed/uncertain fields
  - `ManuscriptSection` and `IllustrationType` enums
  - `SECTION_MAPPING`: Folio-to-section mapping based on scholarly consensus
  - `FOLDOUT_PAGES`: Known foldout panel configurations (f85v, f86v)
  - `MISSING_FOLIOS`: List of known missing folio numbers
  - `extract_all_metadata()`: Convenience function for full metadata extraction

- **Metadata Builder** (`builders/build_metadata.py`): Dataset builder for metadata
  - `build_metadata_datasets()`: Build pages, folios, quires datasets from IVTFF
  - `export_metadata()`: Export to JSONL format
  - `export_to_parquet()`: Export to Parquet format (flattened schema)
  - `MetadataBuildResult` and `MetadataBuildReport` dataclasses
  - CLI interface for standalone metadata building

- **Metadata Tests** (`tests/test_metadata.py`): 42 comprehensive tests
  - Page ID parsing and validation
  - Section mapping and boundary detection
  - Foldout page detection
  - Page, Folio, Quire record extraction
  - Integration tests with real ZL transcription data

### Changed
- `parsers/__init__.py`: Now exports all metadata parser classes and functions
- `builders/__init__.py`: Now exports metadata builder functions and record types

### Output Files (from ZL3b-n.txt)
- `pages.jsonl` / `pages.parquet`: 226 page records
- `folios.jsonl` / `folios.parquet`: 102 folio records  
- `quires.jsonl` / `quires.parquet`: 18 quire records
- `metadata_report.json`: Build statistics and provenance

### Statistics
- Total tests: 324 (282 existing + 42 new metadata tests)
- Languages: A=114, B=82, unknown=30 pages
- Sections: herbal_a=48, herbal_b=70, astronomical=26, biological=20, cosmological=6, pharmaceutical=32, recipes=24
- Hands: 1=113, 2=46, 3=33, 4=26, 5=7 pages
- Foldout folios: 10, Missing folios: 4

## [0.2.2] - 2026-01-18

### Fixed
- **Documentation**: README statistics now match build report (170,564 chars, 33,711 words)
- **Documentation**: Example record in README now matches actual data (text_clean without @254;, section="text_only", illustration_type="T")
- **Tests**: Fixed test expecting 12-char source hash in report (now correctly expects 64-char full hash)
- **Tests**: Fixed test expecting high-ASCII removal (policy is lossless preservation)
- **Tests**: Fixed test fixtures missing required `line_index` field
- **Tests**: All validator edge case tests now include required schema fields

### Changed
- Test suite now passes 275/275 tests (was 267 passing with 8 failures)

## [0.2.1] - 2026-01-18

### Fixed
- Build report now shows `pages_with_lines` (206) vs `total_pages_in_source` (226) correctly
- `text_clean` properly strips ALL IVTFF markup (angle brackets, curly braces, alternatives)
- `text_clean` strips uncertainty markers after flag computation (not before)
- Alternative bracket handling fixed for empty alternatives like `[:ch]` or `[a:]`
- Uppercase 'I' (1 occurrence at f48r.13) normalized to lowercase 'i'

### Added
- Centralized text processing module (`vcat/text_processing.py`) - single source of truth
- Centralized charset module (`vcat/charset.py`) with locked definitions per version
- Charset covenant: locked per version, documented in `docs/charset_decisions.md`
- Cross-platform reproducibility: JSONL uses `newline='\n'` for byte-identical output
- SHA256SUMS file generated with JSONL hash (CI fails hard if missing or empty)
- Release manifest with `sort_keys=True` for stable diffing between releases
- Empirical charset analysis script (`scripts/analyze_charset.py`)
- Source fetch script (`scripts/fetch_sources.py`) with verified hash
- Invariant verification system (`validators/verify_invariants.py`)
- Contract invariant tests (`tests/test_invariants.py`)
- Release acceptance tests (`tests/test_release_v0_2_1.py`)
- Apostrophe (') added to VARIANT_CHARS (27 legitimate occurrences)
- 'j' added to EVA_CORE (14 occurrences, was missing)

### Changed
- Builder and verifier now use SAME authoritative stripping logic from centralized module
- Reproducibility scope explicitly JSONL only (Parquet is content-equivalent but not hash-guaranteed)
- CI verifies SHA256SUMS exists and contains valid hash
- Source hash is now full 64-character SHA256 (was truncated to 12)
- Text cleaning policy updated to `centralized_v0.2.1`

### Contract (Horizon 1)
- **text_clean**: Contains ONLY characters from `ALLOWED_TEXT_CLEAN_CHARSET`
- **Flags**: Computed via centralized `strip_ivtff_markup()` before marker removal
- **Ordering**: Deterministic by `(folio_number, side, panel, line_index)`
- **Reproducibility**: JSONL with canonical JSON serialization (`sort_keys=True`, `separators=(',',':')`) + Unix newlines
- **Charset**: Locked for v0.2.x per `docs/charset_decisions.md`

## [0.2.0] - 2026-01-17

### Added
- `line_index` field: Sequential 1..n index per page (no gaps, unlike `line_number`)
- `has_high_ascii` field: Boolean flag for lines containing `@NNN;` codes
- `has_high_ascii_codes()` method in IVTFFParser for detecting high-ASCII codes
- `format_options` in build report: Captures full IVTFF header options (e.g., "2.0 M 5")
- `text_clean_policy` in build report: Tracks cleaning policy version for reproducibility
- `lines_with_high_ascii` count in build report statistics
- `py.typed` marker for PEP 561 type checking support
- `CITATION.cff` for academic citation support
- `.pre-commit-config.yaml` for automated code quality
- `docs/ZENODO_SETUP.md` for DOI setup instructions
- CI jobs for mypy type checking and pip-audit security scanning

### Changed
- **BREAKING**: `text_clean` now preserves `@NNN;` high-ASCII codes (previously stripped)
  - This fixes data loss where 9 lines became empty after cleaning
  - Cleaning policy is now "lossless_v1"
- Updated dataset card with accurate licensing statement
- Updated JSON schema to include new fields
- Updated documentation to reflect schema changes

### Fixed
- 9 lines that became empty after cleaning now preserve their `@NNN;` content
- Build report now captures full IVTFF version including options

## [0.1.0] - 2026-01-17

### Added
- IVTFF parser for Voynich transcription files (IVTFF 2.0 format)
- EVA character set validation module with comprehensive character definitions
- EVA lines dataset builder producing Parquet and JSONL output
- Dataset card for HuggingFace publication
- Source verification utilities for checking data source accessibility
- Comprehensive documentation suite:
  - `docs/data_model.md` — Data model specification
  - `docs/sources.md` — Data source documentation
  - `docs/eva_alphabet.md` — EVA character reference
  - `docs/decisions.md` — Project decision log
- JSON schemas for data validation
- Example notebook for loading datasets
- CI/CD pipeline with GitHub Actions
- Unit and integration tests

### Notes
- **Pre-1.0 Release**: Schema may change without notice in 0.x versions
- **Primary Source**: Zandbergen-Landini (ZL) v3b transcription
- **Dataset Statistics**: 226 pages, 4,072 lines, 170,607 characters

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.2.1 | 2026-01-18 | Centralized text processing, charset covenant, SHA256SUMS, CI hardening |
| 0.2.0 | 2026-01-17 | Lossless text_clean, line_index, licensing fix |
| 0.1.0 | 2026-01-17 | Initial release with EVA lines dataset |

[Unreleased]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/noah-chelednik/voynich-data/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/noah-chelednik/voynich-data/releases/tag/v0.1.0
