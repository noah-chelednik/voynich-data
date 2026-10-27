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
  - transliteration
  - historical
  - undeciphered
  - digital-humanities
pretty_name: Voynich Manuscript Transliterations (every source, one schema)
size_categories:
  - 10K<n<100K
configs:
  - config_name: zl
    data_files:
      - split: train
        path: zl.parquet
  - config_name: it
    data_files:
      - split: train
        path: it.parquet
  - config_name: it2a
    data_files:
      - split: train
        path: it2a.parquet
  - config_name: cd
    data_files:
      - split: train
        path: cd.parquet
  - config_name: fg
    data_files:
      - split: train
        path: fg.parquet
  - config_name: gc
    data_files:
      - split: train
        path: gc.parquet
  - config_name: rf1b
    data_files:
      - split: train
        path: rf1b.parquet
  - config_name: vt
    data_files:
      - split: train
        path: vt.parquet
  - config_name: lsi
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

# Voynich Manuscript Transliterations

## Dataset Summary

Every transliteration of the Voynich Manuscript (Beinecke MS 408, Yale University) that voynich.nu publishes and the roadmap
names, in one schema: one row per reading of one locus, keyed by René Zandbergen's page and locus ids (shared by the
sources, already harmonized upstream) plus the locus type, each source in its own alphabet and its text exactly as written.
One config per source. Nothing is normalized, mapped to another alphabet, compared or chosen: a row is what its source
says.

**This dataset is part of the Voynich Computational Analysis Toolkit (VCAT).**

## The sources

| Source | Config | Alphabet | Rows (readings) | Pages | Transcribers | Lines reported, not emitted |
|---|---|---|---|---|---|---|
| ZL | `zl` | EVA | 5,385 | 227 | none | 0 |
| IT | `it` | EVA | 5,215 | 225 | none | 0 |
| IT2a | `it2a` | EVA | 5,215 | 225 | none | 0 |
| CD | `cd` | Currier | 2,196 | 131 | none | 0 |
| FG | `fg` | FSG | 4,060 | 202 | none | 0 |
| GC | `gc` | v101 | 5,367 | 226 | none | 0 |
| RF1b | `rf1b` | EVA | 5,385 | 227 | none | 0 |
| VT | `vt` | EVA | 5,207 | 225 | none | 0 |
| LSI | `lsi` | EVA | 17,340 | 227 | C, D, F, G, H, I, J, K, L, N, P, Q, R, T, U, V, X, Z | 4 |

A source's rows are every locus reading its file holds. A line the parser does not accept is not a row: it is listed in
`output/transliterations/transliterations_report.json` (in the repository, beside the data files here) with its line number, its id and the reason. LSI, the Landini-Stolfi interlinear file, holds
one reading per transcriber of each locus, under one `line_id`, with its transcriber code in `transcriber`; its four lines
that number a locus `44a`, which the format does not allow, are the lines reported.

The coverage matrix, the readings each source has on each page, is `output/transliterations/coverage_matrix.csv` in the repository, beside the data files here.

## How the sources depend on each other

The sources are not independent, so two of them agreeing is not two confirmations:

- **IT** (both versions) and **VT** are Takeshi Takahashi's transliteration, taken from **LSI** (its transcriber `H`); VT
  differs from IT2a in how it marks unreadable characters and other inline markup, and lacks some of IT2a's loci.
