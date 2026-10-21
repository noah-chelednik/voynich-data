# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-25

The first release since 0.2.3, and a major one: the EVA rows are every locus of the source, read faithfully, and the
release adds the metadata structure, the word level, every cached transliteration and their variant tables. The row
counts below are the build's (`output/`).

### Migration from 0.2.3

- **`voynich-eva`, configuration `default`** (the lines): 5,385 rows where 0.2.3 had 4,072, every locus of ZL 3b (labels,
  circles and radii included, and the `fRos` page). `text_raw` is the source's text byte for byte; `text_clean` is the
  named profile `analysis-v1` (ligatures kept as their glyphs, `<->` a word space: D1 and D2 of `ERRATA.md`). Every
  configuration name and file path of 0.2.3 still loads (`tests/test_staging.py`); new configurations add the words
  (39,018 rows) and the other layers.
- **`voynich-transcription-mismatch`**: 5,386 rows, one per locus either ZL or IT holds, with new verdicts; the 0.2.3
  agreement figures were wrong in method (the erratum below and in `ERRATA.md`).
- **`voynich-manuscript-metadata`**: 227 pages, 102 folios, 18 quires, 52 bifolia, two page orders, the page-to-canvas
  links to Yale's images and the attributed layers; VCAT's section judgements are marked as VCAT's.
- **`voynich-transliterations`** (new): the nine cached transliterations, 55,370 rows, each in its own alphabet, with the
  variant tables of the EVA readers.
