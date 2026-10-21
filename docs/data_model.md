# VCAT data model and faithfulness contract

Written 2026-10-17 (roadmap item 1.7); revised 2026-10-18 to 2026-10-21 (items 2.3, 2.5, 2.8, 2.4, 2.6, 2.7 and 2.9: every source, the physical structure, the attribution of the layers, the links to Yale's images, the word level, the variant tables, the API and the configurations; then in S21, gates 6 and 7: the legacy markers of a profile by alphabet, and gate 9: the validators' one reading, the quires' sections, the variant alignments, the page examples). This document describes the EVA lines dataset (`output/eva_lines.jsonl`, one row per
source locus of Zandbergen's ZL transliteration, `data_sources/cache/ZL3b-n.txt`), its build report, and the metadata
datasets, and states exactly what VCAT guarantees about them and what it does not. The authority for the source format is
IVTFF 2.0 (file format 2.0.1, document issue 2.0.2, R. Zandbergen). Every guarantee below names the test that enforces it;
`tests/test_data_model_doc.py` checks that this document's field tables, mapping and profile table match the schema, the
committed outputs and the code.

The mismatch index (`output/mismatch_index.jsonl`, roadmap item 1.8) is described in section 10.

## 1. The faithfulness contract

VCAT is a faithful distribution, not an edition: the default view is the source text, structurally parsed, and every
interpretation is an optional, named, versioned layer.

### What VCAT guarantees

| # | guarantee | enforced by |
|---|---|---|
| G1 | **Byte-for-byte round trip.** The parsed data of every cached source rebuilds that source file byte for byte. | `tests/test_round_trip.py::test_every_cached_source_rebuilds_byte_for_byte` |
| G2 | **Never silent.** Every source locus is a row or is reported by the build (`reported_loci`); every page header is a page or is reported (`reported_pages`); the build fails on any unaccounted locus. | `tests/test_loss_accounting.py::test_real_sources_have_no_unaccounted_loci` |
| G3 | **`text_raw` is the source.** Each row's `text_raw` is the source text after the locus identifier and its separating whitespace, exactly, line terminator excluded; a wrapped locus keeps its continuation lines and terminators. | `tests/test_structured_layer.py::test_every_locus_rebuilds_its_source_line` |
| G4 | **The markup fields are the markup of `text_raw`.** `alternates`, `ligatures`, `uncertain_spaces`, `illegible`, `high_ascii`, `comments`, `drawing_breaks` and `markers` list every occurrence, read by IVTFF 2.0 Tables 3, 10 and 11. | `tests/test_structured_layer.py::test_tokens_cover_every_character` |
| G5 | **The structure is the source's.** `locus_type` is the locus code as written; `position` is its locator; `line_type` names its generic type; `page_id` and `line_number` are the identifier's. | `tests/test_conformance.py::test_validators_reject_structure_that_contradicts_the_source` |
| G6 | **The page metadata is the page header's.** `quire`, `hand`, `illustration_type` and `currier_language` are the page variables `$Q`, `$H`, `$I`, `$L` of the row's page header, as written. | `tests/regressions/audit_20261017_validators_s05/test_findings.py::test_f3_rejects_false_page_metadata` |
| G7 | **`text_clean` is a named profile.** It is exactly the profile `analysis-v1` of `text_raw` (section 5), and the build report's `text_clean_policy` names that profile. | `tests/test_profiles.py::test_text_clean_is_the_analysis_profile` |
| G8 | **Provenance.** Every row's `source_version` is the first 12 hex digits of the SHA-256 of the source file, which the build report records in full (`source_hash`) and both validators recompute; `alphabet`, `format_version` and `format_options` are the source's file header. | `tests/regressions/audit_20261017_validators_s05/test_findings.py::test_f4_rejects_false_provenance` |
| G9 | **Order.** Rows are in page order (`parsers.page_order_key`: folio, side, panel; `fRos` between f85r2 and f86v), then `line_index`. | `tests/test_invariants.py::TestStructuralInvariants::test_deterministic_ordering` |
| G10 | **No hand-written counts.** No test, validator or builder compares the data with a hard-coded number of the shapes the detector names: a literal of 100 or more in a comparison, or 10 or more next to a count word; any threshold on a `len(...)` other than an emptiness check; an equality between the `len(...)` of data read from the sources or the output and a literal, or a name assigned one, the data followed through assignments in lexical scope (a nested function sees its enclosing functions' names; a parameter shadows an outer name) and through the return value of a local function; branches are not followed; a large literal assigned to a count-like name; a count typed into a docstring or comment (DECISIONS Q6, Q36; reach cf1c8c6e). Counts the tests need are derived from the source at test time. | `tests/test_ci_checks.py::test_no_literal_counts` |
| G11 | **The committed output is a fresh build.** `output/eva_lines.jsonl` and `output/SHA256SUMS` are byte for byte what the builder produces from the cached source. | `tests/test_structured_layer.py::test_committed_eva_lines_are_a_fresh_build` |

### What VCAT does not guarantee

- **That the transliteration is right.** VCAT reproduces Zandbergen's text; it does not correct it. A glyph is kept as written,
  even when it looks like a slip (ZL `f57v.3` writes an upper-case `I`; DECISIONS Q39).
- **A reading of the text.** No profile is a consensus reading or a decipherment. `analysis-v1` keeps the first, most likely
  reading of each alternate (IVTFF 2.0 Table 10) because it must keep one; the others are in `alternates`.
- **That every source file conforms to IVTFF 2.0.** The parser checks the rules listed in section 7; a source line that
  breaks one is either reported (undefined markup) or kept with a recorded warning (a placement rule), never silently changed.
  Rules outside that list are not checked.
- **That `section` is a fact about the manuscript.** It is VCAT's one name for the source's `$I` illustration type (section
  3): a renaming of what the source states, recorded as the source's layer `section_name` (`data_sources/layers.yaml`,
  DECISIONS Q72); the metadata's `section`, by folio ranges, is VCAT's judgement and says so (section 9).
- **Word counts as a linguistic fact.** `word_count` counts the units of `text_clean` between `.` and `,` (a unit made
  only of high-ASCII codes counts too); whether an uncertain space (`,`) separates words is the transcriber's doubt, which
  `no-uncertain-spaces-v1` resolves the other way.
- **Other sources.** The EVA lines are ZL's. Every cached source is in `voynich-transliterations` in its own alphabet, with
  the variant tables comparing the EVA ones (section 12), and every table is also a configuration of `voynich-eva` (roadmap
  items 2.3, 2.7, 2.9).

## 2. Layers

| layer | fields | what it is |
|---|---|---|
| raw | `text_raw`, `source_line` | the source text, byte for byte, and where it is |
| structure | `page_id`, `line_number`, `line_index`, `line_id`, `locus_type`, `position`, `line_type` | the locus identifier, parsed (IVTFF 2.0 Tables 7 to 9) |
| markup | `alternates`, `ligatures`, `uncertain_spaces`, `illegible`, `high_ascii`, `comments`, `drawing_breaks`, `markers` and the flags `has_alternatives`, `has_high_ascii` | `text_raw` read by IVTFF 2.0 Tables 3, 10, 11 |
| page metadata | `quire`, `hand`, `illustration_type`, `currier_language` | the page header's variables, as written (`@`, set by text tags, gives null) |
| profile | `text`, `text_clean`, `char_count`, `word_count`, `has_uncertain`, `has_illegible` | readings derived from `text_raw` by named rules |
| source naming | `section` | VCAT's one name for the page header's `$I` illustration type: a renaming of what the source states (its layer `section_name`) |
| provenance | `source`, `source_version` | which file, which bytes |

## 3. Fields of `eva_lines.jsonl`

Every row has every field below (`schemas/transcription_lines.schema.json`).

| field | type | meaning |
|---|---|---|
| `page_id` | string | the IVTFF page name: `f` + folio + `r`/`v` + optional panel (`f86v3`), or `fRos` |
| `line_number` | integer | the locus number of the identifier, as the source numbers it (gaps preserved) |
| `line_index` | integer | the row's position on its page, 1 to n |
| `line_id` | string | `{page_id}:{line_number}` (`f1r:7`) |
| `text` | string | `text_raw` with wraps joined and outer whitespace stripped (the parser's `Locus.text`) |
| `text_raw` | string | the source text after the identifier and its whitespace, exactly (G3) |
| `locus_type` | string | the locus code as written, without the transcriber: locator, generic type, subtype (`@P0`, `&Lz`) |
| `source_line` | integer | the 1-based line of the locus identifier in the source file |
| `alternates` | array | each alternate `[a:b]` or `[a:b:c]` as its readings, most likely first |
| `ligatures` | array | the characters of each ligature `{...}` |
| `uncertain_spaces` | integer | how many uncertain word spaces `,` |
| `illegible` | array | each run of `?` (one unreadable character; `???` an unknown number), as written |
| `high_ascii` | array | each high-ASCII code `@NNN;` (128 to 255) as its number, comments excluded |
| `comments` | array | the text of each in-line comment `<!...>` |
| `drawing_breaks` | array | each `<->` or `<~>` (text interrupted by a drawing; a word space) |
| `markers` | array | each paragraph start `<%>`, paragraph end `<$>` and text tag `<@X=y>`, as written |
| `text_clean` | string | the profile `analysis-v1` of `text_raw` (section 5) |
| `line_type` | string | the generic locus type named: `paragraph` (P), `label` (L), `circle` (C), `radius` (R) |
| `position` | string | the locator of the locus code (IVTFF 2.0 Table 8): `@ + * = & ~ / !` |
| `quire` | string or null | the page header's `$Q` |
| `section` | string or null | VCAT's one name for the page header's `$I` (herbal, astronomical, biological, cosmological, pharmaceutical, stars, text_only, zodiac): a renaming of what the source states, its layer `section_name` |
| `currier_language` | string or null | the page header's `$L` (`A` or `B`) |
| `hand` | string or null | the page header's `$H` (Lisa Fagin Davis's hands, `1` to `5`); null when the header sets none, or sets `$H=@` (text tags set it on the page, IVTFF 2.0 section 6.8: unset before the first tag) |
| `illustration_type` | string or null | the page header's `$I` (IVTFF 2.0 Table 6) |
| `source` | string | the source identifier, `zandbergen_landini` |
| `source_version` | string | the first 12 hex digits of the source file's SHA-256 (G8) |
| `char_count` | integer | the glyphs of `text_clean` (`vcat.validate_eva_text`), each high-ASCII code counting as one |
| `word_count` | integer | units of `text_clean` separated by `.` or `,` (a unit of high-ASCII codes only counts) |
| `has_uncertain` | boolean | `text` holds a `?` outside comments (in the first reading of an alternate) |
| `has_illegible` | boolean | `text` holds a legacy EVA marker `!` or `*` outside comments; never true for an IVTFF 2.0 EVA file |
| `has_alternatives` | boolean | `alternates` is not empty |
| `has_high_ascii` | boolean | `high_ascii` is not empty |

## 4. From IVTFF to the dataset

| IVTFF 2.0 item | where it goes |
|---|---|
| file header `#=IVTFF Eva- 2.0 M 5` (section 6.1) | build report `alphabet`, `format_version`, `format_options` |
| comment line `# ...` (section 6.2) | not a row; kept by the parser for the round trip |
| page header `<f1r>  <! $Q=A ... >` (section 6.3) | `page_id`; `$Q`, `$H`, `$I`, `$L` to `quire`, `hand`, `illustration_type`, `currier_language`; `$I` to `section` |
| locus identifier `<f1r.7,*P0>` (section 6.4) | `page_id`, `line_number`, `line_id`, `locus_type`, `position`, `line_type`; `source_line` |
| locus identifier transcriber `;H` (Table 7) | not a row field (ZL has none) |
| transliterated text (section 6.6) | `text_raw`; `text`; the markup fields; `text_clean` |
| `.` and `,` (Table 10) | kept in `text_raw` and `text_clean`; `,` counted in `uncertain_spaces` |
| `?`, `???` (Table 10) | `illegible`; dropped by `analysis-v1` |
| `@NNN;` (Table 10) | `high_ascii`; kept by every profile |
| `{...}` ligature (Table 10) | `ligatures`; glyphs kept, braces dropped by `analysis-v1` |
| `[a:b]`, `[a:b:c]` alternates (Table 10) | `alternates`; the first reading in `analysis-v1` |
| `/` wrap (Table 10, section 5.5) | kept in `text_raw`; joined in `text`; removed by every profile but `raw-v1` |
| `<!...>` comment (Table 11) | `comments`; removed by every profile but `raw-v1` |
| `<->`, `<~>` drawing break (Table 11) | `drawing_breaks`; `.` in `analysis-v1` |
| `<%>`, `<$>` paragraph marks (Table 11, section 6.9) | `markers`; removed by every profile but `raw-v1` |
| `<@X=y>` text tag (Table 11, section 6.8) | `markers`; the tag's value is not applied to the row's page metadata |

## 5. Normalization profiles

A profile is one rule per kind of markup token (`vcat/profiles.py`). Profile ids are versioned (`analysis-v1`); a published
version never changes, and a new rule is a new version. `vcat.profiles.apply_profile(name, text_raw)` applies one.

| token | raw-v1 | diplomatic-v1 | analysis-v1 | no-uncertain-spaces-v1 |
|---|---|---|---|---|
| glyphs | keep | keep | keep, without `!` `*` (EVA only) | keep, without `!` `*` (EVA only) |
| space | keep | keep | keep | keep |
| uncertain_space | keep | keep | keep | drop |
| illegible | keep | keep | drop | drop |
| high_ascii | keep | keep | keep | keep |
| ligature | keep | keep | glyphs, no braces, without `!` `*` (EVA only) | glyphs, no braces, without `!` `*` (EVA only) |
| alternates | keep | keep, whitespace inside removed | first reading | first reading |
| comment | keep | drop | drop | drop |
| drawing_break | keep | keep | `.` | `.` |
| paragraph_start | keep | drop | drop | drop |
| paragraph_end | keep | drop | drop | drop |
| text_tag | keep | drop | drop | drop |
| whitespace | keep | drop | drop | drop |
| wrap | keep | drop | drop | drop |
| unknown | keep | keep | keep | keep |

`analysis-v1` drops `!` and `*` as the legacy EVA illegibility markers from an EVA text only; a text in another alphabet
keeps them as written (GC's v101 writes `*` as a glyph), so `vcat.load` reads each source in its own alphabet (B-053).

The reference lines, through `analysis-v1`:

| locus | `text_raw` | `text_clean` |
|---|---|---|
| `f1r:7` | `<%><!@252;>odar.{c'y}.shol.cphoy.oydar.sh.s.cfhoaiin.shodary` | `odar.c'y.shol.cphoy.oydar.sh.s.cfhoaiin.shodary` |
| `f1r:19` | `dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlo{ct}o` | `dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlocto` |
| `f10r:11` | `@135;otchoshor.qoty.qotor.cthyd<->otar` | `@135;otchoshor.qoty.qotor.cthyd.otar` |

## 6. Identifiers

- **`page_id`** is the page name as the source writes it: `f`, the folio number without leading zeros, `r` or `v`, and an
  optional panel number for foldouts (`f85r1`, `f86v3`); or `fRos`, the one page over the verso of f85 and the recto of f86
  (IVTFF 2.0 section 4.2). The parser accepts names of this shape; a folio number written with a leading zero would be
  accepted and kept as written, not normalized (no cached source has one).
- **`line_id`** is `{page_id}:{line_number}`, unique in the dataset. `line_number` is the source's locus number, so numbering
  gaps in the source stay gaps; `line_index` numbers the rows of a page 1 to n.
- Loci are emitted per page in source order, pages in page order (G9).

## 7. The IVTFF rules the parser enforces

In strict mode (`IVTFFParser(strict=True)`) each break is an error. Otherwise:

- **Reported, not emitted** (the row is missing and the build report names it): an invalid page name; a locus identifier that
  breaks section 6.4 (page name, number 1 to 999, a Table 8 locator, a Table 9 locus type); a locus outside its page; a wrap
  that is not continued; a line that is not in its file's encoding (UTF-8, or the encoding the source's record in
  `data_sources/sources.yaml` states: LSI's is Latin-1); markup the specification does not define (an unclosed or unknown `<...>`,
  `{...}` or `[...]`, an alternate with other than two or three readings, a comment over 80 characters, a `@` not followed by
  a code from 128 to 255, a `.` or `,` next to a drawing break, `<%>` after the start of the text). A malformed page header
  ends the previous page.
- **Emitted, with a recorded warning** (DECISIONS Q33): page variables that break section 6.3 (one upper-case letter set to
  one character, each variable once, `$B` 1 to 6, `$L` `A` or `B`; a broken setting gives no value); word spaces that break
  section 6.7 in a file of format 2.0 or later (first or last in the text, or two in sequence; a wrapped locus is one text);
  paragraph marks that break section 6.9 (only on generic type P, alternating, ending on their page; each transcriber of an
  interlinear file has its own paragraphs; an end needs a start only in a file of format 1.6 or later, the format that
  introduced `<%>`, or one that states no version). `$X=@` (set by text tags, section 6.8) is valid for every variable and
  gives no value.

Documented exceptions in the cached sources: 12 ZL loci put a comment before `<%>`, which is accepted (DECISIONS Q31);
CD2a-n `f42v.16` begins with `<->` and is kept with a 6.7 warning (Q33); IT_ivtff_1a declares format 1.7, which section 6.7
exempts; LSI_ivtff_0d is IVTFF 1.5 and Latin-1, and its four lines that number a locus `44a` are reported, as its record's
`nonconforming` list states (DECISIONS Q63).

Not checked (DECISIONS Q34): Table 6 values other than `$B` and `$L`, text tag conventions (6.8), page and locus order (6.10),
comment line length (6.2), line width (5.1), the whitespace recommendations of 5.6, word spaces inside alternate readings,
alternative identifiers (6.5).

## 8. The build report (`output/eva_lines_build_report.json`)

| field | meaning |
|---|---|
| `source_file`, `source_hash`, `source_verified` | the source path (relative to the repository when the file lies in it), its SHA-256, and whether that was verified against the file's bytes (whether it is the hash `data_sources/sources.yaml` pins is the release manifest's `source.pinned`) |
| `alphabet`, `format_version`, `format_options` | the source's file header |
| `text_clean_policy` | the profile `text_clean` is (`analysis-v1`) |
| `source_loci`, `source_page_headers` | the source census, counted without the parser |
| `total_pages_in_source` | the pages the parser accepted (a rejected page header is in `source_page_headers`, not here) |
| `loci_emitted`, `loci_reported`, `reported_loci`, `reported_pages` | what the build emitted and reported |
| `unaccounted_loci`, `unexpected_loci`, `unaccounted_pages`, `unrecognized_source_lines` | loss accounting; all empty or the build fails |
| `total_lines`, `total_pages`, `pages_with_lines`, `pages_without_lines`, `page_ids_without_lines` | row and page totals |
| `total_words`, `total_characters`, `lines_with_high_ascii`, `lines_by_type` | totals over the rows |
| `pages_by_language`, `pages_by_section` | counts over the pages the parser accepted, pages without loci included (not over the rows) |
| `warnings`, `errors`, `build_date` | every parser and charset warning, build errors, and the instant it was built (ISO 8601, UTC) |

