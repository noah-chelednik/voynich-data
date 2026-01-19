---
license: cc-by-4.0
task_categories:
  - text-classification
  - token-classification
language:
  - zxx
tags:
  - voynich
  - manuscript
  - transcription
  - historical
  - digital-humanities
pretty_name: {{DATASET_PRETTY_NAME}}
size_categories:
  - 1K<n<10K
---

# {{DATASET_NAME}}

## Dataset Summary

{{DATASET_DESCRIPTION}}

**This dataset is part of the Voynich Computational Analysis Toolkit (VCAT).**

## Dataset Structure

### Data Instance

```json
{{EXAMPLE_RECORD}}
```

### Data Fields

{{DATA_FIELDS_TABLE}}

### Data Splits

| Split | Records | Description |
|-------|---------|-------------|
| train | {{RECORD_COUNT}} | {{SPLIT_DESCRIPTION}} |

## Dataset Creation

### Source Data

- **Source:** {{SOURCE_NAME}}
- **URL:** {{SOURCE_URL}}
- **Attribution:** {{SOURCE_ATTRIBUTION}}

### Processing

Built by VCAT processing scripts: `fetch → parse → validate → export`

Repository: [voynich-data](https://github.com/noah-chelednik/voynich-data)

### Validation

{{VALIDATION_STATUS}}

## Considerations

### Limitations

{{LIMITATIONS}}

### Schema Status

⚠️ **Pre-1.0:** Schema may change. Pin to specific versions for reproducibility.

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- `voynich-eva` - Line-level EVA transcription
- `voynich-manuscript-metadata` - Page, folio, quire metadata
- `voynich-transcription-disagreements` - Cross-transcription mismatch index

Datasets can be joined on `page_id`.

## Quick Start

```python
from datasets import load_dataset

# Load the dataset
ds = load_dataset("Ched-ai/{{DATASET_SLUG}}", "{{CONFIG_NAME}}")

# View first record
print(ds["train"][0])
```

## Versioning

- **Current version:** {{VERSION}}
- **Schema status:** Pre-1.0 (may change)

## Licensing

This dataset is released under **CC-BY-4.0**.

{{LICENSING_NOTES}}

## Citation

```bibtex
@misc{{{CITATION_KEY}},
  author = {Noah Chelednik},
  title = {{{DATASET_NAME}}},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/Ched-ai/{{DATASET_SLUG}}}
}
```

## Contact

- **Repository:** [voynich-data](https://github.com/noah-chelednik/voynich-data)
- **Issues:** [GitHub Issues](https://github.com/noah-chelednik/voynich-data/issues)

---

*This project does not claim to solve the Voynich Manuscript. It provides infrastructure for rigorous computational study.*
