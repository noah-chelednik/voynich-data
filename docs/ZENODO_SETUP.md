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

### 2. Create a Release

1. On GitHub, go to Releases → Create a new release
2. Tag: `v0.1.0`
3. Title: `VCAT Data v0.1.0 - Initial Release`
4. Description: Copy from CHANGELOG.md
5. Publish release

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
