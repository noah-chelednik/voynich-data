---
license: cc-by-4.0
license_link: LICENSE
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
configs:
  - config_name: default
    data_files:
      - split: train
        path: mismatch_index.parquet
---

# Voynich Transcription Mismatch Index

## Dataset Summary

This dataset compares two transliterations of the Voynich Manuscript, ZL and IT, locus by locus (every locus type, labels
included), and records which of five sources (ZL, IT, CD, FG, GC) hold each locus. It records where the two transcribers
agree and where they differ, for research on transcription uncertainty; it states no consensus reading.

The primary comparison is between EVA-based transcriptions (ZL and IT), with additional tracking of Currier, FSG, and v101 transcription systems.

## Key Statistics

**Erratum (2026-10-17, roadmap item 1.8).** Version 0.2.3 published that the two EVA transliterations agree on 83.9% of
lines and disagree substantively on 16.1%. Those numbers were wrong in method: the comparison deleted ligatures and alternate
readings, fused words at drawing breaks, did not count an uncertain space as a space, covered only the 4,072 loci the old parser
kept, and counted any line at least 95% similar as agreeing. The index is now built on the named profile `analysis-v1`
(`vcat/profiles.py`), with exact verdicts and no similarity threshold (`vcat/comparison.py`); the similarity score is kept as a
description only. The rebuilt comparison:

<!-- erratum:mismatch-1.8:start (rendered by builders.build_mismatch_index.erratum_table from output/mismatch_report.json; checked by tests/test_mismatch_index.py) -->
| Verdict, ZL against IT, profile `analysis-v1` | Loci | Share of the 5,214 loci both hold |
|---|---|---|
| identical text (`text_raw` equal) | 1,161 | 22.3% |
| same reading (word sequences equal under the profile) | 1,323 | 25.4% |
| same reading for some choice among the alternates | 101 | 1.9% |
| different | 2,629 | 50.4% |

