# Voynich Computational Analysis Toolkit (VCAT) - Data

[![CI](https://github.com/noah-chelednik/voynich-data/actions/workflows/ci.yml/badge.svg)](https://github.com/noah-chelednik/voynich-data/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Datasets-Ched--ai-yellow)](https://huggingface.co/Ched-ai)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23685580.svg)](https://doi.org/10.5281/zenodo.23685580)

**A faithful, tested distribution of the Voynich Manuscript transliterations**

This is release 1.0.0: every locus of the source, the source text kept exactly, and every number checked against the build.
The release before it, 0.2.3, had the defects listed in [ERRATA.md](ERRATA.md); `CHANGELOG.md` says what changed and how to
migrate.

## Overview

This repository contains the data processing infrastructure for the Voynich Computational Analysis Toolkit (VCAT). It provides:

- **Parsers** for IVTFF-format transcription files
- **Validators** for EVA character sets and data integrity
- **Builders** for creating Hugging Face datasets
- **Documentation** of data models, sources, and methodology

## Datasets

### This build

<!-- readme:datasets:start (rendered by builders.cards.readme_datasets_table from output/; checked by tests/test_paperwork.py) -->
| Dataset | Rows in this build | Description |
|---|---|---|
| **voynich-eva** | 5,385 | One row per locus of the ZL transliteration |
| **voynich-manuscript-metadata** | 227 pages, 102 folios, 18 quires | Page, folio and quire metadata |
| **voynich-transcription-mismatch** | 5,386 | ZL against IT, one row per locus of either |
| **voynich-transliterations** | 55,370 readings; 5,390 loci and 38,357 alignments in the variant tables | Every cached transliteration in one schema, one row per reading, one config per source; the variant tables (not a consensus) |
<!-- readme:datasets:end -->

### Quick Load (from Hugging Face)

```python
from datasets import load_dataset

# EVA transcription
ds = load_dataset("Ched-ai/voynich-eva")

# Metadata
pages = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")
folios = load_dataset("Ched-ai/voynich-manuscript-metadata", "folios")
quires = load_dataset("Ched-ai/voynich-manuscript-metadata", "quires")

# Cross-transcription comparison
mismatch = load_dataset("Ched-ai/voynich-transcription-mismatch")

# Every cached transliteration, each in its own alphabet (new in 1.0.0)
zl = load_dataset("Ched-ai/voynich-transliterations", "zl")
```

## Data Sources

The transliterations published on voynich.nu are cached in `data_sources/cache/`, each recorded in `data_sources/sources.yaml`
with its URL, SHA-256, upstream version and license (CC0-1.0, as voynich.nu states; `docs/SOURCES_LICENSE.md`). Every one is
built into `voynich-transliterations`, in one schema; ZL also feeds the EVA and metadata datasets, ZL and IT the mismatch index:

<!-- readme:sources:start (rendered by builders.cards.readme_sources_table from data_sources/; checked by tests/test_paperwork.py) -->
| Source | Alphabet | Readings (locus lines) | Upstream version | Used by |
|---|---|---|---|---|
| ZL: Zandbergen-Landini transliteration (ZL), EVA | EVA | 5,385 | Version 3b of 13/05/2025 | voynich-eva, voynich-manuscript-metadata, voynich-transcription-mismatch, voynich-transliterations |
| IT: Takahashi transliteration (IT), EVA, extracted from the Landini-Stolfi interlinear file | EVA | 5,215 | Version 1a of 27/12/2022 | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| IT2a: Takahashi transliteration (IT), EVA, version 2a, extracted from the Landini-Stolfi interlinear file | EVA | 5,215 | Version 2a of 02/02/2023 modified 25/06/2025 | voynich-eva, voynich-transliterations |
| CD: Currier transliteration (CD), Currier alphabet | Currier | 2,196 | IVTFF version 2a of 02/02/2023 | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| FG: First Study Group transliteration (FG), FSG alphabet | FSG | 4,060 | IVTFF version 2a of 02/02/2023 | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| GC: Glen Claston transliteration (GC), v101 alphabet | v101 | 5,367 | IVTFF version 2a of 05/02/2023 modified 25/06/2025 | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| RF1b: Reference transliteration (RF1b), EVA, full form | EVA | 5,385 | v. 1b | voynich-eva, voynich-transliterations |
| VT: voynichese.com transliteration (VT), EVA, mainly by Takeshi Takahashi | EVA | 5,207 | v. 0e | voynich-eva, voynich-transliterations |
| LSI: Landini-Stolfi interlinear file (LSI), EVA, several transliterations per locus | EVA | 17,340 | Release 1.6e6 - ?? Dec 1998 | voynich-eva, voynich-transliterations |
<!-- readme:sources:end -->

`vcat-verify` checks the cache against that record (see Local Build).

## Cross-Transcription Comparison (ZL vs IT)

How often do the two major EVA transliterations, Zandbergen's (ZL) and Takahashi's (IT), agree, locus by locus?

**Erratum (2026-10-17, roadmap item 1.8).** Version 0.2.3 published that the two EVA transliterations agree on 83.9% of
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

Most differences are small (see the median similarity), but they are differences: any analysis built on a single
transliteration inherits them, and the mismatch dataset lists them locus by locus. VCAT does not pick a reading (no consensus).

## Local Build

```bash
# Clone the repository
git clone https://github.com/noah-chelednik/voynich-data.git
cd voynich-data

# Install dependencies (requires Python 3.11+)
pip install -e ".[dev]"

# Check the cached sources against data_sources/sources.yaml (writes reports/source_verification.json)
vcat-verify

# Fetch any cached source that is missing, checking its pinned SHA-256 (network; the cache is committed)
python scripts/fetch_sources.py

# Build all datasets into output/
python -m builders.build_eva_lines
python -m builders.build_eva_words
python -m builders.build_metadata --parquet
python -m builders.build_mismatch_index
python -m builders.build_transliterations   # every source, and the variant tables
python -m builders.stage_release            # the Hub repositories, locally, into release/staging/ (git-ignored)

# Run the suite (no path: pytest.ini's testpaths include the reviewer proofs)
pytest
```

From the checkout, `vcat.load(source=, unit=, profile=)` reads the build without the network:

```python
import vcat

lines = vcat.load()                                   # ZL's lines under analysis-v1
it_words = vcat.load(source="IT", unit="word")        # IT's words, cut by the EVA tokenizer
raw = vcat.load(source="LSI", unit="line", profile="raw-v1")
```

## Project Structure

```
voynich-data/
├── data_sources/          # Source configuration and downloads
│   ├── sources.yaml       # Source definitions
│   └── cache/             # Downloaded source files
├── vcat/                  # Core library
├── parsers/               # IVTFF parsers
├── builders/              # Dataset builders
├── validators/            # Data validation
├── schemas/               # JSON schemas
├── huggingface/           # HuggingFace export
├── notebooks/             # Usage examples
├── tests/                 # Test suite (with tests/regressions, the reviewer proofs)
└── docs/                  # Documentation
```

## Documentation

- [Data Model](docs/data_model.md) - Page IDs, line numbering, metadata structure
- [Stability policy](STABILITY.md) - What stays stable between releases: versions, identifiers, deprecations
- [Errata](ERRATA.md) - Every correction to published data
- [Sources](docs/sources.md) - Detailed source documentation
- [Reference Checks](docs/reference_checks.md) - The build's counts and entropies against published values
- [Upstream Tracking](docs/upstream_tracking.md) - The weekly check against voynich.nu and the source diff
- [Decisions](docs/decisions.md) - Design decision log
- [EVA Alphabet](docs/eva_alphabet.md) - Character set reference
- [Charset Decisions](docs/charset_decisions.md) - The 0.2.x character set record (superseded by the data model)

## Related Projects

This is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- **voynich-data** (this repo) - Data processing infrastructure
- **voynich-analysis** (planned) - Statistical analysis tools
- **voynich-hypotheses** (planned) - Hypothesis testing framework

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
checks, and ground rules.

## License

- **Code:** MIT License - See [LICENSE](LICENSE) for details.
- **Data:** every cached source is recorded as CC0-1.0, on voynich.nu's statement; every dataset also carries VCAT's own
  annotations, so all four datasets are CC-BY-4.0; the source-derived fields stay CC0-1.0. Each source's statement is in `data_sources/sources.yaml`; the
  per-source matrix is [docs/SOURCES_LICENSE.md](docs/SOURCES_LICENSE.md).
- **The cached source files** in `data_sources/cache/` are their authors' work, redistributed as the matrix records.

## Acknowledgments

This project builds on decades of transcription work by:
- René Zandbergen (voynich.nu, ZL transcription)
- Gabriel Landini (EVA alphabet, EVMT project)
- Jorge Stolfi (interlinear file, UNICAMP archive)
- Takeshi Takahashi (first complete transcription)
- Prescott Currier (statistical analysis, Currier alphabet)
- First Study Group / William Friedman (early transcription)
- Lisa Fagin Davis (hand identification)

## Citation

If you use this data in your research, please cite:

```bibtex
@misc{vcat-data,
  author = {Chelednik, Noah},
  title = {Voynich Computational Analysis Toolkit - Data},
  year = {2026},
  version = {1.0.0},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.23685586},
  url = {https://github.com/noah-chelednik/voynich-data}
}
```

This is the DOI of release 1.0.0. To cite whichever release is the latest, use [10.5281/zenodo.23685580](https://doi.org/10.5281/zenodo.23685580); every
release has its own DOI on [Zenodo](https://doi.org/10.5281/zenodo.23685580).

---

*This project does not claim to solve the Voynich Manuscript. It builds infrastructure for rigorous study.*