## 9. Metadata datasets (`output/metadata/`)

Built by `python -m builders.build_metadata data_sources/cache/ZL3b-n.txt -o output/metadata --parquet` from the same source.

| file | fields |
|---|---|
| `pages.jsonl` | `page_id`, `folio_id`, `side`, `folio_number`, `quire_id`, `quire_letter`, `page_in_quire`, `section`, `currier_language`, `hand`, `illustration_type`, `line_count`, `label_count`, `has_text`, `is_foldout_panel`, `panel_number`, `total_panels`, `is_missing`, `notes` |
| `folios.jsonl` | `folio_id`, `folio_number`, `quire_id`, `recto_page_id`, `recto_page_ids`, `verso_page_ids`, `is_foldout`, `panel_count`, `is_missing`, `total_lines`, `currier_language`, `section`, `notes` |
| `quires.jsonl` | `quire_id`, `quire_letter`, `folio_ids`, `folio_count`, `page_count`, `is_complete`, `total_lines`, `sections`, `notes` |
| `bifolia.jsonl` | `bifolio_id`, `quire_id`, `bifolio_number`, `folio_ids`, `page_ids`, `is_complete`, `notes` |
| `page_orders.jsonl` | `order`, `position`, `page_id`, `attribution` |
| `page_canvases.jsonl` | `page_id`, `canvas_index`, `canvas_id`, `canvas_label`, `coverage`, `image_service` |
| `layers.jsonl` | `layer`, `fields`, `kind`, `source`, `attribution`, `license` |