- **RF1b** was made automatically from **ZL** and **GC**.
- **LSI** collects several transliterations in EVA, one per transcriber code, as its header defines them: among them `H`
  (Takeshi Takahashi's), `C` (Currier's, with later additions) and `F` (the First Study Group's), so its `C` and `F`
  readings descend from the transliterations **CD** and **FG** give in their own alphabets; their loci are not the same
  sets (LSI's `C` holds loci CD lacks).
- **ZL** (Zandbergen-Landini) and **GC** (Glen Claston's v101) are each their transcribers' own reading.

`docs/sources.md` of the repository gives each source's provenance.

## Dataset Structure

### Data Instance

```json
{
  "alphabet": "EVA",
  "line_id": "f1r:1",
  "line_number": 1,
  "locus_type": "@P0",
  "page_id": "f1r",
  "source": "ZL",
  "source_line": 24,
  "text_raw": "<%>fachys.ykal.ar.ataiin.shol.shory.[cth:oto]res.y.kor.sholdy<!@254;>",
  "transcriber": null
}
```

Two readings of one LSI locus:

```json
{
  "alphabet": "EVA",
  "line_id": "f1r:1",
  "line_number": 1,
  "locus_type": "@P0",
  "page_id": "f1r",
  "source": "LSI",
  "source_line": 1972,
  "text_raw": "fachys.ykal.ar.ataiin.shol.shory.cth!res.y.kor.sholdy! ",
  "transcriber": "H"
}
```

```json
{
  "alphabet": "EVA",
  "line_id": "f1r:1",
  "line_number": 1,
  "locus_type": "@P0",
  "page_id": "f1r",
  "source": "LSI",
  "source_line": 1973,
  "text_raw": "fachys.ykal.ar.ataiin.shol.shory.cthorys.y.kor.sholdy! ",
  "transcriber": "C"
}
```

### Data Fields

| Field | Type | Description |
|---|---|---|
| `source` | string | The source's id in data_sources/sources.yaml (ZL, IT, IT2a, CD, FG, GC, RF1b, VT, LSI) |
| `alphabet` | string | The source's transliteration alphabet as data_sources/sources.yaml records it (EVA, Currier, FSG, v101); the text is in it, never mapped to another |
| `page_id` | string | IVTFF page name (e.g., f1r, f86v3, fRos) |
| `line_number` | integer | The locus number the source gives (IVTFF Table 7); Zandbergen's numbering, shared by the sources |
| `line_id` | string | {page_id}:{line_number}, the id the sources share; an interlinear source (LSI) has one row per transcriber's reading under it |
| `locus_type` | string | The IVTFF locus code as written, locator and locus type (IVTFF 2.0 Tables 8 and 9) |
| `transcriber` | string or null | The transcriber code of an interlinear source's reading (IVTFF Table 7, T: LSI's H, C, F ...); null for every other source |
| `text_raw` | string | The transliterated text exactly as in the source: after the locus identifier and its whitespace, continuation lines included |
| `source_line` | integer | 1-based line number of the locus identifier in the source file |

## Variant tables (not a consensus)

Two configurations set the EVA sources' readings of each locus side by side (built by
`python -m builders.build_variants` from the per-source configs above, by the rules of `vcat/variants.py`). **They are not a
consensus: no reading is chosen, none is corrected, and no row says which reading is right.**

- `locus_variants`: one row per locus id, with every EVA reader's words (a reader is a source, or a source's transcriber
  where a file holds several: `LSI.H`), the sources holding the locus in any alphabet, how many different word sequences the
  readers give, and `agreement`, the share of pairs of readers giving the same words. `majority_baseline` is a labelled
  baseline only, never the default and not a reading: the readers are not independent (IT2a revises IT, RF1b derives from
  ZL and GC, LSI collects older transcriptions), so a count of readers is not evidence.
- `word_alignments`: one row per locus per reader other than the frame reader, its words aligned to the words of the frame reader (ZL where it holds the
  locus, else the first reader). The frame is a coordinate system, not a reference. The algorithm is Needleman-Wunsch on
  words (no cost for equal words, a cost of one for a substitution, an insertion or a deletion; of the least-cost alignments, the
  traceback prefers the diagonal, then a deletion, then an insertion). The first row of
  `output/transliterations/word_alignments.jsonl`, as committed:

```json
{
  "frame_reader": "ZL",
  "frame_words": [
    "fachys",
    "ykal",
    "ar",
    "ataiin",
    "shol",
    "shory",
    "cthres",
    "y",
    "kor",
    "sholdy"
  ],
  "line_id": "f1r:1",
  "matches": 10,
  "operations": [
    "match",
    "match",
    "match",
    "match",
    "match",
    "match",
    "match",
    "match",
    "match",
    "match"
  ],
  "page_id": "f1r",
  "reader": "IT",
  "word_agreement": 1.0,
  "words": [
    "fachys",
    "ykal",
    "ar",
    "ataiin",
    "shol",
    "shory",
    "cthres",
    "y",
    "kor",
    "sholdy"
  ]
}
```

