---
license: cc-by-4.0
license_link: LICENSE
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
configs:
  - config_name: pages
    data_files:
      - split: train
        path: pages.jsonl
  - config_name: folios
    data_files:
      - split: train
        path: folios.jsonl
  - config_name: quires
    data_files:
      - split: train
        path: quires.jsonl
  - config_name: bifolia
    data_files:
      - split: train
        path: bifolia.jsonl
  - config_name: page_orders
    data_files:
      - split: train
        path: page_orders.jsonl
  - config_name: page_canvases
    data_files:
      - split: train
        path: page_canvases.jsonl
  - config_name: layers
    data_files:
      - split: train
        path: layers.jsonl
---

# Voynich Manuscript Metadata

## Dataset Summary

Page, folio and quire metadata of the Voynich Manuscript (Beinecke MS 408, Yale University), read from the page headers of
the Zandbergen-Landini (ZL) transliteration (version 3b of 13/05/2025) and grouped into folios, quires and bifolia by VCAT. Its
configurations are `pages`, `folios`, `quires`, `bifolia` (the sheets: conjugate leaves), `page_orders` (named orders of the
pages; `foliation` is the default), `page_canvases` (each page's links to Yale's images of it) and `layers` (who each classification is attributed to, and its license).

## Dataset Structure

The field tables are rendered from the record classes of `parsers/metadata_parser.py` (`page_canvases` from `vcat/iiif.py`,
`layers` from `vcat/layers.py`); the rows are the build's. The
configurations load the JSONL files, which hold these records as written; the Parquet files the builder also writes hold
the same rows with the same structure.

### `pages`

The first row of `output/metadata/pages.jsonl`, as committed:

```json
{
  "page_id": "f1r",
  "folio_id": "f1",
  "side": "recto",
  "folio_number": 1,
  "quire_id": "qA",
  "quire_letter": "A",
  "page_in_quire": "A",
  "section": {
    "value": "herbal_a",
    "attribution": "vcat",
    "confidence": "medium",
    "disputed": true,
    "alternatives": []
  },
  "currier_language": "A",
  "hand": "1",
  "illustration_type": "T",
  "line_count": 28,
  "label_count": 0,
  "has_text": true,
  "is_foldout_panel": false,
  "panel_number": null,
  "total_panels": null,
  "is_missing": false,
  "notes": []
}
```

| Field | Type | Description |
|---|---|---|
| `page_id` | `str` | Canonical page identifier (e.g., "f1r", "f86v3") |
| `folio_id` | `str` | Parent folio identifier (e.g., "f1", "f85") |
| `side` | `str` | Page side ("recto" or "verso") |
| `folio_number` | `int` | Numeric folio number |
| `quire_id` | `str or None` | Quire identifier (e.g., "qA", "q1") |
| `quire_letter` | `str or None` | Quire letter from IVTFF $Q variable |
| `page_in_quire` | `str or None` | Position within quire from IVTFF $P variable |
| `section` | `UncertainValue or None` | Manuscript section with uncertainty metadata |
| `currier_language` | `str or None` | Currier language classification ("A" or "B") |
| `hand` | `str or None` | Scribe/hand identifier |
| `illustration_type` | `str or None` | Illustration type code |
| `line_count` | `int` | Number of text lines on this page |
| `label_count` | `int` | Number of labels on this page |
| `has_text` | `bool` | Whether page has any transcribed text |
| `is_foldout_panel` | `bool` | Whether this is a panel of a foldout page |
| `panel_number` | `int or None` | Panel number if foldout (1-indexed) |
| `total_panels` | `int or None` | Total panels if foldout |
| `is_missing` | `bool` | Whether this page is from a missing folio |
| `notes` | `list[str]` | Additional notes |

### `folios`

The first row of `output/metadata/folios.jsonl`, as committed:

