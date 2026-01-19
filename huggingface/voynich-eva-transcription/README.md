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
  - medieval
  - undeciphered
pretty_name: Voynich Manuscript EVA Transcription
size_categories:
  - 1K<n<10K
---

# Voynich Manuscript EVA Transcription

## Dataset Summary

This dataset contains the complete transcription of the Voynich Manuscript (Beinecke MS 408) in the EVA (Extensible Voynich Alphabet) encoding. The Voynich Manuscript is a famous 15th-century codex written in an undeciphered script and unknown language.

The primary transcription is from the Zandbergen-Landini (ZL) source, the most complete and accurate EVA transcription available.

## Dataset Structure

### Data Instances

```json
{
  "page_id": "f1r",
  "line_number": 1,
  "line_id": "f1r:1",
  "text": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "locus_type": "P",
  "position": "@",
  "currier_language": "A",
  "hand": "1",
  "quire": "A",
  "has_uncertain": false,
  "has_illegible": false,
  "source": "zl",
  "source_version": "ZL3b-n.txt"
}
```

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `page_id` | string | Page identifier (e.g., "f1r", "f85v3") |
| `line_number` | int | Line number within page |
| `line_id` | string | Unique identifier: `{page_id}:{line_number}` |
| `text` | string | EVA-encoded transcription text |
| `locus_type` | string | Type code: P=paragraph, L=label, C=circular, R=radial |
| `position` | string | Position indicator: @=new unit, +=continuation, etc. |
| `currier_language` | string | Currier's language classification (A or B) |
| `hand` | string | Scribal hand identifier (1-5 per Davis 2020) |
| `quire` | string | Quire identifier |
| `has_uncertain` | bool | Contains uncertain reading markers |
| `has_illegible` | bool | Contains illegible markers |
| `source` | string | Transcription source identifier |
| `source_version` | string | Source file version |

### Data Splits

| Split | Records | Description |
|-------|---------|-------------|
| train | 4,072 | Complete transcription (no train/test split - this is a reference dataset) |

## Dataset Creation

### Source Data

- **Primary Source:** Zandbergen-Landini (ZL) transcription
- **Source URL:** https://www.voynich.nu/data/
- **Source Version:** ZL3b-n.txt (retrieved 2026-01-17)
- **Format:** IVTFF 2.0 (Interlinear Voynich Transcription File Format)

### Processing

Built by the [Voynich Computational Analysis Toolkit (VCAT)](https://github.com/noah-chelednik/voynich-data).

Pipeline: fetch → parse → validate → export

## Considerations

### Limitations

- **Undeciphered text:** The meaning of the text is unknown
- **Transcription uncertainty:** Some character readings are contested
- **Word boundaries:** Word boundaries (marked by `.`) are interpretive, not definitive
- **Pre-1.0 schema:** Schema may evolve in future versions
- **Single transcription system:** This dataset uses EVA; other systems (Currier, FSG) encode the same text differently

### EVA Alphabet

The EVA (Extensible Voynich Alphabet) uses lowercase letters to represent Voynich glyphs:

- Basic glyphs: `a c d e h i k l m n o p q r s t y`
- Compound glyphs: `ch sh cth ckh cph cfh`
- Rare glyphs: `f g j v x z`
- Word separator: `.`
- Uncertainty marker: `?`
- Illegible marker: `*`

### Known Issues

- ~100 rare "weirdoes" (unusual glyph forms) are encoded inconsistently
- Line boundaries may differ between transcription sources
- Marginalia and labels may have incomplete coverage

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- [voynich-manuscript-metadata](./voynich-manuscript-metadata): Page, folio, and quire metadata
- [voynich-transcription-mismatch](./voynich-transcription-mismatch): Cross-transcription comparison

Datasets can be joined on `page_id` or `line_id`.

## Quick Start

```python
from datasets import load_dataset

# Load the dataset
ds = load_dataset("Ched-ai/voynich-eva-transcription")

# Inspect
print(f"Total lines: {len(ds['train'])}")
print(ds['train'][0])

# Filter by Currier language
lang_a = ds['train'].filter(lambda x: x['currier_language'] == 'A')
lang_b = ds['train'].filter(lambda x: x['currier_language'] == 'B')
print(f"Language A: {len(lang_a)}, Language B: {len(lang_b)}")
```

## Citation

```bibtex
@misc{voynich-eva-transcription,
  author = {VCAT Contributors},
  title = {Voynich Manuscript EVA Transcription},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/Ched-ai/voynich-eva-transcription}
}

@misc{zandbergen-landini-transcription,
  author = {Zandbergen, René and Landini, Gabriel},
  title = {Voynich Manuscript Transcription},
  url = {https://www.voynich.nu/}
}
```

## References

- Zandbergen, R. voynich.nu - The Voynich Manuscript. https://www.voynich.nu/
- Beinecke Rare Book & Manuscript Library. MS 408: Voynich Manuscript. Yale University.
- Davis, L. F. (2020). How Many Hands Wrote the Voynich Manuscript? Manuscript Studies, 5(2).
- Bowern, C. & Lindemann, L. (2021). The Linguistics of the Voynich Manuscript. Annual Review of Linguistics.

## Contact

- **Repository:** [GitHub](https://github.com/noah-chelednik/voynich-data)
- **Issues:** [GitHub Issues](https://github.com/noah-chelednik/voynich-data/issues)
