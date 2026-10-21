---
license: cc-by-4.0
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
configs:
  - config_name: default
    data_files:
      - split: train
        path: eva_lines.parquet
  - config_name: words
    data_files:
      - split: train
        path: eva_words.parquet
  - config_name: pages
    data_files:
      - split: train
        path: pages.parquet
  - config_name: folios
    data_files:
      - split: train
        path: folios.parquet
  - config_name: quires
    data_files:
      - split: train
        path: quires.parquet
  - config_name: bifolia
    data_files:
      - split: train
        path: bifolia.parquet
  - config_name: page_orders
    data_files:
      - split: train
        path: page_orders.parquet
  - config_name: page_canvases
    data_files:
      - split: train
        path: page_canvases.parquet
  - config_name: layers
    data_files:
      - split: train
        path: layers.parquet
  - config_name: mismatch
    data_files:
      - split: train
        path: mismatch_index.parquet
  - config_name: transliteration_zl
    data_files:
      - split: train
        path: zl.parquet
  - config_name: transliteration_it
    data_files:
      - split: train
        path: it.parquet
  - config_name: transliteration_it2a
    data_files:
      - split: train
        path: it2a.parquet
  - config_name: transliteration_cd
    data_files:
      - split: train
        path: cd.parquet
  - config_name: transliteration_fg
    data_files:
      - split: train
        path: fg.parquet
  - config_name: transliteration_gc
    data_files:
      - split: train
        path: gc.parquet
  - config_name: transliteration_rf1b
    data_files:
      - split: train
        path: rf1b.parquet
  - config_name: transliteration_vt
    data_files:
      - split: train
        path: vt.parquet
  - config_name: transliteration_lsi
    data_files:
      - split: train
        path: lsi.parquet
  - config_name: locus_variants
    data_files:
      - split: train
        path: locus_variants.parquet
  - config_name: word_alignments
    data_files:
      - split: train
        path: word_alignments.parquet
---

# Voynich Manuscript EVA Transcription

## Dataset Summary

One row per locus (line, label, circle or radius text) of the Zandbergen-Landini (ZL) transliteration of the Voynich
Manuscript (Beinecke MS 408, Yale University), in EVA (the Extensible Voynich Alphabet), version 3b of 13/05/2025. Each row
keeps the source text exactly as written (`text_raw`) beside VCAT's readings of it, so nothing the transliterator recorded is
lost: every locus of the source file is a row, and the build fails if one is not.

**This dataset is part of the Voynich Computational Analysis Toolkit (VCAT).**

### Every layer as a configuration

The `default` configuration is the lines, as published since version 0.2.3; every other layer of VCAT is a configuration of
this repository too (roadmap item 2.9), so one `load_dataset("Ched-ai/voynich-eva", "<config>")` reaches all of it. The
repositories `voynich-manuscript-metadata` and `voynich-transcription-mismatch` keep their own configurations, so every name
and path that loads today still loads.

| Config | File | One row is |
|---|---|---|
| `default` | `eva_lines.parquet` | one locus of ZL (the lines) |
| `words` | `eva_words.parquet` | one word of ZL's lines |
| `pages` | `pages.parquet` | one page |
| `folios` | `folios.parquet` | one folio |
| `quires` | `quires.parquet` | one quire |
| `bifolia` | `bifolia.parquet` | one sheet (conjugate leaves) |
| `page_orders` | `page_orders.parquet` | one page in one named order |
| `page_canvases` | `page_canvases.parquet` | one link from a page to Yale's images |
| `layers` | `layers.parquet` | one interpretive layer and its attribution |
| `mismatch` | `mismatch_index.parquet` | one locus of ZL or IT, compared |
| `transliteration_zl` | `zl.parquet` | one reading of ZL |
| `transliteration_it` | `it.parquet` | one reading of IT |
| `transliteration_it2a` | `it2a.parquet` | one reading of IT2a |
| `transliteration_cd` | `cd.parquet` | one reading of CD |
| `transliteration_fg` | `fg.parquet` | one reading of FG |
| `transliteration_gc` | `gc.parquet` | one reading of GC |
| `transliteration_rf1b` | `rf1b.parquet` | one reading of RF1b |
| `transliteration_vt` | `vt.parquet` | one reading of VT |
| `transliteration_lsi` | `lsi.parquet` | one reading of LSI |
| `locus_variants` | `locus_variants.parquet` | one locus, every EVA reading side by side (not a consensus) |
| `word_alignments` | `word_alignments.parquet` | one reader's words of a locus aligned to the frame |