```json
{
  "folio_id": "f1",
  "folio_number": 1,
  "quire_id": "qA",
  "recto_page_id": "f1r",
  "recto_page_ids": [
    "f1r"
  ],
  "verso_page_ids": [
    "f1v"
  ],
  "is_foldout": false,
  "panel_count": null,
  "is_missing": false,
  "total_lines": 38,
  "currier_language": "A",
  "section": {
    "value": "herbal_a",
    "attribution": "vcat",
    "confidence": "medium",
    "disputed": true,
    "alternatives": []
  },
  "notes": []
}
```

| Field | Type | Description |
|---|---|---|
| `folio_id` | `str` | Folio identifier (e.g., "f1", "f85") |
| `folio_number` | `int` | Numeric folio number |
| `quire_id` | `str or None` | Parent quire identifier |
| `recto_page_id` | `str or None` | First recto page (kept for existing readers; see recto_page_ids) |
| `recto_page_ids` | `list[str]` | Every recto page of the folio, in panel order |
| `verso_page_ids` | `list[str]` | Every verso page of the folio, in panel order |
| `is_foldout` | `bool` | Whether this is a foldout folio |
| `panel_count` | `int or None` | Number of panels if foldout |
| `is_missing` | `bool` | Whether this folio is missing |
| `total_lines` | `int` | Total lines across all pages |
| `currier_language` | `str or None` | Predominant Currier language |
| `section` | `UncertainValue or None` | Predominant section assignment |
| `notes` | `list[str]` | Additional notes |

### `quires`

The first row of `output/metadata/quires.jsonl`, as committed:

```json
{
  "quire_id": "qA",
  "quire_letter": "A",
  "folio_ids": [
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8"
  ],
  "folio_count": 8,
  "page_count": 16,
  "is_complete": true,
  "total_lines": 225,
  "sections": [
    "herbal_a"
  ],
  "notes": []
}
```

| Field | Type | Description |
|---|---|---|
| `quire_id` | `str` | Quire identifier (e.g., "qA", "q1") |
| `quire_letter` | `str or None` | Original quire letter from IVTFF |
| `folio_ids` | `list[str]` | List of folio IDs in this quire |
| `folio_count` | `int` | Number of folios |
| `page_count` | `int` | Number of pages |
| `is_complete` | `bool or None` | False when a missing folio lies inside the quire's folio range; None when a missing folio lies between this quire and the next or previous one (consecutive quire letters) and the source cannot say which lost it; True otherwise |
| `total_lines` | `int` | Total lines in quire |
| `sections` | `list[str]` | Sections represented in this quire |
| `notes` | `list[str]` | Additional notes |

### `bifolia`

One row per sheet: the leaves of a quire whose page headers carry the same bifolio number (`$B`, counted from the
outermost sheet) are conjugate, one sheet folded once. Read from ZL's page headers (`$Q`, `$B`); a sheet with one leaf has only
that leaf in the source. The first row of `output/metadata/bifolia.jsonl`, as committed:

```json
{
  "bifolio_id": "qA.b1",
  "quire_id": "qA",
  "bifolio_number": 1,
  "folio_ids": [
    "f1",
    "f8"
  ],
  "page_ids": [
    "f1r",
    "f1v",
    "f8r",
    "f8v"
  ],
  "is_complete": true,
  "notes": []
}
```

| Field | Type | Description |
|---|---|---|
| `bifolio_id` | `str` | `{quire_id}.b{bifolio_number}` (e.g., "qA.b1") |
| `quire_id` | `str` | The quire it belongs to |
| `bifolio_number` | `int` | `$B`, counted from the outermost sheet of the quire |
| `folio_ids` | `list[str]` | Its leaves, in folio order |
| `page_ids` | `list[str]` | The pages of its leaves, in foliation order |
| `is_complete` | `bool` | Whether both leaves are in the source |
| `notes` | `list[str]` | Additional notes |

### `page_orders`

One row per page per named order, each order with who defines it:

