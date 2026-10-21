# Zenodo Integration Setup

This document describes how to connect this repository to Zenodo for DOI assignment.

## Why Zenodo?

Zenodo provides:
- Permanent DOI for each release
- Long-term archival (backed by CERN)
- Automatic metadata from CITATION.cff
- Citation tracking

## Setup Steps

### 1. Connect GitHub to Zenodo

1. Go to https://zenodo.org
2. Log in with your GitHub account
3. Go to Settings → GitHub
4. Find `noah-chelednik/voynich-data` and flip the toggle ON

### 2. Create the releases

The old state is frozen first, so users of the 0.2.3 data can cite and pin it before anything changes (`docs/ROADMAP.md`
item 1.0):

1. On GitHub, go to Releases → Draft a new release; tag `v0.2.3` on commit `472ef73` (the published `main`); title
   `VCAT Data v0.2.3`; description: the 0.2.3 entry of CHANGELOG.md; publish. Zenodo archives it and gives it a DOI.
   That commit holds no `.zenodo.json`, and its `CITATION.cff` says version 0.1.0 (dated 2026-01-17): if the archived
   record shows that version or that date, edit them to 0.2.3 and 2026-01-18 (the CHANGELOG's
   0.2.3 date) on the record's page on Zenodo afterwards.
2. Then, after `main` holds 1.0.0, a second release: tag `v1.0.0`; title `VCAT Data v1.0.0`; description: the 1.0.0
   entry of CHANGELOG.md (with its migration notes); publish. Zenodo reads `.zenodo.json` for its metadata.

### 3. Get Your DOI

1. Zenodo automatically archives the release
2. Go to https://zenodo.org/account/settings/github/
3. Find your repository, click the DOI badge
4. Copy the DOI (format: `10.5281/zenodo.XXXXXXX`)

### 4. Update Documentation

Add the DOI to:
- README.md (badge at top)
- CITATION.cff (`doi:` field)
- Dataset card on HuggingFace

### Badge Markdown

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

## Notes

- Each new release gets a new DOI
- Zenodo provides a "concept DOI" that always points to the latest version
- Use the concept DOI in citations for "always latest"
- Use version-specific DOI for reproducibility