- **Licenses**: every dataset is CC-BY-4.0 (each carries VCAT's annotations); the source-derived fields stay CC0-1.0. 0.2.3
  declared `other`.
- **Python**: `vcat.load(source=, unit=, profile=)` reads every source at line or word level, and ZL at page level.

### Fixed
- Mismatch index rebuilt (roadmap item 1.8). Erratum: Version 0.2.3 published that the two EVA transliterations agree on 83.9% of
lines and disagree substantively on 16.1%. Those numbers were wrong in method: the comparison deleted ligatures and alternate
readings, fused words at drawing breaks, did not count an uncertain space as a space, covered only the 4,072 loci the old parser
kept, and counted any line at least 95% similar as agreeing. The index is now built on the named profile `analysis-v1`
(`vcat/profiles.py`), with exact verdicts and no similarity threshold (`vcat/comparison.py`); the similarity score is kept as a
description only. The rebuilt comparison:

<!-- erratum:mismatch-1.8:start (rendered by builders.build_mismatch_index.erratum_table from output/mismatch_report.json; checked by tests/test_mismatch_index.py) -->
| Verdict, ZL against IT, profile `analysis-v1` | Loci | Share of the 5,214 loci both hold |
|---|---|---|
| identical text (`text_raw` equal) | 1,161 | 22.3% |
| same reading (word sequences equal under the profile) | 1,323 | 25.4% |
| same reading for some choice among the alternates | 101 | 1.9% |
| different | 2,629 | 50.4% |

Agreement (identical, same reading, or an alternate's reading): 2,585 of 5,214 loci (49.6%). Different: 2,629 (50.4%), with a median similarity of 0.973 among them. ZL only: 171; IT only: 1.
<!-- erratum:mismatch-1.8:end -->

### Added (roadmap item 2.1, upstream tracking)
- A weekly check that voynich.nu still serves every pinned source (`.github/workflows/upstream.yml`,
  `scripts/check_upstream.py`): an issue on a change, a failed run on an unreachable source, never an adoption. The source
  diff, loci added, removed and changed (`vcat/upstream.py`, `scripts/source_diff.py`, `docs/upstream_tracking.md`).

### Added (roadmap item 2.10, reference checks)
- Acceptance tests against published values (`tests/test_reference_checks.py`, `docs/reference_checks.md`): the character
  counts and the single and conditional character entropies of ZL, FG and CD, and ZL's word tokens and types, each within
  an argued tolerance of a value quoted from voynich.nu (`data_sources/references.yaml`: the page, its SHA-256, the quote,
  the tolerance and why); the statistics in `vcat/reference.py`; `scripts/check_references.py` checks the quotes against
  the pinned pages. Every check names the damage it is shown to fail on (markup left in, uncertain readings
  kept, loci lost, word division lost), and the suite shows it failing there.

### Added (roadmap item 2.9, the API and the configurations)
- `vcat.load(source=, unit=, profile=)`: the build's rows of any cached source, as lines, words or (ZL) pages, read under any
  profile, offline.
- Every table as a configuration of `voynich-eva` (its card lists them); `python -m builders.stage_release` builds each Hub
  repository locally into `release/staging/` (git-ignored). Every configuration name and file of the 0.2.3 cards still
  loads. `voynich-eva`'s license becomes CC-BY-4.0 for the VCAT layers it now holds; its lines, words and per-source text
  stay CC0 (DECISIONS Q86).

### Changed (roadmap item 2.9)
- The EVA `section` is described as the source's renaming (the layer `section_name`) in the schema and the data model's
  opening, and the data model no longer says only ZL is published (B-118).

### Added (roadmap item 2.7, the variant tables, not a consensus)
- The transliterations dataset's `locus_variants` and `word_alignments` configurations (`python -m builders.build_variants`,
  also run by `builders.build_transliterations`): every EVA reader's words of each locus side by side, the agreement and the
  distinct readings, a labelled majority baseline (null on a tie, never the default), and each reader's words aligned to
  ZL's by Needleman-Wunsch (`vcat/variants.py`). No consensus reading. The dataset's license becomes CC-BY-4.0 for VCAT's
  comparison (the layer `variants`); the per-source fields stay CC0 (DECISIONS Q84).
- `docs/sources.md` states that no mapping between alphabets is applied; the mapping tables of roadmap 2.3 are deferred
  (DECISIONS Q82).

### Added (roadmap item 2.6, the word level)
- The EVA dataset's `words` configuration (`output/eva_words.jsonl`, `.parquet`, `eva_words_report.json`; `python -m
  builders.build_eva_words`): one row per word of the lines, with its position in its line and in the source's paragraph
  (`<%>` to `<$>`), the space after it (`certain` or `uncertain`) and its line's hand, Currier language, section and quire.
  Both validators recompute every row from the lines.
- `vcat/words.py`, the one EVA tokenizer, documented; the lines' `word_count` now uses it (every committed count unchanged).

### Added (roadmap item 2.4, links to Yale's images)
- The metadata dataset's `page_canvases` configuration: each page's links to the canvases of Yale University Library's
  IIIF manifest of Beinecke MS 408 that it lies on, `coverage` `whole` or `part` as Yale's labels say, with the canvas's
  IIIF id and image service. The canvases are read into `data_sources/iiif/yale-2002046-canvases.json` (`python -m
  vcat.iiif --fetch`), pinned to the manifest's SHA-256. Links only; no image is copied. A layer `iiif_links` (VCAT's,
  CC-BY-4.0) attributes the mapping.

### Changed (roadmap item 2.4)
- The layers `illustration_type` and `currier_language` name ZL (voynich-eva) and the metadata's source in separate
  clauses (they read "as ZL and ZL record them" for a ZL build).

### Added (roadmap item 2.8, attribution of the interpretive layers)
- `data_sources/layers.yaml`, published as the metadata dataset's `layers` configuration: every field that records a
  classification, whether a source states it or VCAT judges it, whose classification it is and its own license (the
  source's CC0-1.0, VCAT's CC-BY-4.0).

### Changed (roadmap item 2.8)
- The metadata `section` (VCAT's folio ranges) is attributed to VCAT (`attribution: vcat`), where it named voynich.nu.
- A sheet with one leaf in the source says only that, with the quire's folios missing from the manuscript, instead of
  calling its conjugate lost: a partial transliteration omits leaves the manuscript keeps (B-106).
- Both validators require a Boolean `is_complete` (B-107), every metadata table's whole population (B-108), the metadata
  report's source hash and totals (B-109), the mismatch rows in their documented order (B-099) and the EVA report's
  unrecognized lines (B-100).

### Added (roadmap item 2.5, the physical structure layer)
- `voynich-manuscript-metadata` gains `bifolia` (one row per sheet: the leaves of a quire whose page headers share a bifolio
  number, conjugate; a sheet with one leaf lost its conjugate) and `page_orders` (one row per page per named order:
  `foliation`, the default, and `zl_file`, ZL's own order, each with who defines it).

### Changed (roadmap item 2.5)
- The metadata Parquet files hold exactly their JSONL's rows, nested values included; they used to flatten `section`
  (dropping its `alternatives`) and join the page-id lists into strings (B-095). Both validators check every metadata
  table and recompute the bifolia and the orders from the source.
- A folio whose pages' Currier languages tie has no predominant language, with a note, where the choice depended on the
  hash seed (B-091; no cached source has such a folio).

### Added (roadmap item 2.3, part 2: every source in one schema)
- The dataset `voynich-transliterations`: one row per reading of one locus in each of the nine cached transliterations,
  keyed by Zandbergen's page and locus ids and the locus type, each in its own alphabet and exactly as written; one config
  per source; the coverage matrix (`coverage_matrix.csv`, the readings of each source on each page); its build report lists
  every line the parser does not accept. `docs/sources.md` states how the sources depend on each other and renders the
  coverage per source.

### Fixed (roadmap item 2.3, part 2b)
- The mismatch loader refuses a source with repeated locus ids instead of keeping the last reading (B-076, B-089).
- A registry verdict that is not a Boolean (`license_verified: "false"`) is refused (B-092).
- The cards' table checks compare the whole displayed table, so an added field row fails (B-096).
- `docs/data_model.md` names the per-source encoding, the format-1.6 paragraph rule and LSI's listed lines (B-097), and says
  which sources `sources_present` evaluates (B-090).

### Added (roadmap item 2.3, part 2: every source parsed)
- The Landini-Stolfi interlinear file (LSI) is cached and parsed with the others: each cached file is read in the encoding
  its record states (LSI is Latin-1), every one rebuilds byte for byte, and every reading of every locus is emitted or
  reported. Four LSI lines that number a locus `44a`, which IVTFF does not allow, are reported and listed in its record.

### Fixed (roadmap item 2.3, part 2)
- Parallel readings of an interlinear file have their own paragraphs (B-049); a paragraph end needs a start only from
  format 1.6, which introduced the start mark; only the first line is the file header (B-050); `$L=@` and every other
  `$X=@` are accepted, the value unset (B-051). The one page whose header sets `$H=@` (`f115r`, 45 rows) now has `hand`
  null in `voynich-eva` and `voynich-manuscript-metadata`, where it carried the literal `@`.

### Added (roadmap item 2.3, part 1: the sources fetched and pinned)
- Every transliteration voynich.nu publishes that the roadmap names is pinned in `data_sources/sources.yaml` by URL, SHA-256
  and upstream version; RF1b (full EVA), VT and the current IT (2a) are cached beside ZL, IT 1a, CD, FG and GC. The
  Landini-Stolfi interlinear file (LSI) and RF1b's basic form were pinned but not cached, each with its reason; LSI has
  since been cached and built (item 2.3), RF1b's basic form is still pinned only.
- License verdicts: voynich.nu's statement that the transliterations in its tables are CC0 is quoted in
  `docs/SOURCES_LICENSE.md`, with the table each file is linked from; every source is CC0-1.0. The mismatch dataset's card
  license is therefore `cc-by-4.0` (VCAT's comparison), its text CC0-1.0.

### Fixed (roadmap item 2.3, part 1)
- IT 1a's recorded URL was not where voynich.nu publishes it (it is under `data/previous/`).
- `scripts/fetch_sources.py` fetches every cached source, and moves a download into the cache only when it has the pinned
  SHA-256 (it used to leave a mismatching download in the cache).

### Added (roadmap items 2.2 and 2.11, stability and errata)
- `STABILITY.md`: SemVer for the data (what each version part may change), permanent identifiers (`page_id`,
  `line_id`, profile ids: never reused, never silently changed), deprecations announced one release ahead.
- `ERRATA.md`, seeded with the Phase 1 corrections of 0.2.3 (D1 to D8), and issue templates for data bugs and
  transcription errors (reported upstream, never corrected here).

### Changed (roadmap item 1.9, paperwork)
- One version (`pyproject.toml`, `vcat.__version__`, `CITATION.cff`, the `voynich-eva` card, the metadata build report),
  checked by `tests/test_paperwork.py`; the mislabelled "1.0.0" heading below corrected.
- `data_sources/sources.yaml` rewritten: every cached file with its URL, SHA-256, upstream version and license statement,
  checked against the cache by the suite. `docs/SOURCES_LICENSE.md` holds the per-source license matrix rendered from it: ZL
  CC0-1.0 (per voynich.nu, verified at the license check); IT, CD, FG and GC, whose files state no license, were since
  recorded as CC0-1.0 on voynich.nu's statement (S12). It no longer says the
  source files are not redistributed: they are, in `data_sources/cache/`.
- Dataset licenses followed from their sources here (`voynich-eva` CC0-1.0, `voynich-manuscript-metadata` CC-BY-4.0,
  `voynich-transcription-mismatch` per source); since DECISIONS Q86 every dataset is CC-BY-4.0, as each carries VCAT's
  annotations. The cards gained a Known Limitations section and lost their "complete transcription" claims; their field tables,
  statistics and example rows are rendered from the schema, the record classes and the build. The stale 0.2.3 data copies in
  the card directories were removed (a release uploads `output/`).
- `vcat-verify` checks the cache against `sources.yaml` offline, writes `reports/source_verification.json` and renders the
  Markdown receipt from it (the old receipt said PASS while the JSON said FAIL); it is now packaged, so the console script
  imports.
- CI runs `pytest` with no positional path (the regression tests run), and its smoke step runs
  the builder's checks (it only imported the module).
- Build reports name no local path (`source_file` and the metadata output paths are relative to the repository) and time
  stamps are UTC instants (`+00:00`; the EVA builder wrote local time with a `Z`). The persisted metadata report is the one
  returned. A requested Parquet export that fails now fails the build, and the release manifest lists only the files the
  build wrote. The release manifest names `docs/data_model.md` as its contract (`docs/charset_decisions.md`, the 0.2.x
  covenant, is marked superseded), and records whether the source is the one `sources.yaml` pins (`source.pinned`); both
  validators check its source hash against the build.
- `load_schema("transcription_lines")` and the other documented short names work. Named `vcat.*` loggers write through the
  stream and level `configure_logging` sets.
- The README commands work (`python -m builders.build_metadata` exited 2 without a source argument); the notebooks run in the
  suite, offline, and are committed without outputs. `docs/progress.md` no longer presents the 0.2.x checklist as complete.

## [0.2.3, continued] - 2026-01-18

This entry was headed "1.0.0" by mistake: no version 1.0.0 has been released, and the work below shipped in 0.2.3
(roadmap item 1.9, one version everywhere).

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
- ✅ 350 tests defined, 343 passing (corrected 2026-10-21: the entry said "350+"; 7 tests skipped without the raw source)
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
- Uppercase 'I' (1 occurrence, at f57v.3; corrected 2026-10-21: the entry said f48r.13, a locus ZL does not hold) normalized to lowercase 'i'

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
- Apostrophe (') added to VARIANT_CHARS (27 legitimate occurrences, as first reported; corrected 2026-10-21: the count does not reproduce from the 0.2.3 build)
- 'j' added to EVA_CORE (14 occurrences, was missing; as first reported, the count does not reproduce from the 0.2.3 build)

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
| 1.0.0 | 2026-10-25 | Every locus, faithful text, metadata structure, words, every transliteration; CC-BY-4.0 |
| 0.2.3 | 2026-01-18 | Metadata parser and dataset (pages, folios, quires) |
| 0.2.2 | 2026-01-18 | Documentation and test corrections |
| 0.2.1 | 2026-01-18 | Centralized text processing, charset covenant, SHA256SUMS, CI hardening |
| 0.2.0 | 2026-01-17 | Lossless text_clean, line_index, licensing fix |
| 0.1.0 | 2026-01-17 | Initial release with EVA lines dataset |

[Unreleased]: https://github.com/noah-chelednik/voynich-data/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.3...v1.0.0
[0.2.3]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/noah-chelednik/voynich-data/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/noah-chelednik/voynich-data/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/noah-chelednik/voynich-data/releases/tag/v0.1.0