- `foliation`: the folio numbers written on the manuscript's leaves, as IVTFF names its pages
- `zl_file`: the order of the pages in the Zandbergen-Landini transliteration (ZL), EVA, as voynich.nu publishes it

Another attributed order can be added as rows of its own name; none other is included, since no machine-readable source of
one is available here. The first row of `output/metadata/page_orders.jsonl`, as committed:

```json
{
  "order": "foliation",
  "position": 1,
  "page_id": "f1r",
  "attribution": "the folio numbers written on the manuscript's leaves, as IVTFF names its pages"
}
```

| Field | Type | Description |
|---|---|---|
| `order` | `str` | The order's name: `foliation` (the default: folio number, recto before verso, panels in number order) or `<source>_file` (the order the source built from lists its pages in: `zl_file` for ZL) |
| `position` | `int` | 1-based position in that order |
| `page_id` | `str` | The page |
| `attribution` | `str` | Who defines the order |

### `page_canvases`

Each page's links to the Beinecke Library's images of it (Yale University Library's IIIF manifest of MS 408; its address
and SHA-256 are in the statistics below): one row per page per canvas it lies on. A page lies on every
canvas whose label names its folio and side (`1r` is `f1r`; `69v and 70r` shows `f69v`, `f70r1` and `f70r2`; a foldout
panel lies on the canvas labelled with its side; `fRos` on `85v and 86r (foldout)`). Where Yale's label says the side is
shown `(part)`, the link's `coverage` is `part`: the page, or one of its panels, may lie on that canvas only in part. The
links read Yale's labels and nothing else; this dataset holds links only, never an image. The first row of
`output/metadata/page_canvases.jsonl`, as committed:

```json
{
  "page_id": "f1r",
  "canvas_index": 3,
  "canvas_id": "https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006076",
  "canvas_label": "1r",
  "coverage": "whole",
  "image_service": "https://collections.library.yale.edu/iiif/2/1006076"
}
```

| Field | Type | Description |
|---|---|---|
| `page_id` | `str` | The page, as in `pages` |
| `canvas_index` | `int` | The canvas's position in Yale's manifest, from 1 |
| `canvas_id` | `str` | The canvas's IIIF id in Yale's manifest |
| `canvas_label` | `str` | Yale's label for the canvas, as written |
| `coverage` | `str` | `whole` when the label names the page's side, `part` when it says that side is shown in part |
| `image_service` | `str` | The canvas image's IIIF Image API service (a link; VCAT copies no image) |

### `layers`

Every field that records a classification rather than the transliteration's text, with whose classification it is and its
own license: the source's (stated by ZL's page headers, CC0-1.0) or VCAT's judgement (CC-BY-4.0). From
`data_sources/layers.yaml` of the repository:

| Field | Type | Description |
|---|---|---|
| `layer` | `str` | The layer's name |
| `fields` | `list[str]` | The dataset fields it fills, as `<dataset>:<field>` |
| `kind` | `str` | `source` (a value a transliteration states) or `vcat` (VCAT's judgement) |
| `source` | `str` | Where its values come from |
| `attribution` | `str` | Whose classification it is |
| `license` | `str` | The license of its values: `CC0-1.0` for a source's, `CC-BY-4.0` for VCAT's |

| Layer | Kind | Fields | Attribution | License |
|---|---|---|---|---|
| `section` | VCAT's judgement | `voynich-manuscript-metadata:pages.section`, `voynich-manuscript-metadata:folios.section`, `voynich-manuscript-metadata:quires.sections` | VCAT's judgement, after the classifications described on voynich.nu; not a statement of any source | `CC-BY-4.0` |
| `section_name` | the source's | `voynich-eva:section`, `voynich-eva:words.section` | René Zandbergen's illustration types, as ZL records them | `CC0-1.0` |
| `illustration_type` | the source's | `voynich-eva:illustration_type`, `voynich-manuscript-metadata:pages.illustration_type` | René Zandbergen's illustration types, as ZL records them (voynich-eva) and ZL (the metadata) | `CC0-1.0` |
| `hand` | the source's | `voynich-eva:hand`, `voynich-eva:words.hand`, `voynich-manuscript-metadata:pages.hand` | Lisa Fagin Davis's scribal hands, after Davis (2020), as ZL records them (voynich-eva); Lisa Fagin Davis's scribal hands, after Davis (2020), as ZL records them (the metadata) | `CC0-1.0` |
| `currier_language` | the source's | `voynich-eva:currier_language`, `voynich-eva:words.currier_language`, `voynich-manuscript-metadata:pages.currier_language`, `voynich-manuscript-metadata:folios.currier_language` | Prescott Currier's languages A and B, as ZL records them (voynich-eva) and ZL (the metadata) | `CC0-1.0` |
| `physical_structure` | the source's | `voynich-eva:quire`, `voynich-eva:words.quire`, `voynich-manuscript-metadata:pages.quire_id`, `voynich-manuscript-metadata:pages.quire_letter`, `voynich-manuscript-metadata:pages.page_in_quire`, `voynich-manuscript-metadata:folios.quire_id`, `voynich-manuscript-metadata:quires.quire_letter`, `voynich-manuscript-metadata:bifolia.quire_id`, `voynich-manuscript-metadata:bifolia.bifolio_number`, `voynich-manuscript-metadata:bifolia.is_complete`, `voynich-manuscript-metadata:page_orders.order` | René Zandbergen's codicological description, as ZL records it | `CC0-1.0` |
| `comparison` | VCAT's judgement | `voynich-transcription-mismatch:status`, `voynich-transcription-mismatch:similarity_score` | VCAT's judgement; the texts compared are the sources' | `CC-BY-4.0` |
| `missing_folios` | VCAT's judgement | `voynich-manuscript-metadata:pages.is_missing`, `voynich-manuscript-metadata:folios.is_missing`, `voynich-manuscript-metadata:quires.is_complete` | VCAT's judgement, after the gaps in the foliation described on voynich.nu; not a statement of any source | `CC-BY-4.0` |
| `foldouts` | the source's | `voynich-manuscript-metadata:pages.is_foldout_panel`, `voynich-manuscript-metadata:folios.is_foldout` | René Zandbergen's naming of the foldout panels, as ZL records it | `CC0-1.0` |
| `iiif_links` | VCAT's judgement | `voynich-manuscript-metadata:page_canvases.canvas_id`, `voynich-manuscript-metadata:page_canvases.coverage` | VCAT's mapping of Yale's canvas labels to the page names; the labels and the images are Yale University Library's, linked, never copied | `CC-BY-4.0` |
| `variants` | VCAT's judgement | `voynich-transliterations:locus_variants.agreement`, `voynich-transliterations:locus_variants.distinct_readings`, `voynich-transliterations:locus_variants.majority_baseline`, `voynich-transliterations:word_alignments.frame_reader`, `voynich-transliterations:word_alignments.operations`, `voynich-transliterations:word_alignments.matches`, `voynich-transliterations:word_alignments.word_agreement` | VCAT's comparison; not a consensus, and the majority baseline is not a reading | `CC-BY-4.0` |

## Statistics

From the committed build report (`output/metadata/metadata_report.json`; this table is rendered from it):

| Metric | Value |
|---|---|
| Pages | 227 |
| Folios | 102 |
| Foldout folios | 10 |
| Quires | 18 |
| Quires with no missing folio | 13 |
| Bifolia | 52 |
| Bifolia with one leaf in the source | 2 |
| Links from a page to Yale's images | 247 |
| Links to a canvas showing the page's side in part | 36 |
| Pages in section `astronomical` | 26 |
| Pages in section `biological` | 20 |
| Pages in section `cosmological` | 7 |
| Pages in section `herbal_a` | 48 |
| Pages in section `herbal_b` | 70 |
| Pages in section `pharmaceutical` | 32 |
| Pages in section `recipes` | 24 |
| Pages of Currier language A | 114 |
| Pages of Currier language B | 83 |
| Pages of Currier language unknown | 30 |
| Yale's IIIF manifest | <https://collections.library.yale.edu/manifests/2002046> |
| Its SHA-256, when the canvases were read | `317d58fd9ea90392a83d9858a91eada3d0b41416a3c835857dc0154bd123a309` |

## Dataset Creation

### Source Data

- The page headers (`$Q`, `$P`, `$B`, `$I`, `$L`, `$H`) of the ZL transliteration, file `ZL3b-n.txt`,
  from https://www.voynich.nu/data/ZL3b-n.txt (SHA-256 in `data_sources/sources.yaml`). The hands (`$H`) are those ZL
  records, after Davis (2020).
- The canvases of Yale University Library's IIIF manifest of Beinecke MS 408 (its address and SHA-256 in the statistics
  above): each canvas's id, label and image service, read into the repository's `data_sources/iiif/` and pinned to the
  manifest's SHA-256. Linked, never copied: the images are Yale's.
