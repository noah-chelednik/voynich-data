# VCAT Roadmap

Goal: the most complete, faithful, and trustworthy open Voynich data source —
built for quality alone, not credit, papers, or conferences. Supersedes the
June launch plan (`ACTION_PLAN.md`, kept as history). The defect table below is
the state measured on 2026-10-08, when this plan was written; the current state

**The one rule:** VCAT is a faithful distribution of Zandbergen's
transliterations, not an edition. The default view is the source text,
structurally parsed. Every interpretation (normalization, section labels,
scribal hands, page orders, agreement scores) is an optional, named,
versioned, attributed layer.

**Definition of correct:** the parsed data rebuilds the source IVTFF file
byte-for-byte. Tests read the upstream files; no hand-written expected counts.

---

## The state the plan started from (2026-10-08)

Nothing has been published since; the items below record what has changed.

Published at the time: `Ched-ai/voynich-eva` (4,072 lines, ~2,300 downloads),
`-manuscript-metadata`, `-transcription-mismatch`. Local, GitHub (472ef73) and
HF are in sync. 343 tests pass, CI green, builds reproducible.

Known defects in the published data:

| # | Defect | Impact | Where |
|---|---|---|---|
| D1 | `{...}` stripped as a comment; in IVTFF 2.0 it marks ligatures (glyph data) | 351 rows lose glyphs, e.g. `dlo{ct}o` → `dloo`, `odar.{c'y}.shol` → `odar..shol` | `vcat/text_processing.py:43`, `parsers/ivtff_parser.py` (`extract_text`), `builders/build_mismatch_index.py:210`, `docs/eva_alphabet.md:143` |
| D2 | `<->` (drawing interruption) removed with no separator | 616 rows fuse words, e.g. `cthyd<->otar` → `cthydotar` | `vcat/text_processing.py:50` (used by the builder) and `builders/build_mismatch_index.py:209`; the parser's `extract_text` already turns it into a space |
| D3 | `LOCUS_PATTERN` rejects letter subtypes (`Lz Lf Ls Lc Ln Lt Ri Ro Cc Pb Pc Pt Pr`…) and `&`/`~` locators; `PAGE_PATTERN` rejects the `<fRos>` page header; non-strict mode skips silently | ZL: 1,313 of 5,385 loci dropped (measured 2026-10-08), incl. all 160 fRos loci: zodiac f70–f73 empty, labels, circular/radial text, `Pb` paragraph text. GC drops 1,297, IT 1,146, FG 80, CD 42 | `parsers/ivtff_parser.py:290-291` |
| D4 | Validators/tests hard-code the defect | 4072/206/226 and thresholds (`>4000`, `>200`, `>=220`, `>3000`) locked in; 7 real-file tests always skip | `validators/verify_invariants.py:169,180`, `builders/build_eva_lines.py:36,345,347,672,706`, `builders/__init__.py`, several test files; two fixtures look in `raw_sources/` (files are in `cache/`): `tests/conftest.py:291`, `tests/test_parsers.py:141-146` |
| D5 | Mismatch compares raw text, deletes `[a:b]`, doesn't map `,`→`.` | "16% disagree / 29% agree" headline likely ~8.6% / ~44% | `builders/build_mismatch_index.py` |
| D6 | `text_clean` is an undocumented mix: keeps 1,668 `,` and 80 `@NNN;`, silently picks first `[a:b]` | No reproducible definition of "clean" | `vcat/text_processing.py` |
| D7 | `line_id` (`f1r:1`) discards IVTFF locus type (`@P0`, `&Lz`…) | Structural info lost for labels/circular text | `builders/build_eva_lines.py` |
| D8 | Paperwork: 4 version numbers (0.2.3 / 0.1.0 / "1.0.0" / MIT-only), `sources.yaml` says ZL3a + `to_verify`, only ZL fetchable, `SOURCES_LICENSE.md` says raw files aren't redistributed (they are), dataset license "research-use" though upstream is CC0, card says "complete transcription", README `build_metadata` command exits 2, notebooks never run | Trust and reproducibility | various |

Upstream licensing: voynich.nu/roadmap.html states the transliterations are
public domain under CC0; acknowledge the source and link back. Landini's Eva
font is NOT free for commercial use — never bundle it. Landini died Oct 2025.

---

## Phase 1 — Faithful and correct (≈2–4 weeks)

- [ ] **1.0 Freeze the current state first.** (Owner ruling 2026-10-08: publish ONCE, at the end of
      the whole run; this freeze is the first block of `RELEASE_COMMANDS.md`, run at
      that single publish, before anything new is uploaded.) Enable GitHub↔Zenodo, tag
      `v0.2.3` as-is, get a DOI, tag the HF repos at the same revision. Users
      of the 4,072-row data can pin it before anything changes.
- [x] **1.1 Parser accepts every locus.** Regex for full IVTFF 2.0 locus
      syntax (all locators incl. `&` `~`, letter subtypes) and every page
      header (incl. `<fRos>`), for every cached source (IT declares IVTFF
      1.7). Unknown syntax → error in strict mode, recorded warning
      otherwise. Never silent.
- [x] **1.2 Raw + structured markup layer.** Every row carries:
      - `text_raw`: the IVTFF text byte-for-byte;
      - parsed markup as fields: alternates `[a:b]` (all readings), ligatures
        `{...}`, uncertain spaces `,`, illegible `?`/`*`, high-ASCII `@NNN;`,
        inline comments `<!...>`, drawing breaks `<->`, other `<$>`-style
        markers;
      - `locus_type` (e.g. `@P0`, `&Lz`) and source line number.
- [x] **1.3 Fix D1/D2** as a consequence of 1.2: ligatures kept as glyph
      data; `<->` treated as a word boundary in normalized text.