What each configuration holds is described on its own dataset card: the metadata tables on `voynich-manuscript-metadata`,
the mismatch index on `voynich-transcription-mismatch`, the per-source readings and the variant tables (not a consensus) on
`voynich-transliterations`.

## Dataset Structure

### Data Instance

The first row of the build, as committed:

```json
{
  "alternates": [
    [
      "cth",
      "oto"
    ]
  ],
  "char_count": 43,
  "comments": [
    "@254;"
  ],
  "currier_language": "A",
  "drawing_breaks": [],
  "hand": "1",
  "has_alternatives": true,
  "has_high_ascii": false,
  "has_illegible": false,
  "has_uncertain": false,
  "high_ascii": [],
  "illegible": [],
  "illustration_type": "T",
  "ligatures": [],
  "line_id": "f1r:1",
  "line_index": 1,
  "line_number": 1,
  "line_type": "paragraph",
  "locus_type": "@P0",
  "markers": [
    "<%>"
  ],
  "page_id": "f1r",
  "position": "@",
  "quire": "A",
  "section": "text_only",
  "source": "zandbergen_landini",
  "source_line": 24,
  "source_version": "bf5b6d4ac1e3",
  "text": "<%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>",
  "text_clean": "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy",
  "text_raw": "<%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>",
  "uncertain_spaces": 0,
  "word_count": 10
}
```

### Data Fields

The fields of `schemas/transcription_lines.schema.json`, in order (this table is rendered from the schema):