Readings are taken under the profile `analysis-v1` and cut by the EVA tokenizer (`vcat/words.py`). Only EVA readings are
compared: the Currier, FSG and v101 sources are listed among those holding a locus, never compared, since no mapping between
the alphabets is applied (see the repository's decision record).

| Field | Type | Description |
|---|---|---|
| `line_id` | string | The locus id (`<page>:<locus>`), as in each source's config |
| `page_id` | string | The page |
| `line_number` | integer | The locus number on the page |
| `present_in` | array of string | Every source holding the locus, in any alphabet, in source order |
| `compared` | array of string | The readers compared: the EVA sources holding it, one per transcriber where a file has several |
| `readings` | array of object | Each compared reader's reading: reader, source, transcriber, locus type, source line, words |
| `distinct_readings` | integer | How many different word sequences the readers give |
| `agreement` | number or null | The share of pairs of readers giving the same words; null for fewer than two |
| `majority_baseline` | object or null | A labelled baseline, never the default and not a reading: the words more readers give than any other, with their support and readers; null on a tie |

| Field | Type | Description |
|---|---|---|
| `line_id` | string | The locus id |
| `page_id` | string | The page |
| `frame_reader` | string | The reader aligned to: ZL where it holds the locus, else the first reader |
| `reader` | string | The reader aligned |
| `frame_words` | array of string or null | The frame's words, position by position; null where the reader has a word the frame lacks |
| `words` | array of string or null | The reader's words in the same positions; null where the frame has a word the reader lacks |
| `operations` | array of values | Each position's operation: `match`, `substitute`, `delete` or `insert` |
| `matches` | integer | How many positions hold equal words |
| `word_agreement` | number or null | `matches` over the positions; null when neither has a word |

From the committed report (`output/transliterations/variants_report.json`; this table is rendered from it):

| Metric | Value |
|---|---|
| Loci (any source) | 5,390 |
| Loci with two or more EVA readers | 5,387 |
| Loci where every EVA reader gives the same words | 697 |
| Loci with no majority baseline (a tie) | 127 |
| Word alignments (one per locus per reader other than the frame reader) | 38,357 |

## Known Limitations

- Each source is distributed as it is, transcription choices and errors included: VCAT never corrects a transliteration
  (`STABILITY.md`, Corrections; report an error upstream).
- The alphabets differ (EVA, Currier, FSG, v101); no mapping between them is applied here.
- LSI is a beta file upstream ("It still requires checking by comparison against the input file").
- The pages and loci a source lacks are lacks of that source, not gaps in the manuscript: compare with the coverage matrix.

## Licensing

**Data:** CC-BY-4.0 for the dataset, which holds VCAT's comparison in its variant tables (`agreement`,
`distinct_readings`, `majority_baseline`, the alignments and `word_agreement`: the layer `variants` of
`data_sources/layers.yaml`). The per-source configs hold only the sources' text and ids, which voynich.nu makes available
under CC0 (the statement is quoted, with the table that links each file, in `docs/SOURCES_LICENSE.md` of the repository):
those fields stay CC0-1.0 wherever they are reused.

**Code:** MIT (the repository's `LICENSE`).

Please cite the transliterators and voynich.nu in published work. Per-source details:
[SOURCES_LICENSE.md](https://github.com/noah-chelednik/voynich-data/blob/main/docs/SOURCES_LICENSE.md).

## Citation

Cite each source's transliterators as `docs/sources.md` names them, and René Zandbergen's voynich.nu, which publishes the
files in the IVTFF format (https://www.voynich.nu/transcr.html). This dataset is part of VCAT Data, which is cited as:

```bibtex
@misc{vcat-data,
  author = {Chelednik, Noah},
  title = {Voynich Computational Analysis Toolkit - Data},
  year = {2026},
  version = {1.0.0},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.23685586},
  url = {https://github.com/noah-chelednik/voynich-data}
}
```
