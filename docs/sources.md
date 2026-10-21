# VCAT Data Sources

The record of every source is `data_sources/sources.yaml`: for each file in `data_sources/cache/`, its upstream URL, SHA-256,
upstream version (the version line of the file's own header, or, for a file whose header carries none, the version
voynich.nu's table lists, which its file name carries) and license. The suite checks that record against the
cache (`tests/test_sources.py`), and `vcat-verify` checks it on demand. This guide describes the sources; where it and
`data_sources/sources.yaml` could disagree, `data_sources/sources.yaml` is the record.

## The cached sources

All are IVTFF files published on voynich.nu by René Zandbergen. Each was fetched from its recorded URL on 2026-10-17 (S12)
with the pinned SHA-256 (the five cached before then had exactly those bytes upstream), and `scripts/fetch_sources.py`
fetches any of them that is missing. Every one is built into `voynich-transliterations` (one schema, one row per reading);
ZL also into the EVA and metadata datasets, ZL and IT 1a into the mismatch index.

### ZL: Zandbergen-Landini transliteration (EVA)

**File**: `data_sources/cache/ZL3b-n.txt`
**Version**: 3b of 13/05/2025 (its header: "ZL transliteration file, updated from EVMT project")
**Transliterators**: René Zandbergen, Gabriel Landini
**Used by**: every dataset. It is VCAT's primary source: the EVA rows (`voynich-eva`), the page, folio and quire metadata (from
its page headers), and one side of the mismatch index.

### IT: Takahashi transliteration (EVA)

**File**: `data_sources/cache/IT_ivtff_1a.txt`
**Version**: 1a of 27/12/2022 (its header: "Extracted from LSI_ivtff_0d.txt", the Landini-Stolfi interlinear file); voynich.nu
now lists it among its previous versions (https://www.voynich.nu/data/previous/)
**Transliterator**: Takeshi Takahashi
**Used by**: the mismatch index, as the other side of the comparison with ZL.

### IT2a: Takahashi transliteration, version 2a (EVA)

**File**: `data_sources/cache/IT2a-n.txt`
**Version**: 2a of 02/02/2023, modified 25/06/2025 (its header), the current IT on voynich.nu
**Transliterator**: Takeshi Takahashi
**Used by**: `voynich-transliterations`. The mismatch index keeps IT 1a, the version its published comparison used (DECISIONS
Q67); both versions are in `voynich-transliterations`.

### CD: Currier transliteration (Currier alphabet)

**File**: `data_sources/cache/CD2a-n.txt`
**Version**: IVTFF version 2a of 02/02/2023 (its header: "Currier transliteration from file voynich.orig")
**Transliterators**: Prescott Currier, Mary D'Imperio
**Used by**: the mismatch index, for whether it holds each locus (`sources_present`), none of its text; it is parsed and
rebuilt byte for byte by the suite (`tests/test_round_trip.py`).

### FG: First Study Group transliteration (FSG alphabet)

**File**: `data_sources/cache/FG2a-n.txt`
**Version**: IVTFF version 2a of 02/02/2023 (its header: "FSG transliteration, file FSG.txt. Source: Reeds, 18 June 1994")
**Transliterators**: the First Study Group (William Friedman)
**Used by**: the mismatch index, for whether it holds each locus (`sources_present`), none of its text; parsed and
rebuilt by the suite.

### GC: Glen Claston transliteration (v101 alphabet)

**File**: `data_sources/cache/GC2a-n.txt`
**Version**: IVTFF version 2a of 05/02/2023, modified 25/06/2025 (its header: "Original file: voyn101.txt")
**Transliterator**: Glen Claston (Tim Rayhel)
**Used by**: the mismatch index, for whether it holds each locus (`sources_present`), none of its text; parsed and
rebuilt by the suite.

### RF1b: Reference transliteration (EVA, full form)

**File**: `data_sources/cache/RF1b-e.txt`
**Version**: 1b, as voynich.nu's table of transliteration files lists it (the file's header carries no version line; its name
does)
**Origin**: combined automatically from the GC and ZL transliterations by René Zandbergen, defined in the STA alphabet and
given here in EVA; a source derived from two others, not an independent reading
**Used by**: `voynich-transliterations`.

### VT: voynichese.com transliteration (EVA)

**File**: `data_sources/cache/VT0e-n.txt`
**Version**: 0e, as voynich.nu's table lists it (no version line in the header)
**Transliterator**: mainly Takeshi Takahashi, by way of LSI. voynich.nu's README says it differs from IT2a "only in
details related to unreadable characters" (https://www.voynich.nu/data/000_README.txt); the cached files differ more:
VT also marks other inline markup differently and lacks some of IT2a's loci (review 993fba3d finding 1)
**Used by**: `voynich-transliterations`.

### LSI: Landini-Stolfi interlinear file (EVA, several transliterations per locus)