- [x] **1.4 Round-trip test.** Rebuild IVTFF from parsed data and diff
      against the source; must be byte-identical for every cached source.
- [x] **1.5 Real validation.** Loss accounting: every source locus is emitted
      or explicitly reported. Expected counts derived from the source file at
      test time. Fix both real-file fixture paths. Remove all hard-coded
      counts and thresholds. Build fails on any unaccounted locus. Validate
      the built rows against `schemas/` (CI today only checks the schema
      files themselves).
- [x] **1.6 Normalization profiles.** Named, versioned, documented rule sets
      derived from the raw layer: `raw`, `diplomatic`, `analysis-v1` (and e.g.
      `no-uncertain-spaces`). Each rule tested on real lines (f1r:7, f1r:17,
      f1r:19, f10r:11). `text_clean` becomes an alias for one named profile.
- [x] **1.7 Data model + faithfulness contract.** `docs/data_model.md`
      rewritten: every field, the IVTFF → schema mapping table, what VCAT
      guarantees and what it does not. Fix `docs/eva_alphabet.md` (`{}` =
      ligature).
- [x] **1.8 Mismatch fix.** Compare a named normalization profile, keep
      alternates, map `,` correctly. Correct the headline everywhere (README,
      cards, CHANGELOG) with an explicit erratum.
- [x] **1.9 Paperwork.** One version number everywhere (pyproject,
      CITATION.cff, CHANGELOG, cards). Per-source license matrix (ZL CC0 per
      voynich.nu; check GC/v101, IT, LSI, RF1b, VT individually). Data CC0
      where upstream permits, VCAT-original annotations CC-BY-4.0, code MIT.
      `sources.yaml` with URL + SHA-256 + upstream version for every source.
      Fix README commands; run notebooks in CI. Remove absolute local paths
      from build reports. Cards: "known limitations" section, no
      "complete" claims that tests don't prove.
- [ ] **1.10 Release v1.0.0** (Owner ruling 2026-10-08: not released after Phase 1; it ships once,
      count change (4,072 → 5,385), the D1/D2 corrections, and the mismatch
      erratum, with migration notes. New DOI.

**Exit criteria:** round-trip test passes for all cached sources; zero
unaccounted loci; no hard-coded counts in tests or validators; every number in
README and cards is produced by the build; the local gate fully green.


branch rules, gate rules, measured corrections), revised 2026-10-08.

---

## Phase 2 — Complete and connected (≈3–9 months part-time)

- [x] **2.1 Upstream tracking.** Scheduled CI job checksums voynich.nu files
      and opens an issue on change; each release ships a source diff report
      (loci added / removed / changed) and pins upstream versions.
- [x] **2.2 Stability policy.** SemVer for schema, `STABILITY.md`: IDs are
      never reused or silently changed; deprecations announced one release
      ahead.
- [x] **2.3 All transliterations, one schema.** ZL, RF1b, IT, VT, GC, FG, CD,
      LSI — each as its own config, keyed by Zandbergen's `folio.locus` IDs
      (already harmonized upstream) plus locus type. Each source keeps its own
      alphabet (v101, Currier, FSG are not EVA); cross-alphabet mapping
      tables are documented and optional. Per-source coverage matrix and a
      source-dependency note (RF1b derives from ZL+GC; LSI contains C/F/H).
      Mapping tables deferred beyond this release: no pinned source holds one
      (DECISIONS Q82).
- [x] **2.4 IIIF links.** Page → canvas mapping to Yale's manifest
      (`collections.library.yale.edu/manifests/2002046`, 213 canvases). Link,
      never rehost.
- [x] **2.5 Physical structure layer.** Bifolia/conjugate leaves, foldout
      panels, quire structure. Page orders as named optional tables: current
      foliation (default), plus attributed alternatives (e.g. Layfield–Davis
      2026 singulion hypothesis).
- [x] **2.6 Word-level config.** One row per word with positional features
      (word index, line/paragraph initial/final, line-in-paragraph), joined
      hand / Currier language / section / quire. One documented EVA
      tokenizer.
- [x] **2.7 Variant table (not a consensus).** Per-locus and per-word aligned
      readings across sources, agreement scores, alignment algorithm recorded.
      Optional majority-vote column only as a labelled baseline, never the
      default.
- [x] **2.8 Attribution for interpretive layers.** Section labels marked as
      VCAT's judgement; Davis hands and Currier languages attributed to their
      sources; each layer has its own license field.
- [x] **2.9 Minimal Python API.** `vcat.load(source=, unit=, profile=)`.
      Fold all layers into `Ched-ai/voynich-eva` as configs (don't create a
      new umbrella repo; keep existing users' paths working).
- [x] **2.10 Reference checks.** Word/token counts and h1/h2 entropy compared
      against published literature values as acceptance tests (not a
      published "statistics suite").
- [x] **2.11 Errata path.** Public issue templates for transcription errors
      and data bugs; errata log in the repo. Transcription errors are reported
      upstream, never forked.

---

## Deferred (revisit only if users ask)

- Alternative glyph tokenizations (ch/sh/aiin as units, v101-style, etc.)
- Control corpora (Naibbe, Timm generator, gibberish) — link only; their
  licenses and parameter choices are other people's research
- Benchmark tasks, fixed splits, leaderboards — obvious tasks leak through
  page structure; risks turning data into research claims
- A broader statistics suite beyond 2.10
- Word/glyph bounding boxes on IIIF canvases, illustration region annotation

## Out of scope

- Decipherment of any kind
- Conferences, papers, endorsements, outreach (owner's choice)
- Rehosting images; bundling the Eva font

## Open decision

- Reporting parser/transcription discrepancies to Zandbergen (upstream QA,
  not promotion). Reviewer A recommends it as the only external correctness
  check available; owner's call.
