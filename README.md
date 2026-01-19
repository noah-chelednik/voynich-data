# Voynich Computational Analysis Toolkit (VCAT) - Data

[![CI](https://github.com/noah-chelednik/voynich-data/actions/workflows/ci.yml/badge.svg)](https://github.com/noah-chelednik/voynich-data/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Rigorous infrastructure for studying an unknown structured artifact**

> 🎉 **Horizon 1 Complete:** All foundational datasets are built and ready for publication!

## Overview

This repository contains the data processing infrastructure for the Voynich Computational Analysis Toolkit (VCAT). It provides:

- **Parsers** for IVTFF-format transcription files
- **Validators** for EVA character sets and data integrity
- **Builders** for creating Hugging Face datasets
- **Documentation** of data models, sources, and methodology

## Datasets

### Available Datasets

| Dataset | Records | Description |
|---------|---------|-------------|
| **voynich-eva** | 4,072 | Line-level EVA transcription from ZL source |
| **voynich-manuscript-metadata** | 226 pages, 102 folios, 18 quires | Structured codicological metadata |
| **voynich-transcription-mismatch** | 4,072 | Cross-transcription comparison (5 sources) |

### Quick Load (from HuggingFace)

```python
from datasets import load_dataset

# EVA transcription
ds = load_dataset("Ched-ai/voynich-eva")
print(f"Lines: {len(ds['train'])}")  # 4,072

# Metadata
pages = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")
folios = load_dataset("Ched-ai/voynich-manuscript-metadata", "folios")
quires = load_dataset("Ched-ai/voynich-manuscript-metadata", "quires")

# Cross-transcription comparison
mismatch = load_dataset("Ched-ai/voynich-transcription-mismatch")
```

## Data Sources

This project processes five transcription sources:

| Source | Alphabet | Lines | Description |
|--------|----------|-------|-------------|
| ZL (Zandbergen-Landini) | EVA | 4,072 | Primary reference, most complete |
| IT (Takahashi) | EVA | 4,069 | Secondary EVA transcription |
| CD (Currier/D'Imperio) | Currier | 2,154 | Historical Currier alphabet |
| FG (Friedman Study Group) | FSG | 3,980 | NSA research group |
| GC (Glen Claston) | v101 | 4,070 | High-granularity alphabet |

See `data_sources/sources.yaml` for complete source documentation.

## Mismatch Index Statistics

Cross-transcription comparison (ZL vs IT):

- **Total EVA agreement rate: 83.9%**
- Exact matches: 901 (22.1%)
- Normalized matches: 293 (7.2%)
- High similarity (≥95%): 2,220 (54.6%)
- Content mismatches: 655 (16.1%)

## Local Build

```bash
# Clone the repository
git clone https://github.com/noah-chelednik/voynich-data.git
cd voynich-data

# Install dependencies (requires Python 3.11+)
pip install -e ".[dev]"

# Download source files
python scripts/fetch_sources.py

# Build all datasets
python -m builders.build_eva_lines
python -m builders.build_metadata
python -m builders.build_mismatch_index

# Run tests
pytest tests/
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
├── tests/                 # Test suite (343 tests)
└── docs/                  # Documentation
```

## Documentation

- [Data Model](docs/data_model.md) - Page IDs, line numbering, metadata structure
- [Sources](docs/sources.md) - Detailed source documentation
- [Decisions](docs/decisions.md) - Design decision log
- [EVA Alphabet](docs/eva_alphabet.md) - Character set reference
- [Charset Decisions](docs/charset_decisions.md) - Character set covenant

## Related Projects

This is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- **voynich-data** (this repo) - Data processing infrastructure ✅
- **voynich-analysis** (planned) - Statistical analysis tools
- **voynich-hypotheses** (planned) - Hypothesis testing framework

## Contributing

Contributions welcome! Please:

1. Check existing issues before opening a new one
2. Run tests and linting before submitting PRs
3. Document any methodology changes

## License

MIT License - See [LICENSE](LICENSE) for details.

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
  author = {VCAT Contributors},
  title = {Voynich Computational Analysis Toolkit - Data},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/noah-chelednik/voynich-data}
}
```

---

*This project does not claim to solve the Voynich Manuscript. It builds infrastructure for rigorous study.*