**File**: `data_sources/cache/latin-1/LSI_ivtff_0d.txt` (apart from the others: its encoding is not the format's ASCII)
**Version**: its header's release line, "Release 1.6e6 - ?? Dec 1998" (Jorge Stolfi's); voynich.nu's IVTFF conversion is
`0d`, still beta ("It still requires checking by comparison against the input file", https://www.voynich.nu/data/beta/000_README.txt)
**Transcribers**: one reading per transcriber code of each locus (`<f1r.1,@P0;H>`, `;C`, `;F`, ...); Takahashi's (`H`) is
the source of IT and VT
**Format**: IVTFF 1.5, so its paragraphs have end marks only (the start mark came with format 1.6); its few bytes above 127,
all in comments, are Latin-1 (the registry's `encoding: latin-1`); four lines number a locus `44a`, which IVTFF does not
allow: the parser reports them, never drops them (the registry's `nonconforming`)
**Used by**: `voynich-transliterations`.

## How the sources depend on each other

The sources are not independent (principle 4: no consensus reading), so agreement between two of them is not two
confirmations:

| source | derives from |
|---|---|
| ZL | its transcribers' own reading (Zandbergen, Landini) |
| GC | its transcriber's own reading (Glen Claston, v101) |
| RF1b | ZL and GC, combined automatically upstream |
| IT, IT2a | LSI's `H` readings (Takeshi Takahashi), extracted |
| VT | LSI's `H` readings, as voynichese.com gives them; differs from IT2a in how it marks unreadable characters and other inline markup, and lacks some of IT2a's loci |
| CD | Currier's and D'Imperio's transliteration; LSI's `C` readings descend from it, in EVA, with later additions (their loci are not the same sets) |
| FG | the First Study Group's; LSI's `F` readings descend from it, in EVA (their loci are not the same sets) |
| LSI | several transliterations, one per transcriber code (its header defines them) |

## No mapping between alphabets

The sources keep their own alphabets: ZL, IT, IT2a, RF1b, VT and LSI write EVA; CD writes Currier's alphabet, FG the First
Study Group's, GC v101. VCAT applies no mapping between them and publishes none: no cached or pinned file holds one, and a
mapping between these alphabets is not one to one, so any table VCAT wrote would be its own judgement. The variant tables
(roadmap item 2.7, `docs/data_model.md` section 12) compare EVA readings only; the other sources are listed as holding a
locus. Mapping tables are deferred beyond this release (DECISIONS Q82).

## Coverage

Every cached source is built into the dataset `voynich-transliterations` (`builders/build_transliterations.py`), one row per
reading. Per source, from its build report; the page-by-page matrix is `output/transliterations/coverage_matrix.csv`:

<!-- sources:coverage:start (rendered by builders.cards.transliterations_statistics from output/transliterations/transliterations_report.json; checked by tests/test_transliterations.py) -->
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
<!-- sources:coverage:end -->

## Sources pinned but not cached

`data_sources/sources.yaml` lists under `not_cached` the files VCAT pins by URL, SHA-256 and version but does not commit, each
with its reason:

- **RF1b, basic EVA** (https://www.voynich.nu/data/RF1b-er.txt): voynich.nu's simplification of RF1b; the full form is cached.

## Verifying the cache

```bash
vcat-verify                              # or: python -m data_sources.verify_sources
```

For every record it checks that the file exists, that its SHA-256 is the pinned one and the one
`data_sources/checksums_all.txt` lists, that its first line is an IVTFF header, and that its header carries the recorded
upstream version (or, for a listed version, that its file name carries it and its header has no version line); a cache file without a record also fails. It writes the machine receipt `reports/source_verification.json`
and renders the human receipt `reports/source_verification_report.md` from it, and exits 0 only when every check passes.
`--online` also fetches every fetched source from its pinned voynich.nu URL and checks the served bytes against the pin
(network access; the same check as `scripts/check_upstream.py`, [upstream tracking](upstream_tracking.md)).

The checksums file can be checked with the standard tool:

```bash
cd data_sources/cache && sha256sum -c ../checksums_all.txt
```

## Fetching a missing source

```bash
python scripts/fetch_sources.py
```

For each record marked `url_fetched` (every cached source), it downloads the file from the recorded URL when it is missing from
the cache, to a temporary file beside it, and moves it in only when the bytes have the pinned SHA-256; otherwise it fails and
the cache is as it was. A cached file with another hash is reported and left in place; the cache is never edited. The cache
is committed, so a checkout needs no fetch.

## If an upstream file changes

A new upstream version is a new file: cache it under its own name, add its record to `data_sources/sources.yaml` (URL, SHA-256, the
header's version line or the listed version, the table that lists it, license), add its line to `data_sources/checksums_all.txt`, and run the suite. The builders
record the SHA-256 of the file they read in every build report, and the release manifest says whether it is the pinned one.

## Licensing

The per-source license matrix and what VCAT redistributes are in `docs/SOURCES_LICENSE.md`.

## Related Documentation

- `docs/data_model.md`: the rows, the profiles, and the faithfulness contract
- `docs/SOURCES_LICENSE.md`: the license of each source and of VCAT's outputs
- `docs/eva_alphabet.md`: the EVA character set