The physical structure (roadmap item 2.5): `bifolia.jsonl` is one row per sheet, the leaves of a quire whose page headers
share a bifolio number `$B` (conjugate leaves; a sheet with one leaf has only that leaf in the source); `page_orders.jsonl` is one row per
page per named order, `foliation` (the default: folio number, recto before verso, panels in number order) and `zl_file`
(ZL's own order of its pages), each row naming who defines its order. Every Parquet file holds exactly its JSONL's rows,
nested values included (B-095), and both validators check that and recompute the bifolia and the orders from the source's
page headers.

The links to Yale's images (roadmap item 2.4): `page_canvases.jsonl` is one row per page per canvas of Yale University
Library's IIIF manifest of Beinecke MS 408 (https://collections.library.yale.edu/manifests/2002046) that the page lies on.
`vcat/iiif.py` reads the canvases (id, label, image service) into `data_sources/iiif/yale-2002046-canvases.json`, pinned to
the manifest's SHA-256, which the build report repeats. A page lies on every canvas whose label names its folio and side
(its panels on the canvas of their side; `fRos` on the one naming f85 verso and f86 recto); `coverage` is `part` where the
label says that side is shown in part, else `whole`. The rule reads Yale's labels only, so which panel lies on which part
is not decided. The canvases of the binding (`[Front cover]` and the like) name no page. Links only: no image is copied.
Both validators recompute the links from the canvases with the validators' own reading of the labels (one reading,
independent of `vcat/iiif.py`'s, run by both).

The attribution of every classification (roadmap item 2.8): `layers.jsonl` is `data_sources/layers.yaml` as published, one
row per layer, each with the dataset fields it fills, whether it is the source's (a value a transliteration states, as
written or named: the illustration type, the Davis hands, the Currier languages, the codicological fields) or VCAT's
judgement (the metadata `section`, by VCAT's folio ranges, whose page and folio rows carry `attribution: vcat` (the quires' `sections` list the names alone); the missing folios and a
quire's completeness, by VCAT's table of the gaps in the foliation), and its own license
(`CC0-1.0` for the source's, `CC-BY-4.0` for VCAT's). The EVA rows' `section` is the source's: VCAT's one name for each `$I`
code, a renaming, not a judgement. A layer of the metadata names the transliteration the build read: ZL for the
published datasets, another source's id for a build from it. A sheet with one leaf in the source says only that; a partial
transliteration omits leaves the manuscript keeps (B-106).

