---
license: other
license_name: research-use
license_link: LICENSE
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
  - undeciphered
  - eva
  - digital-humanities
pretty_name: Voynich Manuscript EVA Transcription
size_categories:
  - 1K<n<10K
---

# Voynich Manuscript EVA Transcription

## Dataset Summary

This dataset provides a line-level transcription of the Voynich Manuscript in EVA (Extensible Voynich Alphabet) encoding. The Voynich Manuscript is a 15th-century codex written in an undeciphered script, held at Yale University's Beinecke Rare Book & Manuscript Library (MS 408).

This transcription is derived from the Zandbergen-Landini (ZL) transcription, the most complete and accurate EVA transcription available.

**This dataset is part of the Voynich Computational Analysis Toolkit (VCAT).**

## Dataset Structure

### Data Instance

```json
{
  "page_id": "f1r",
  "line_number": 1,
  "line_index": 1,
  "line_id": "f1r:1",
  "text": "<%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>",
  "text_clean": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "line_type": "paragraph",
  "position": "@",
  "quire": "A",
  "section": "text_only",
  "currier_language": "A",
  "hand": "1",
  "illustration_type": "T",
  "char_count": 43,
  "word_count": 10,
  "has_uncertain": false,
  "has_illegible": false,
  "has_alternatives": true,
  "has_high_ascii": true,
  "source": "zandbergen_landini",
  "source_version": "bf5b6d4ac1e3"
}
```

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `page_id` | string | Folio identifier (e.g., "f1r" for folio 1 recto) |
| `line_number` | int | Source locus ID within page (may have gaps - preserves original numbering) |
| `line_index` | int | Sequential index within page (always 1..n, no gaps) |
| `line_id` | string | Unique identifier: `{page_id}:{line_number}` |
| `text` | string | Raw transcription with IVTFF markup |
| `text_clean` | string | Cleaned text (markup removed, @NNN; codes preserved - lossless) |
| `line_type` | string | Type: "paragraph", "label", "circle", "radius" |
| `position` | string | Position indicator: "@" (new), "+" (continue), "=" (end), "*" (new para) |
| `quire` | string | Quire identifier (A-T) |
| `section` | string | Manuscript section (herbal, astronomical, biological, etc.) |
| `currier_language` | string | Currier's language classification: "A" or "B" |
| `hand` | string | Scribe hand identifier |
| `illustration_type` | string | Type of illustration on page (H=herbal, A=astro, etc.) |
| `char_count` | int | Count of EVA characters |
| `word_count` | int | Count of words (separated by `.` or `,`) |
| `has_uncertain` | bool | Contains uncertain reading markers (`?`) |
| `has_illegible` | bool | Contains illegible markers |
| `has_alternatives` | bool | Contains alternative readings (`[a:b]`) |
| `has_high_ascii` | bool | Contains high-ASCII codes (`@NNN;`) |
| `source` | string | Source transcription identifier |
| `source_version` | string | SHA256 hash prefix of source file |

### Data Splits

| Split | Records | Description |
|-------|---------|-------------|
| train | 4,072 | Complete transcription (no splits) |

## Dataset Creation

### Source Data

- **Source:** Zandbergen-Landini (ZL) Transcription v3b
- **URL:** https://www.voynich.nu/data/ZL3b-n.txt
- **Format:** IVTFF 2.0 (Intermediate Voynich Transliteration File Format)
- **Attribution:** René Zandbergen and Gabriel Landini

The ZL transcription is based on the European Voynich Manuscript Transcription (EVMT) project and represents the most accurate complete transcription of the Voynich Manuscript.

### Processing

Built by VCAT processing scripts:
1. Parse IVTFF format
2. Extract page-level metadata from headers
3. Clean text (remove markup, keep first alternatives)
4. Validate against EVA character set
5. Compute line-level statistics
6. Export to Parquet

Pipeline: `fetch → parse → validate → export`

