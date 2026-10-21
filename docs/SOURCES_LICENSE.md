# Source Transcription Provenance and Licensing

What VCAT knows about the rights of each source, what it redistributes, and under what terms it offers its own outputs. The
record is `data_sources/sources.yaml`; the tables below are rendered from it and from the dataset cards
(`builders.cards`, checked by `tests/test_sources.py`).

## The short version

- The **manuscript itself** (Beinecke MS 408, Yale University) is in the public domain.
- **Every transliteration VCAT caches or pins** (ZL, IT, CD, FG, GC, RF1b, VT, LSI, and RF1b's basic form, which is pinned
  but not cached) is
  CC0-1.0: voynich.nu, which publishes them, states so for the files its tables of transliterations link, and each file is
  linked from one of those tables. The statement was read at its source on 2026-10-17 (S12) and is quoted below.
- **VCAT's code** is MIT. **Data VCAT derives** is CC0-1.0 where every source it derives from is CC0-1.0; **VCAT's own
  annotations** (section attributions and confidences, comparison verdicts and scores) are CC-BY-4.0.

## The upstream statement

From voynich.nu, "Licences and copyright" (https://www.voynich.nu/roadmap.html), read 2026-10-17:

> "The transliterations of the Voynich MS text, as collected in tables here, here and here, have been collected from different sources and have always been in the public domain. More specifically, they are being made available at this web site in accordance with the Creative Commons CC0 licence"

The three "here" are links to these tables, and every source file below is linked from one of them (its `listed_at` in
`data_sources/sources.yaml`):

- https://www.voynich.nu/transcr.html#links
- https://www.voynich.nu/extra/legacy.html
- https://www.voynich.nu/extra/sta.html#stalinks

The same section asks users of the site's material to acknowledge it; VCAT's cards cite the transliterators and voynich.nu.
The statement covers the transliterations only: the Voynich script fonts on the site have their own terms, and VCAT bundles
none of them.

## Per-source matrix

<!-- license:matrix:start (rendered by builders.cards.license_matrix from data_sources/sources.yaml) -->
| Source | File | License | Basis | Verified | Redistributed here | Used by |
|---|---|---|---|---|---|---|
| ZL | `data_sources/cache/ZL3b-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-manuscript-metadata, voynich-transcription-mismatch, voynich-transliterations |
| IT | `data_sources/cache/IT_ivtff_1a.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/extra/legacy.html | yes | yes | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| IT2a | `data_sources/cache/IT2a-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transliterations |
| CD | `data_sources/cache/CD2a-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| FG | `data_sources/cache/FG2a-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| GC | `data_sources/cache/GC2a-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transcription-mismatch, voynich-transliterations |
| RF1b | `data_sources/cache/RF1b-e.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transliterations |
| VT | `data_sources/cache/VT0e-n.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transliterations |
| LSI | `data_sources/cache/latin-1/LSI_ivtff_0d.txt` | CC0-1.0 | voynich.nu's statement (license_statement): the transliterations collected in its tables are made available under CC0; this file is linked from https://www.voynich.nu/transcr.html#links | yes | yes | voynich-eva, voynich-transliterations |
<!-- license:matrix:end -->

"Verified" is yes when the statement has been read at its source and quoted in this document (S12).

## Pinned but not cached

`data_sources/sources.yaml` lists under `not_cached` the files VCAT pins by URL and SHA-256 but does not commit, each with its
reason: the basic-EVA form of RF1b (VCAT caches the full form). It is CC0-1.0 by the statement above. The Landini-Stolfi
interlinear file (LSI) was pinned here at S12 and is cached since S13.

## What this repository redistributes

- **The source files themselves.** Every cached file is committed in `data_sources/cache/` (the matrix's "Redistributed
  here"), so that every build and test can be rerun from a checkout; the CC0 statement permits this.
- **The derived datasets** (`output/`), built from those files by the builders.
- **The build and test code**, so anyone can rebuild the datasets from the original sources.

## Each dataset's license

<!-- license:datasets:start (rendered by builders.cards.dataset_license_table from data_sources/sources.yaml and the cards) -->
| Dataset | Sources | VCAT annotations | Card license |
|---|---|---|---|
| voynich-eva | ZL, IT, IT2a, CD, FG, GC, RF1b, VT, LSI | yes | `cc-by-4.0` |
| voynich-manuscript-metadata | ZL | yes | `cc-by-4.0` |
| voynich-transcription-mismatch | ZL, IT, CD, FG, GC | yes | `cc-by-4.0` |
| voynich-transliterations | ZL, IT, IT2a, CD, FG, GC, RF1b, VT, LSI | yes | `cc-by-4.0` |
<!-- license:datasets:end -->

The rule (`data_sources/sources.yaml`, `outputs`): every source CC0-1.0 and no VCAT annotations gives `cc0-1.0`; every
source CC0-1.0 with VCAT annotations gives `cc-by-4.0` (the source-derived fields stay CC0-1.0, as the card says); a source
under any other license would give `other`, with each source's terms.

## If you are a rights holder

If you are an author of one of these transcriptions and would like the attribution changed, the terms clarified, or content
removed, please [open an issue](https://github.com/noah-chelednik/voynich-data/issues); it will be acted on promptly.