The metadata section, quire and foldout assignments come from `parsers/metadata_parser.py`; VCAT's own tables there (the
section ranges and the missing folios) are its judgements, and `layers.jsonl` says so field by field.

## 10. The mismatch index (`output/mismatch_index.jsonl`)

Built by `python -m builders.build_mismatch_index` (roadmap item 1.8; `schemas/mismatch_index.schema.json`). One row per locus
id that ZL (`data_sources/cache/ZL3b-n.txt`) or IT (`data_sources/cache/IT_ivtff_1a.txt`) emits, in page order then locus number: both `text_raw`, both readings
under the comparison profile (`analysis-v1`), both locus codes and source lines, which of the dataset's five sources hold the
id (`sources_present`: ZL, IT, CD, FG, GC, the sources its record in `data_sources/sources.yaml` names; the other cached
sources are not evaluated, so their absence there says nothing), a `status`, and a `similarity_score`. CD, FG and GC use
other alphabets and are only marked present or absent; every cached source's text is in `voynich-transliterations`, and
variant tables across all sources are roadmap item 2.7.

The `status` of a locus both hold is one exact verdict of `vcat.comparison.compare`, closest first: `identical` (the
`text_raw` are equal), `same_reading` (the word sequences under the profile are equal; `.`, `,` and drawing breaks all
separate words), `alternate_reading` (equal for some choice among the alternate readings), `different`. A locus one source
lacks is `zl_only` or `it_only`. The `similarity_score` (the `difflib` ratio of the first-reading word sequences) describes a
difference and never decides a verdict. There is no consensus reading: the index says where the two differ and leaves the
reading to the user (principle 4).