Repository: [voynich-data](https://github.com/noah-chelednik/voynich-data)

### Validation

- Schema validation: ✓ Passed
- EVA character validation: ✓ 170,564 characters validated
- All smoke tests: ✓ Passed (10/10)

## Statistics

| Metric | Value |
|--------|-------|
| Total pages | 226 |
| Total lines | 4,072 |
| Total EVA characters | 170,564 |
| Total words | 33,711 |
| Paragraph lines | 3,957 |
| Label lines | 115 |
| Language A pages | 114 |
| Language B pages | 82 |

### Top Characters by Frequency

| Character | Count | Percentage |
|-----------|-------|------------|
| o | 22,022 | 12.9% |
| e | 17,823 | 10.4% |
| h | 16,133 | 9.5% |
| y | 15,819 | 9.3% |
| a | 12,628 | 7.4% |
| c | 11,917 | 7.0% |
| d | 11,673 | 6.8% |
| i | 10,745 | 6.3% |
| k | 9,854 | 5.8% |
| l | 9,380 | 5.5% |

## Considerations

### Limitations

- **Transcription uncertainty:** The Voynich script is ambiguous; some readings are uncertain (flagged with `has_uncertain` and `has_alternatives`)
- **No semantic meaning:** This is a character-level transcription; the text remains undeciphered
- **Section classification:** Section assignments are approximate and may differ from other sources
- **Single transcription:** This dataset uses ZL only; other transcriptions may differ (see `voynich-transcription-disagreements`)

### Schema Status

⚠️ **Pre-1.0:** Schema may change. Pin to specific versions for reproducibility.

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- `voynich-eva` (this dataset) - Line-level EVA transcription
- `voynich-manuscript-metadata` - Page, folio, quire metadata
- `voynich-transcription-disagreements` - Cross-transcription mismatch index

Datasets can be joined on `page_id`.

## Quick Start

```python
from datasets import load_dataset

# Load the dataset
ds = load_dataset("Ched-ai/voynich-eva", "lines")

# View first record
print(ds["train"][0])

# Filter by Currier language
lang_a = ds["train"].filter(lambda x: x["currier_language"] == "A")
lang_b = ds["train"].filter(lambda x: x["currier_language"] == "B")

# Get herbal section
herbal = ds["train"].filter(lambda x: x["section"] == "herbal")

# Get clean text for analysis
texts = [row["text_clean"] for row in ds["train"]]
```

## Versioning

- **Current version:** v0.2.2
- **Schema status:** Pre-1.0 (may change)
- **Source version:** ZL3b (May 2025)

## Licensing

**Processing code and dataset structure:** MIT License

**Underlying transcription data:** The ZL transcription is provided by [voynich.nu](https://voynich.nu) for research purposes. The transcription authors (Zandbergen & Landini) have not published an explicit license statement. Based on the public availability and academic nature of the work, we believe research use is permitted. Users should:

- **Cite the original transcribers** (see Source Citation below)
- **Verify rights independently** for commercial applications
- **Contact the transcription authors** if in doubt about specific uses

This dataset is released as a **research resource**. If you are aware of more specific licensing terms, please open an issue.

## Citation

```bibtex
@misc{voynich-eva,
  author = {Noah Chelednik},
  title = {Voynich Manuscript EVA Transcription},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/Ched-ai/voynich-eva}
}
```

### Source Citation

```bibtex
@misc{zandbergen-landini,
  author = {Zandbergen, René and Landini, Gabriel},
  title = {Voynich Manuscript Transliteration},
  url = {https://www.voynich.nu/transcr.html}
}
```

## Contact

- **Repository:** [voynich-data](https://github.com/noah-chelednik/voynich-data)
- **Issues:** [GitHub Issues](https://github.com/noah-chelednik/voynich-data/issues)

---

*This project does not claim to solve the Voynich Manuscript. It provides infrastructure for rigorous computational study.*
