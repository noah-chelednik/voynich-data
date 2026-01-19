---
license: cc-by-4.0
task_categories:
  - other
language:
  - zxx
tags:
  - voynich
  - manuscript
  - transcription
  - comparison
  - alignment
pretty_name: Voynich Transcription Mismatch Index
size_categories:
  - 1K<n<10K
---

# Voynich Transcription Mismatch Index

## Dataset Summary

This dataset provides a line-by-line comparison across five different transcription sources of the Voynich Manuscript. It tracks agreements and disagreements between transcribers, enabling research on transcription uncertainty and consensus.

The primary comparison is between EVA-based transcriptions (ZL and IT), with additional tracking of Currier, FSG, and v101 transcription systems.

## Key Statistics

| Metric | Value |
|--------|-------|
| Total lines | 4,072 |
| Lines with both EVA sources | 4,069 |
| EVA exact matches | 901 (22.1%) |
| EVA normalized matches | 293 (7.2%) |
| EVA high similarity (≥95%) | 2,220 (54.6%) |
| EVA content mismatches | 655 (16.1%) |
| **Total EVA agreement rate** | **83.9%** |

## Transcription Sources

| ID | Name | Alphabet | Lines | Description |
|----|------|----------|-------|-------------|
| zl | Zandbergen-Landini | EVA | 4,072 | Primary reference (most complete) |
| it | Takahashi | EVA | 4,069 | Secondary EVA transcription |
| cd | Currier/D'Imperio | Currier | 2,154 | Historical Currier alphabet |
| fg | Friedman Study Group | FSG | 3,980 | NSA research group transcription |
| gc | Glen Claston | v101 | 4,070 | High-granularity v101 alphabet |

## Dataset Structure

### Data Instance

```json
{
  "page_id": "f1r",
  "line_number": 1,
  "line_id": "f1r:1",
  "zl_text": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "it_text": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "cd_text": "VAS92.9FAE.AR.APAM.ZOE.ZOR9.QOR92.9.FOR.ZOE89",
  "fg_text": "8ACIS.ICAL.AB.APAM.SOL.SOB2.QPBES.2.COB.SOLD2",
  "gc_text": "fZC*9S,9kAL,Ar,AtAiiN,Sol,Sor9,C!reS,9,kor,SolD9",
  "status": "exact_match",
  "eva_agreement": true,
  "similarity_score": 1.0,
  "sources_present": ["zl", "it", "cd", "fg", "gc"],
  "sources_missing": [],
  "notes": []
}
```

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `page_id` | string | Page identifier |
| `line_number` | int | Line number within page |
| `line_id` | string | Unique identifier: `{page_id}:{line_number}` |
| `zl_text` | string/null | ZL (EVA) transcription |
| `it_text` | string/null | IT (EVA) transcription |
| `cd_text` | string/null | Currier transcription |
| `fg_text` | string/null | FSG transcription |
| `gc_text` | string/null | v101 transcription |
| `status` | string | Comparison status (see below) |
| `eva_agreement` | bool/null | EVA transcriptions agree |
| `similarity_score` | float/null | Text similarity (0-1) |
| `sources_present` | list[string] | Sources with this line |
| `sources_missing` | list[string] | Sources missing this line |
| `notes` | list[string] | Additional notes |

### Status Values

| Status | Description | Count |
|--------|-------------|-------|
| `exact_match` | ZL and IT are identical | 901 |
| `normalized_match` | Match after removing uncertainty markers | 293 |
| `high_similarity` | ≥95% similar | 2,220 |
| `content_mismatch` | <95% similar | 655 |
| `zl_missing` | Line missing from ZL | 0 |
| `it_missing` | Line missing from IT | 3 |

## Use Cases

### Finding Uncertain Lines

```python
from datasets import load_dataset

ds = load_dataset("Ched-ai/voynich-transcription-mismatch")

# Find lines where transcribers disagree
mismatches = ds['train'].filter(lambda x: x['status'] == 'content_mismatch')
print(f"Disagreements: {len(mismatches)}")

# Find low-similarity mismatches
low_sim = ds['train'].filter(
    lambda x: x['similarity_score'] is not None and x['similarity_score'] < 0.5
)
print(f"Low similarity: {len(low_sim)}")
```

### Robustness Testing

Use this dataset to test whether your analysis results are robust across transcription variants:

```python
# Check if a pattern appears in both ZL and IT
def pattern_in_both(record, pattern):
    zl_has = pattern in (record['zl_text'] or '')
    it_has = pattern in (record['it_text'] or '')
    return zl_has and it_has
```

### Cross-Reference with Metadata

Join with voynich-manuscript-metadata to analyze disagreements by section:

```python
# Which sections have most disagreements?
meta = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")
# Create page_id -> section mapping
# Then filter mismatches by section
```

## Dataset Creation

### Processing

1. Parse all five transcription files (IVTFF format)
2. Align lines by `line_id` (page:line_number)
3. Compare EVA transcriptions with normalization
4. Compute similarity scores for mismatches
5. Record presence/absence for all sources

### Methodology Notes

- **EVA comparison:** Only ZL and IT are directly compared (same alphabet)
- **Normalization:** Removes uncertainty markers (`?`, `!`, `*`) and editorial brackets
- **Similarity:** SequenceMatcher ratio (0-1)
- **High similarity threshold:** ≥0.95

## Considerations

### Limitations

- **Cross-alphabet comparison not attempted:** CD, FG, GC use different alphabets; direct text comparison not meaningful
- **Line alignment by ID:** May miss reflow differences where transcribers split lines differently
- **Normalization choices:** May hide meaningful distinctions

### Why Transcriptions Disagree

- **Glyph identification:** Scribal hands are difficult to read
- **Character boundaries:** Where one glyph ends and another begins
- **Damaged areas:** Faded or damaged sections
- **Word boundaries:** Interpreting spaces between words
- **Transcription conventions:** Different systems make different choices

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- [voynich-eva-transcription](./voynich-eva-transcription): Complete EVA transcription
- [voynich-manuscript-metadata](./voynich-manuscript-metadata): Page, folio, quire metadata

## Quick Start

```python
from datasets import load_dataset

ds = load_dataset("Ched-ai/voynich-transcription-mismatch")

# Summary statistics
total = len(ds['train'])
exact = len(ds['train'].filter(lambda x: x['status'] == 'exact_match'))
high_sim = len(ds['train'].filter(lambda x: x['status'] == 'high_similarity'))
normalized = len(ds['train'].filter(lambda x: x['status'] == 'normalized_match'))

agreement_rate = (exact + high_sim + normalized) / total * 100
print(f"EVA agreement rate: {agreement_rate:.1f}%")
```

## Citation

```bibtex
@misc{voynich-transcription-mismatch,
  author = {VCAT Contributors},
  title = {Voynich Transcription Mismatch Index},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/Ched-ai/voynich-transcription-mismatch}
}
```

## References

- Zandbergen, R. & Landini, G. ZL Transcription. https://www.voynich.nu/
- Takahashi, T. IT Transcription.
- Currier, P. (1976). Papers on the Voynich Manuscript. NSA.
- Friedman First Study Group. FSG Transcription.
- Claston, G. v101 Transcription.

## Contact

- **Repository:** [GitHub](https://github.com/noah-chelednik/voynich-data)
- **Issues:** [GitHub Issues](https://github.com/noah-chelednik/voynich-data/issues)