Agreement (identical, same reading, or an alternate's reading): 2,585 of 5,214 loci (49.6%). Different: 2,629 (50.4%), with a median similarity of 0.973 among them. ZL only: 171; IT only: 1.
<!-- erratum:mismatch-1.8:end -->

## Transcription Sources

| ID | Name | Alphabet | In this index |
|----|------|----------|---------------|
| zl | Zandbergen-Landini (`ZL3b-n.txt`) | EVA | compared |
| it | Takahashi (`IT_ivtff_1a.txt`) | EVA | compared |
| cd | Currier/D'Imperio (`CD2a-n.txt`) | Currier | present or absent only |
| fg | Friedman Study Group (`FG2a-n.txt`) | FSG | present or absent only |
| gc | Glen Claston (`GC2a-n.txt`) | v101 | present or absent only |

The loci each source holds, its SHA-256 and every parser warning are in `mismatch_report.json` (`sources`).

## Dataset Structure

### Data Instance

```json
{
  "comparison_profile": "analysis-v1",
  "it_locus_type": "@P0",
  "it_reading": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "it_source_line": 6,
  "it_text_raw": "<%>fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "line_id": "f1r:1",
  "line_number": 1,
  "page_id": "f1r",
  "similarity_score": 1.0,
  "sources_present": [
    "zl",
    "it",
    "cd",
    "fg",
    "gc"
  ],
  "status": "same_reading",
  "zl_locus_type": "@P0",
  "zl_reading": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "zl_source_line": 24,
  "zl_text_raw": "<%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>"
}
```

The first row, as built (`output/mismatch_index.jsonl`).

### Data Fields

| Field | Type | Description |
|---|---|---|
| `page_id` | string | IVTFF page name (f1r, f86v3, fRos) |
| `line_number` | integer | The locus number of the identifier |
| `line_id` | string | {page_id}:{line_number}, the key shared with the EVA lines dataset |
| `status` | string | identical: the two text_raw are equal; same_reading: the profile's word sequences are equal (. , and drawing breaks all separate words); alternate_reading: equal for some choice among the alternates; different: none of these; zl_only or it_only: one source has no such locus |
| `comparison_profile` | string | The normalization profile both texts are read through (vcat.profiles), e.g. analysis-v1 |
| `zl_text_raw` | string or null | ZL's text_raw, byte for byte, or null |
| `it_text_raw` | string or null | IT's text_raw, byte for byte, or null |
| `zl_reading` | string or null | ZL's text under the comparison profile |
| `it_reading` | string or null | IT's text under the comparison profile |
| `zl_locus_type` | string or null | ZL's locus code as written (@P0, &Lz) |
| `it_locus_type` | string or null | IT's locus code as written |
| `zl_source_line` | integer or null | The line of the locus identifier in ZL3b-n.txt |
| `it_source_line` | integer or null | The line of the locus identifier in IT_ivtff_1a.txt |
| `similarity_score` | number or null | difflib ratio of the two first-reading word sequences; a description, never the verdict |
| `sources_present` | array of string | Which of the five sources ZL, IT, CD, FG and GC hold this locus id; the other cached sources are not evaluated, so their absence here says nothing |

### Status Values

| Status | Meaning |
|--------|---------|
| `identical` | the two `text_raw` are the same string |
| `same_reading` | the word sequences under the comparison profile are the same (`.`, `,` and drawing breaks all separate words) |
| `alternate_reading` | the word sequences are the same for some choice among the alternate readings |
| `different` | none of the above |
| `zl_only` | only ZL has this locus |
| `it_only` | only IT has this locus |

Their counts are in the table under Key Statistics and in `mismatch_report.json` (`status_counts`).

## Use Cases

### Finding Uncertain Lines

```python
from datasets import load_dataset

ds = load_dataset("Ched-ai/voynich-transcription-mismatch")

# Loci where the two EVA transliterations read differently
mismatches = ds['train'].filter(lambda x: x['status'] == 'different')
print(f"Different: {len(mismatches)}")

# The most dissimilar of them (the score describes a difference; it never decides the status)
low_sim = mismatches.filter(lambda x: x['similarity_score'] < 0.5)
print(f"Low similarity: {len(low_sim)}")
```

### Robustness Testing

Use this dataset to test whether a result holds in both transliterations:

```python
# Check if a pattern appears in both readings (under the comparison profile)
def pattern_in_both(record, pattern):
    zl_has = pattern in (record['zl_reading'] or '')
    it_has = pattern in (record['it_reading'] or '')
    return zl_has and it_has
```

### Cross-Reference with Metadata

Join with voynich-manuscript-metadata to look at differences by page:

```python
meta = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")
# map page_id to the page record, then group the 'different' rows by it
```

## Dataset Creation

### Processing

1. Parse ZL and IT (and the other three sources, for presence) with the IVTFF parser; every parser warning goes to the report
2. Align loci by `line_id` (`page:locus number`)
3. Read both texts through the normalization profile `analysis-v1` (`vcat/profiles.py`)
4. Give each locus one exact verdict (`vcat/comparison.py`) and a similarity score as a description

### Methodology Notes

- **Compared:** only ZL and IT (the same alphabet, EVA)
- **Profile:** `analysis-v1`: ligature glyphs kept, the first reading of each alternate, drawing breaks as word spaces, `?` and the legacy EVA markers `!` and `*` dropped
- **Word spaces:** `.`, `,` (an uncertain space) and drawing breaks all separate words
- **Alternates:** a reading matches either option (`alternate_reading`)
- **Similarity:** `difflib.SequenceMatcher` ratio of the first-reading word sequences; no threshold

## Known Limitations

- **Two transliterations only.** CD, FG and GC use other alphabets; their texts are not compared.
- **Alignment by locus id.** Loci that the two transliterations number differently are compared as different loci.
- **One comparison profile.** The verdicts are those of `analysis-v1`; another profile can turn a `different` locus into
  `same_reading` or back (the rules are in `docs/data_model.md`).
- **No consensus.** The index says where the two differ; it never chooses a reading.
- **The similarity score describes, it never decides.** It ranks how far apart two readings are; no threshold sets a status.
- **Stable schema.** From 1.0.0, field names and meanings change only as `STABILITY.md` allows (a major version).

## Why Transcriptions Disagree

- **Glyph identification:** Scribal hands are difficult to read
- **Character boundaries:** Where one glyph ends and another begins
- **Damaged areas:** Faded or damaged sections
- **Word boundaries:** Interpreting spaces between words
- **Transcription conventions:** Different systems make different choices

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- [voynich-eva](https://huggingface.co/datasets/Ched-ai/voynich-eva): one row per locus of the ZL transliteration
- [voynich-manuscript-metadata](https://huggingface.co/datasets/Ched-ai/voynich-manuscript-metadata): Page, folio, quire metadata

## Quick Start

```python
from datasets import load_dataset

ds = load_dataset("Ched-ai/voynich-transcription-mismatch")["train"]
both = ds.filter(lambda x: x['status'] not in ('zl_only', 'it_only'))
agree = both.filter(lambda x: x['status'] != 'different')
print(f"Agreement over the loci both hold: {len(agree) / len(both):.1%}")
```

## Licensing

**VCAT's comparison** (the verdicts, statuses and similarity scores): CC-BY-4.0. **The text of the rows:** CC0-1.0. It is
read from two transliterations, ZL and IT (Takahashi), and the rows also record whether CD, FG and GC hold each locus
(none of their text). voynich.nu makes every one of these transliterations available under CC0; the statement was read at
its source and is recorded in `data_sources/sources.yaml`. The dataset as a whole is offered under CC-BY-4.0.

Please cite the transliterators in published work. **Code:** MIT (the repository's `LICENSE`). Per-source details:
[SOURCES_LICENSE.md](https://github.com/noah-chelednik/voynich-data/blob/main/docs/SOURCES_LICENSE.md).

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
