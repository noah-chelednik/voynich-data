---
license: cc-by-4.0
task_categories:
  - other
language:
  - en
tags:
  - voynich
  - manuscript
  - metadata
  - codicology
  - medieval
pretty_name: Voynich Manuscript Metadata
size_categories:
  - n<1K
---

# Voynich Manuscript Metadata

## Dataset Summary

This dataset contains structured metadata about the Voynich Manuscript (Beinecke MS 408), a famous 15th-century codex held at Yale's Beinecke Rare Book & Manuscript Library. The dataset includes three tables: pages, folios, and quires, providing comprehensive codicological information.

## Dataset Structure

### Configurations

This dataset has three configurations:

- `pages`: Page-level metadata (226 records)
- `folios`: Folio-level metadata (116 records)
- `quires`: Quire-level metadata (20 records)

### Pages Configuration

```json
{
  "page_id": "f1r",
  "folio_id": "f1",
  "side": "recto",
  "quire_id": "qA",
  "currier_language": "A",
  "hand": "1",
  "illustration_type": "herbal",
  "section": "herbal_a",
  "has_text": true,
  "line_count": 31,
  "is_foldout_panel": false,
  "panel_number": null
}
```

#### Pages Fields

| Field | Type | Description |
|-------|------|-------------|
| `page_id` | string | Unique page identifier (e.g., "f1r", "f85v3") |
| `folio_id` | string | Parent folio identifier |
| `side` | string | "recto" or "verso" |
| `quire_id` | string | Quire identifier |
| `currier_language` | string | Currier's statistical language classification (A/B) |
| `hand` | string | Scribal hand per Davis 2020 |
| `illustration_type` | string | Type of illustration |
| `section` | string | Manuscript section |
| `has_text` | bool | Page contains transcribed text |
| `line_count` | int | Number of text lines |
| `is_foldout_panel` | bool | Part of a foldout page |
| `panel_number` | int/null | Panel number if foldout |

### Folios Configuration

```json
{
  "folio_id": "f1",
  "folio_number": 1,
  "quire_id": "qA",
  "is_foldout": false,
  "panel_count": null,
  "is_missing": false,
  "pages": ["f1r", "f1v"]
}
```

#### Folios Fields

| Field | Type | Description |
|-------|------|-------------|
| `folio_id` | string | Unique folio identifier |
| `folio_number` | int | Numeric folio number |
| `quire_id` | string | Parent quire identifier |
| `is_foldout` | bool | Folio is a foldout |
| `panel_count` | int/null | Number of panels if foldout |
| `is_missing` | bool | Folio is missing from manuscript |
| `pages` | list[string] | List of page IDs |

### Quires Configuration

```json
{
  "quire_id": "qA",
  "quire_number": 1,
  "folio_count": 8,
  "is_complete": true,
  "folios": ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"],
  "section_primary": "herbal_a"
}
```

#### Quires Fields

| Field | Type | Description |
|-------|------|-------------|
| `quire_id` | string | Unique quire identifier |
| `quire_number` | int | Numeric quire number |
| `folio_count` | int | Number of folios in quire |
| `is_complete` | bool | No missing folios |
| `folios` | list[string] | Ordered list of folio IDs |
| `section_primary` | string | Dominant manuscript section |

## Manuscript Sections

| Section | Description | Currier Language |
|---------|-------------|------------------|
| herbal_a | Plant illustrations with text | A |
| herbal_b | Plant illustrations, different style | B |
| astronomical | Circular diagrams, zodiac | Mixed |
| biological | Human figures, tubes, pools | B |
| cosmological | Foldout pages with complex diagrams | B |
| pharmaceutical | Small plant parts, containers | A |
| recipes | Dense text, few illustrations | A |

## Dataset Creation

### Source Data

Metadata extracted from:
- IVTFF transcription file headers (ZL3b-n.txt)
- voynich.nu section classifications
- Davis (2020) scribal hand identifications
- Beinecke Library catalog

### Processing

Built by the [Voynich Computational Analysis Toolkit (VCAT)](https://github.com/noah-chelednik/voynich-data).

## Considerations

### Limitations

- **Scholarly disputes:** Some classifications are contested
- **Section boundaries:** Not all scholars agree on section divisions
- **Hand identification:** Based on Davis 2020; other scholars may differ
- **Pre-1.0 schema:** May evolve in future versions

### Attribution

All metadata includes implicit attribution to the ZL transcription and voynich.nu. Disputed classifications are noted in the source documentation.

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- [voynich-eva-transcription](./voynich-eva-transcription): EVA transcription text
- [voynich-transcription-mismatch](./voynich-transcription-mismatch): Cross-transcription comparison

Datasets can be joined on `page_id`, `folio_id`, or `quire_id`.

## Quick Start

```python
from datasets import load_dataset

# Load pages metadata
pages = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")

# Load folios metadata
folios = load_dataset("Ched-ai/voynich-manuscript-metadata", "folios")

# Load quires metadata
quires = load_dataset("Ched-ai/voynich-manuscript-metadata", "quires")

# Count pages by section
from collections import Counter
sections = Counter(p['section'] for p in pages['train'])
print(sections)

# Find foldout pages
foldouts = [p for p in pages['train'] if p['is_foldout_panel']]
print(f"Foldout panels: {len(foldouts)}")
```

## Citation

```bibtex
@misc{voynich-manuscript-metadata,
  author = {VCAT Contributors},
  title = {Voynich Manuscript Metadata},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/Ched-ai/voynich-manuscript-metadata}
}
```

## References

- Zandbergen, R. voynich.nu - The Voynich Manuscript. https://www.voynich.nu/
- Davis, L. F. (2020). How Many Hands Wrote the Voynich Manuscript? Manuscript Studies, 5(2), 271-305.
- Beinecke Rare Book & Manuscript Library. MS 408: Voynich Manuscript. Yale University.

## Contact

- **Repository:** [GitHub](https://github.com/noah-chelednik/voynich-data)
- **Issues:** [GitHub Issues](https://github.com/noah-chelednik/voynich-data/issues)
