# Publishing Guide

This document provides step-by-step instructions for publishing VCAT Horizon 1 artifacts.

## Prerequisites

1. GitHub account: noah-chelednik
2. HuggingFace account: Ched-ai
3. Git installed locally
4. Python 3.11+ with `huggingface_hub` installed:
   ```bash
   pip install huggingface_hub datasets
   ```

## Step 1: Publish to GitHub

### 1.1 Create the Repository

1. Go to https://github.com/new
2. Repository name: `voynich-data`
3. Description: "Data processing infrastructure for the Voynich Computational Analysis Toolkit"
4. Public repository
5. Don't initialize with README (we have one)
6. Click "Create repository"

### 1.2 Push the Code

```bash
cd voynich-data

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: VCAT Horizon 1 - EVA lines dataset"

# Add remote
git remote add origin https://github.com/noah-chelednik/voynich-data.git

# Push
git push -u origin main
```

### 1.3 Verify CI

- Go to https://github.com/noah-chelednik/voynich-data/actions
- CI workflow should run automatically
- Fix any issues if tests fail

## Step 2: Publish to HuggingFace

### 2.1 Login to HuggingFace

```bash
huggingface-cli login
# Enter your HuggingFace token when prompted
```

### 2.2 Create the Dataset Repository

```bash
# Create the dataset on HuggingFace
huggingface-cli repo create voynich-eva --type dataset
```

### 2.3 Upload the Dataset

```python
from datasets import load_dataset
from huggingface_hub import HfApi

# Load the local parquet file
ds = load_dataset("parquet", data_files="output/eva_lines.parquet")

# Push to hub
ds.push_to_hub("Ched-ai/voynich-eva", config_name="lines")
```

Or using the CLI:
```bash
cd output
huggingface-cli upload Ched-ai/voynich-eva eva_lines.parquet --repo-type dataset
```

### 2.4 Upload the Dataset Card

The dataset card (README.md) should be uploaded to the dataset repository:

```bash
# Copy the dataset card
cp output/README.md hf_card_README.md

# Upload to HuggingFace
huggingface-cli upload Ched-ai/voynich-eva hf_card_README.md README.md --repo-type dataset
```

### 2.5 Verify the Dataset

```python
from datasets import load_dataset

# Test loading from HuggingFace
ds = load_dataset("Ched-ai/voynich-eva", "lines")
print(ds)
print(ds["train"][0])
```

## Step 3: Create Verification Threads

### 3.1 GitHub Discussion

1. Go to https://github.com/noah-chelednik/voynich-data
2. Enable Discussions in Settings
3. Create a new discussion:
   - Category: General
   - Title: "Horizon 1 Verification: Did the datasets load for you?"
   - Body:
     ```
     If you've successfully loaded any of the VCAT Horizon 1 datasets,
     please comment below with:
     - Which dataset(s) you loaded
     - Your environment (Python version, datasets library version)
     - Any issues encountered
     
     This helps us verify the datasets work across environments.
     ```

### 3.2 HuggingFace Discussion

1. Go to https://huggingface.co/datasets/Ched-ai/voynich-eva/discussions
2. Create a new discussion with the same content

## Checklist

### GitHub
- [ ] Repository created
- [ ] Code pushed
- [ ] CI passing (green badge)
- [ ] Discussions enabled
- [ ] Verification thread created

### HuggingFace  
- [ ] Dataset repository created
- [ ] Parquet file uploaded
- [ ] Dataset card (README.md) uploaded
- [ ] Dataset loads via `load_dataset("Ched-ai/voynich-eva", "lines")`
- [ ] Verification thread created

### External Verification
- [ ] At least one external user has confirmed successful load
- [ ] Verification logged in docs/progress.md

## Troubleshooting

### "Repository not found" when pushing to GitHub

Make sure you've created the repository on GitHub first, and the remote URL is correct:
```bash
git remote -v
git remote set-url origin https://github.com/noah-chelednik/voynich-data.git
```

### HuggingFace upload fails

1. Check you're logged in: `huggingface-cli whoami`
2. Make sure you have write access to the repository
3. Try with explicit token: `huggingface-cli upload ... --token YOUR_TOKEN`

### Dataset doesn't load

1. Verify the parquet file is valid:
   ```python
   import pandas as pd
   df = pd.read_parquet("output/eva_lines.parquet")
   print(len(df))
   ```
2. Check the dataset card YAML frontmatter is valid
3. Wait a few minutes for HuggingFace to process the upload

## Next Steps

After successful publishing:

1. Update progress.md with publishing confirmation
2. Announce on relevant forums (optional)
3. Begin Phase 2: Metadata dataset
