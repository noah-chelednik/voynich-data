# Publishing Guide

What a release publishes, from where, and what must pass first. VCAT publishes once per release, with the maintainer's approval of
each step; nothing in this guide is run by a build or a test.

## What each dataset repository receives

Each Hugging Face dataset repository receives exactly what `python -m builders.stage_release` writes into
`release/staging/<repository>/` (git-ignored): its card and license from `huggingface/<name>/`, every file its card's
configurations load with that file's JSONL or Parquet twin, and its build reports, all copied from `output/`, built by the
builders at the release commit (`tests/test_staging.py` checks each staged file against its build file). The card
directories hold no copy of the data (`tests/test_sources.py`).

| Hugging Face repository | Data files (every file its card's configurations load, with its twin) | Build reports staged beside the data |
|---|---|---|
| `Ched-ai/voynich-eva` | the manifest's `output/eva_lines.jsonl` and `output/eva_lines.parquet`, then every other file its card loads | `output/eva_lines_build_report.json`, `output/eva_words_report.json`, `output/SHA256SUMS`, `output/release_manifest.json` |
| `Ched-ai/voynich-manuscript-metadata` | every file its card loads, from `output/metadata/` | `output/metadata/metadata_report.json` |
| `Ched-ai/voynich-transcription-mismatch` | `output/mismatch_index.jsonl` and `output/mismatch_index.parquet` | `output/mismatch_report.json` |
| `Ched-ai/voynich-transliterations` (new in 1.0.0) | every file its card loads, from `output/transliterations/` | `output/transliterations/transliterations_report.json`, `output/transliterations/variants_report.json`, `output/transliterations/coverage_matrix.csv` |

Each card's `configs` entry names its data file by base name, so every staged file goes at the repository's root under
its own name.

## Before publishing

All of these, at the release commit:

```bash
vcat-verify                   # the cached sources match data_sources/sources.yaml
pytest                        # the suite, reviewer proofs included; the committed output is a fresh build
```

and the license matrix of `docs/SOURCES_LICENSE.md` verified for every source a published dataset uses (S12).

## Uploading

With `huggingface_hub` installed and a token for the `Ched-ai` organization, one repository at a time, its staged folder
whole:

```bash
python -m builders.stage_release
huggingface-cli upload Ched-ai/voynich-eva release/staging/voynich-eva . --repo-type dataset
```

Then load each dataset from the Hub (`load_dataset("Ched-ai/voynich-eva")`) and compare its rows with `output/`. A release
freezes the old state first: the previous version is tagged in git and on each Hub repository before anything new is
uploaded.

## Version and citation

The version is the one in `pyproject.toml`, which `vcat.__version__`, `CITATION.cff`, `.zenodo.json`, the `voynich-eva`
card and the metadata build report state too (`tests/test_paperwork.py`). A release also records its DOI (`docs/ZENODO_SETUP.md`).