`output/mismatch_report.json` holds the counts per status, the agreement over the loci both hold (every verdict but
`different`), the median similarity of the `different` loci, and per source its file, SHA-256, emitted loci, reported loci and
every parser warning (never silent). The README, the dataset card and the CHANGELOG quote its numbers through
`builders.build_mismatch_index.erratum_table`, and the suite checks that they do.

## 11. The word level (`output/eva_words.jsonl`)

Built by `python -m builders.build_eva_words` from `output/eva_lines.jsonl` (roadmap item 2.6;
`schemas/eva_words.schema.json`), with a Parquet copy of the same rows and `output/eva_words_report.json` (the lines file it
read, by SHA-256, and its totals). One row per word, in line order, then word order.

**The EVA tokenizer** (`vcat/words.py`, the only one: the lines' `word_count` uses it too). A word is a maximal run of a
line's `text_clean` (profile `analysis-v1`) between word spaces: `.` (a certain space, which the profile also writes for
`<->` and `<~>`), `,` (an uncertain space) and whitespace. A run of separators is one boundary, certain if any of it is;
separators at the ends bound nothing, so no word is empty. A high-ASCII code `@NNN;` and a ligature's apostrophe (`c'y`)
are part of their word. An uncertain space ends a word, and the word records `space_after: uncertain`, so a reader can join
across it as the profile `no-uncertain-spaces-v1` does. The tokenizer reads glyphs only as characters: it decides nothing
the reading does not state.

**Paragraphs** are the source's (IVTFF 2.0 section 6.9): among lines of generic type `P`, a paragraph runs from the line
carrying the start mark `<%>` to the line carrying the end mark `<$>`, on one page; `paragraph_id` is `<page>.p<n>`, the
n-th on its page. Labels, circles, radii and the `P` lines outside every marked pair (ZL's free-floating `Pb` lines) are in
no paragraph; their paragraph fields are null and false.

Each word carries its line's `hand`, `currier_language`, `section` and `quire`, attributed as the lines' are
(`data_sources/layers.yaml`). Both validators recompute every row from the lines with the validators' own reading of these rules (one reading,
independent of `vcat/words.py`, run by both).

| Field | Type | Meaning |
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

## 12. The variant tables (`output/transliterations/locus_variants.jsonl`, `word_alignments.jsonl`)

Built by `python -m builders.build_variants` (and at the end of `python -m builders.build_transliterations`) from the
per-source rows of the transliterations dataset, by the rules of `vcat/variants.py` (roadmap item 2.7;
`schemas/locus_variants.schema.json`, `schemas/word_alignments.schema.json`), with Parquet copies of the same rows and
`output/transliterations/variants_report.json` (each input file by SHA-256, the profile, the algorithm, the totals). **They are not a consensus:
no reading is chosen, none is corrected, and no field says which reading is right.**

A *reader* is one source's transcription of a locus: a source, or a source's transcriber where a file holds several
(`LSI.H`). Only EVA readers are compared; the sources in Currier, FSG and v101 are listed in `present_in` and never
compared, because VCAT maps no alphabet to another (DECISIONS Q82). A reading is the reader's `text_raw` under
`analysis-v1`, cut by the EVA tokenizer (section 11).

`locus_variants` has one row per locus id: the readers' words side by side, `distinct_readings`, and `agreement`, the share
of pairs of readers giving the same words. `majority_baseline` is a labelled baseline, never the default and not a reading:
the words more readers give than any other, with their support, or null on a tie. Readers are not independent (IT2a
revises IT; RF1b derives from ZL and GC; LSI collects older transcriptions), so a count of readers is not evidence.

`word_alignments` has one row per locus per reader other than the frame reader: its words aligned to the frame reader's (ZL where it holds the locus,
else the first reader in source order). The frame is a coordinate system, not a reference. The alignment is
Needleman-Wunsch on words: cost 0 for equal words, 1 for a substitution, an insertion or a deletion; of the alignments of
least cost, the traceback from the end prefers the diagonal, then a deletion (a frame word with no reader word), then an
insertion. `word_agreement` is the share of aligned positions holding equal words.

| Field | Type | Meaning |
|---|---|---|
| `line_id` | string | The locus id (`<page>:<locus>`), as in each source's config |
| `page_id` | string | The page |
| `line_number` | integer | The locus number on the page |
| `present_in` | array | Every source holding the locus, in any alphabet, in source order |
| `compared` | array | The readers compared: the EVA sources holding it, one per transcriber where a file has several |
| `readings` | array | Each compared reader's reading: reader, source, transcriber, locus type, source line, words |
| `distinct_readings` | integer | How many different word sequences the readers give |
| `agreement` | number or null | The share of pairs of readers giving the same words; null for fewer than two |
| `majority_baseline` | object or null | A labelled baseline, never the default and not a reading: the words more readers give than any other, with their support and readers; null on a tie |

| Field | Type | Meaning |
|---|---|---|
| `line_id` | string | The locus id |
| `page_id` | string | The page |
| `frame_reader` | string | The reader aligned to: ZL where it holds the locus, else the first reader |
| `reader` | string | The reader aligned |
| `frame_words` | array | The frame's words, position by position; null where the reader has a word the frame lacks |
| `words` | array | The reader's words in the same positions; null where the frame has a word the reader lacks |
| `operations` | array | Each position's operation: `match`, `substitute`, `delete` or `insert` |
| `matches` | integer | How many positions hold equal words |
| `word_agreement` | number or null | `matches` over the positions; null when neither has a word |

## 13. The API and the configurations

`vcat.load(source=, unit=, profile=)` (`vcat/api.py`, roadmap item 2.9) reads the committed build (`output/`, or
`output_dir`), never the network, and returns plain rows. `source` is a cached source's id; `unit` is `line`, `word` or
`page` (the metadata's pages, ZL only); `profile` is a normalization profile (section 5). A line row keeps every field it
has and gains `reading`, its `text_raw` under the profile. ZL's words under `analysis-v1` are the word level (section 11);
any other source's or profile's words are cut from the reading by the EVA tokenizer. An unknown name is refused.

Every table is also a configuration of `voynich-eva` (`builders/stage_release.py`, `EVA_CONFIGS`): `default` (the lines,
as published since 0.2.3), `words`, the metadata's tables, `mismatch`, one `transliteration_<source>` per source, and
the variant tables. `python -m builders.stage_release` builds each Hub repository locally into `release/staging/`
(git-ignored): its card, LICENSE and the files its configurations load. The repositories `voynich-manuscript-metadata` and
`voynich-transcription-mismatch` keep their configurations, so every name and file the 0.2.3 cards define still loads
(`PUBLISHED_CONFIGS`; `tests/test_staging.py` loads each with the `datasets` library, offline). Nothing is uploaded here.