- VCAT's section names and their attribution, confidence and dispute flags (`parsers/metadata_parser.py`), after the
  classifications described on voynich.nu.

### Processing

`python -m builders.build_metadata --parquet` builds the seven JSONL files (and Parquet copies of the same rows) and their report
from the cached source. Repository:
[voynich-data](https://github.com/noah-chelednik/voynich-data).

## Known Limitations

- **Only folios with pages are records.** A folio absent from the manuscript has no folio record, so `is_missing` is false
  on every folio row; whether a quire lost a folio is `is_complete` (null when the source cannot say which quire lost it).
- **Sections are VCAT's interpretation.** `section` and the folios' attribution, confidence and dispute flags are VCAT's
  annotations, not fields of the source; scholars draw the section boundaries differently.
- **Hands and languages are the source's.** `hand` and `currier_language` are as ZL records them; other scholars assign some
  pages differently, and pages without a `$L` value have none.
- **Stable schema.** From 1.0.0, field names and meanings change only as `STABILITY.md` allows (a major version).

## Related Datasets

This dataset is part of the **Voynich Computational Analysis Toolkit (VCAT)**:

- [voynich-eva](https://huggingface.co/datasets/Ched-ai/voynich-eva): one row per locus of the ZL transliteration
- [voynich-transcription-mismatch](https://huggingface.co/datasets/Ched-ai/voynich-transcription-mismatch): ZL against IT,
  locus by locus

Datasets join on `page_id`; `voynich-eva`'s `quire` holds the quire letter, this dataset's `quire_letter`.

## Quick Start

```python
from collections import Counter

from datasets import load_dataset

pages = load_dataset("Ched-ai/voynich-manuscript-metadata", "pages")
folios = load_dataset("Ched-ai/voynich-manuscript-metadata", "folios")
quires = load_dataset("Ched-ai/voynich-manuscript-metadata", "quires")

# Pages by Currier language
print(Counter(p["currier_language"] for p in pages["train"]))

# Panels of foldout pages
foldouts = [p for p in pages["train"] if p["is_foldout_panel"]]
```

## Licensing

**VCAT's annotations** (the section names and their attribution, confidence and dispute flags): CC-BY-4.0. **The fields
read from the ZL page headers:** CC0-1.0, as voynich.nu states for the ZL transliteration (recorded in
`data_sources/sources.yaml`, read at its source). The dataset as a whole is offered under CC-BY-4.0.

**Code:** MIT (the repository's `LICENSE`). Per-source details:
[SOURCES_LICENSE.md](https://github.com/noah-chelednik/voynich-data/blob/main/docs/SOURCES_LICENSE.md).

## Citation

```bibtex
@misc{voynich-manuscript-metadata,
  author = {VCAT Contributors},
  title = {Voynich Manuscript Metadata},
  year = {2026},
  publisher = {Hugging Face},
  version = {1.0.0},
  doi = {10.5281/zenodo.23685586},
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