| Field | Type | Description |
|---|---|---|
| `page_id` | string | IVTFF page name (e.g., f1r, f86v3, fRos) |
| `line_number` | integer | Source locus ID within page (may have gaps - preserves original numbering) |
| `line_index` | integer | Sequential index within page (always 1..n, no gaps) |
| `line_id` | string | Unique line identifier: {page_id}:{line_number} |
| `text` | string | Transcription text for this line with IVTFF markup, stripped, continuation lines joined (text_raw is the exact source text) |
| `text_raw` | string | The transliterated text exactly as in the source: after the locus identifier and the whitespace that follows it, to the end of the line (a wrapped locus keeps its continuation lines and line terminators) |
| `locus_type` | string | The IVTFF locus code as written, locator and locus type (IVTFF 2.0 Tables 8 and 9), e.g. @P0, &Lz |
| `source_line` | integer | 1-based line number of the locus identifier in the source file |
| `alternates` | array of array of string | The readings of each uncertain reading [a:b] or [a:b:c], as written, most likely first |
| `ligatures` | array of string | The characters of each ligature {...}, as written |
| `uncertain_spaces` | integer | Number of uncertain word spaces (,) |
| `illegible` | array of string | Each run of unreadable characters (?, or ??? for an unknown number), as written |
| `high_ascii` | array of integer | Each high-ASCII code @NNN; in the transliterated text (not in comments) |
| `comments` | array of string | The text of each in-line comment <!...> |
| `drawing_breaks` | array of string | Each interruption by a drawing, as written (a word space) |
| `markers` | array of string | Each paragraph start <%>, paragraph end <$> and text tag <@X=y>, as written |
| `text_clean` | string | The normalization profile analysis-v1 of text_raw (vcat.profiles; the build report's text_clean_policy): ligature glyphs without braces, the first reading of each alternate, <-> and <~> as '.', '?' and the legacy EVA markers '!' '*' dropped, ',' kept, comments, paragraph marks, text tags, whitespace and wraps removed; glyphs as written |
| `line_type` | string | Type of text |
| `position` | string | IVTFF locator, the locus position relative to the previous item (IVTFF 2.0 Table 8) |
| `quire` | string or null | Quire identifier (A-T) |
| `section` | string or null | VCAT's one name for the page header's $I illustration type: a renaming of what the source states, the source's layer section_name (data_sources/layers.yaml); the metadata's section by folio ranges is VCAT's judgement |
| `currier_language` | string or null | Currier's language classification |
| `hand` | string or null | Scribe hand identifier |
| `illustration_type` | string or null | Type of illustration on page |
| `source` | string | Source identifier (e.g., zandbergen_landini) |
| `source_version` | string | SHA256 hash prefix of source file |
| `char_count` | integer | Count of EVA characters in clean text |
| `word_count` | integer | Count of words (separated by . or ,) |
| `has_uncertain` | boolean | text holds a '?' (an unreadable character) outside comments, counting only the first reading of an alternate |
| `has_illegible` | boolean | text holds a legacy EVA illegibility marker '!' or '*' outside comments; never true for an IVTFF 2.0 EVA file |
| `has_alternatives` | boolean | Contains alternative readings ([a:b]) |
| `has_high_ascii` | boolean | Contains high-ASCII codes (@NNN;) |

`text_clean` is the normalization profile `analysis-v1`; the other profiles (`raw-v1`, `diplomatic-v1`,
`no-uncertain-spaces-v1`) are computed from `text_raw` by `vcat.profiles`. The rules are in `docs/data_model.md`.

### Data Splits

One split, `train`, holding every row.

### The word level (`words` config)

One row per word of the lines above (`eva_words.parquet`, from `eva_words.jsonl`), built by
`python -m builders.build_eva_words` from the committed lines. The tokenizer is the one EVA tokenizer of the repository
(`vcat/words.py`, which the lines' `word_count` also uses): a word is a run of a line's `text_clean` between word spaces;
`.` is a certain space, `,` an uncertain one (the transliterator was not sure; it ends a word here, and `space_after` says
`uncertain`, so a reader can join across it); a high-ASCII code `@NNN;` is part of its word. The tokenizer decides nothing
about glyphs and never splits or joins what `text_clean` does not.

Positions: `word_index`, `line_initial`, `line_final` within the line; `paragraph_id`, `line_in_paragraph`,
`paragraph_initial`, `paragraph_final` within the source's paragraph, which runs from the `P` line carrying the start mark
`<%>` to the one carrying the end mark `<$>` (IVTFF 2.0 section 6.9: where a paragraph begins and ends is the
transcriber's decision). Labels, circles, radii and the few free-floating lines outside a marked pair are in no paragraph.
Each word carries its line's `hand`, `currier_language`, `section` and `quire`. The first row of
`output/eva_words.jsonl`, as committed:

```json
{
  "currier_language": "A",
  "hand": "1",
  "line_final": false,
  "line_id": "f1r:1",
  "line_in_paragraph": 1,
  "line_index": 1,
  "line_initial": true,
  "line_type": "paragraph",
  "locus_type": "@P0",
  "page_id": "f1r",
  "paragraph_final": false,
  "paragraph_id": "f1r.p1",
  "paragraph_initial": true,
  "quire": "A",
  "section": "text_only",
  "space_after": "certain",
  "word": "fachys",
  "word_id": "f1r:1.1",
  "word_index": 1
}
```

| Field | Type | Description |
|---|---|---|
| `word_id` | string | The word's id: its line's `line_id`, a period and its position in the line (`f1r:1.3`) |
| `line_id` | string | The line (locus) it is in, as in the lines config |
| `page_id` | string | The page |
| `line_index` | integer | The line's position on its page, as in the lines config |
| `word_index` | integer | The word's position in its line, from 1 |
| `word` | string | The word: a run of the line's `text_clean` between word spaces (`vcat/words.py`) |
| `space_after` | string or null | The space after it: `certain` (`.`), `uncertain` (`,`), or null for the last word of the line |
| `line_initial` | boolean | Whether it is the first word of its line |
| `line_final` | boolean | Whether it is the last word of its line |
| `paragraph_id` | string or null | The source's paragraph it is in (`<page>.p<n>`, the n-th on the page), or null outside every paragraph |
| `line_in_paragraph` | integer or null | Its line's position in the paragraph, from 1; null outside one |
| `paragraph_initial` | boolean | Whether it is the first word of its paragraph |
| `paragraph_final` | boolean | Whether it is the last word of its paragraph |
| `line_type` | string | The line's type, as in the lines config (`paragraph`, `label`, `circle`, `radius`) |
| `locus_type` | string | The line's IVTFF locus code, as in the lines config (`@P0`) |
| `hand` | string or null | The line's hand (`$H`), as in the lines config |
| `currier_language` | string or null | The line's Currier language (`$L`), as in the lines config |
| `section` | string or null | The line's section, as in the lines config |
| `quire` | string or null | The line's quire (`$Q`), as in the lines config |

## Dataset Creation

### Source Data

- **Source:** the ZL transliteration, file `ZL3b-n.txt`, version 3b of 13/05/2025
- **URL:** https://www.voynich.nu/data/ZL3b-n.txt
- **SHA-256:** recorded in `data_sources/sources.yaml`; the release manifest says whether the build read the pinned bytes
  (`source.pinned`, checked by both validators), and `python -m data_sources.verify_sources` checks the cached file
- **Format:** IVTFF 2.0
- **Transliterators:** René Zandbergen and Gabriel Landini

### Processing

`python -m builders.build_eva_lines` parses the file (`parsers.IVTFFParser`), emits one row per locus, accounts for every source
locus and page (a locus that is neither a row nor reported fails the build), and writes JSONL, Parquet, a build report, a
SHA-256 file and a release manifest. Two validators (`validators/validate_phase1_outputs.py`,
`validators/verify_invariants.py`) check the rows against the source; the suite checks that the committed files are a fresh
build. Repository: [voynich-data](https://github.com/noah-chelednik/voynich-data).

## Statistics

From the committed build report (`output/eva_lines_build_report.json`; this table is rendered from it):

| Metric | Value |
|---|---|
| Pages | 227 |
| Lines (loci) | 5,385 |
| Source loci | 5,385 |
| Words (`word_count`, summed) | 39,018 |
| EVA characters (`char_count`, summed) | 194,437 |
| Lines holding a high-ASCII code | 132 |
| `circle` lines | 84 |
| `label` lines | 1,029 |
| `paragraph` lines | 4,130 |
| `radius` lines | 142 |
| Pages of Currier language A | 114 |
| Pages of Currier language B | 83 |
| Pages of Currier language unknown | 30 |

The word level, from its committed build report (`output/eva_words_report.json`; this table is rendered from it):

| Metric | Value |
|---|---|
| Words | 39,018 |
| Lines holding a word | 5,385 |
| Paragraphs (the source's `<%>` to `<$>`) | 740 |
| Words in a paragraph | 35,056 |
| Words followed by an uncertain space | 2,748 |

## Known Limitations

- **One transliteration.** The rows are ZL's readings. Other transliterations read many loci differently: ZL and Takahashi
  (IT) give the same reading on about half of the loci they share (see
  [voynich-transcription-mismatch](https://huggingface.co/datasets/Ched-ai/voynich-transcription-mismatch)). VCAT does
  not choose between readings.
- **Uncertain readings stay uncertain.** Alternates (`[a:b]`), unreadable characters (`?`) and uncertain spaces (`,`) are
  kept in `text_raw` and listed in their fields; `text_clean` takes the first reading of each alternate, so it is one
  reading among those the source allows.
- **`section` is VCAT's one name for the page header's `$I` illustration type**: a renaming of what the source states
  (the source's layer `section_name`, `data_sources/layers.yaml`), not a field of its own in the source; the metadata's
  section by folio ranges is VCAT's judgement.
- **Counts are of the profile's text.** `char_count` and `word_count` count `text_clean`; another profile counts differently.
- **Stable schema.** From 1.0.0, field names and meanings change only as `STABILITY.md` allows (a major version); pin a
  version for reproducible work.
- **The text is undeciphered.** The rows record glyphs, not meaning.

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- `voynich-eva` (this dataset): one row per locus of the ZL transliteration
- [voynich-manuscript-metadata](https://huggingface.co/datasets/Ched-ai/voynich-manuscript-metadata): page, folio and quire
  metadata
- [voynich-transcription-mismatch](https://huggingface.co/datasets/Ched-ai/voynich-transcription-mismatch): ZL against IT,
  locus by locus

Datasets can be joined on `page_id`.

## Quick Start

```python
from datasets import load_dataset

ds = load_dataset("Ched-ai/voynich-eva")
print(ds["train"][0])

# Rows of Currier language A
lang_a = ds["train"].filter(lambda x: x["currier_language"] == "A")

# The analysis text of every row
texts = [row["text_clean"] for row in ds["train"]]

# Another layer: its configuration name
words = load_dataset("Ched-ai/voynich-eva", "words")
```

From a checkout of the repository, `vcat.load(source=, unit=, profile=)` reads the same build without the network:

```python
import vcat

lines = vcat.load()                                     # ZL's lines under analysis-v1
it_words = vcat.load(source="IT", unit="word")          # IT's words, cut by the EVA tokenizer
raw = vcat.load(source="LSI", unit="line", profile="raw-v1")
```

## Versioning

- **Current version:** v1.0.0
- **Schema status:** stable from 1.0.0, under `STABILITY.md` (identifiers never reused or silently changed)
- **Source version:** ZL 3b of 13/05/2025

## Licensing

**Data:** CC-BY-4.0 for the repository, which holds VCAT's annotations in some configurations (the metadata's section
judgements and missing folios, the links to Yale's images, the mismatch verdicts and the variant tables: the VCAT layers of
`data_sources/layers.yaml`). The `default` lines, the `words` and every `transliteration_*` configuration are the sources'
text and functions of it, which voynich.nu makes available under CC0 (the statement is recorded in
`data_sources/sources.yaml`, read at its source and quoted in `docs/SOURCES_LICENSE.md`): those fields stay CC0-1.0 wherever
they are reused.

**Code:** MIT (the repository's `LICENSE`).

Please cite the transliterators (below) in published work. Per-source details: [SOURCES_LICENSE.md](https://github.com/noah-chelednik/voynich-data/blob/main/docs/SOURCES_LICENSE.md).

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

Every transliteration this repository holds, with its transliterators (from `data_sources/sources.yaml`); cite the ones you use, and the dataset above:

| Source | Transliteration | Transliterators | Upstream version |
|---|---|---|---|
| ZL | Zandbergen-Landini transliteration (ZL), EVA | René Zandbergen, Gabriel Landini | Version 3b of 13/05/2025 |
| IT | Takahashi transliteration (IT), EVA, extracted from the Landini-Stolfi interlinear file | Takeshi Takahashi | Version 1a of 27/12/2022 |
| IT2a | Takahashi transliteration (IT), EVA, version 2a, extracted from the Landini-Stolfi interlinear file | Takeshi Takahashi | Version 2a of 02/02/2023 modified 25/06/2025 |
| CD | Currier transliteration (CD), Currier alphabet | Prescott Currier, Mary D'Imperio | IVTFF version 2a of 02/02/2023 |
| FG | First Study Group transliteration (FG), FSG alphabet | First Study Group (William Friedman) | IVTFF version 2a of 02/02/2023 |
| GC | Glen Claston transliteration (GC), v101 alphabet | Glen Claston (Tim Rayhel) | IVTFF version 2a of 05/02/2023 modified 25/06/2025 |
| RF1b | Reference transliteration (RF1b), EVA, full form | René Zandbergen | v. 1b |
| VT | voynichese.com transliteration (VT), EVA, mainly by Takeshi Takahashi | Takeshi Takahashi | v. 0e |
| LSI | Landini-Stolfi interlinear file (LSI), EVA, several transliterations per locus | Gabriel Landini, Jorge Stolfi, and the transcribers it collects | Release 1.6e6 - ?? Dec 1998 |

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
