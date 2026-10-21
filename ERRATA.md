# Errata

Every correction to published data, newest first (roadmap item 2.11). Each entry names what was wrong, which releases carry
it, what corrects it, and how to tell which you have. An entry is never removed. Report a data bug with the issue template
"Data bug"; a reading the transliteration itself gets wrong is a transcription error, reported upstream ("Transcription
error"), never corrected here (`STABILITY.md`, Corrections).

The entries below are the defects Phase 1 found in release 0.2.3, the one published (D1 to D8 of `docs/ROADMAP.md`). Their
corrections ship in release 1.0.0; the counts are those measured on the 0.2.3 output (the roadmap's of 2026-10-08,
with the units corrected by review ea46bb38).

| id | affects | what was wrong in 0.2.3 | corrected by | how to tell |
|---|---|---|---|---|
| E-008 (D8) | all three datasets and the repository | four different version numbers; `data_sources/sources.yaml` named the wrong ZL version and an unfetchable source set; the provenance document denied redistributing the source files the repository holds; a "research use" dataset license where the upstream is CC0; cards claiming a "complete transcription"; a README command that exited 2; notebooks never run | item 1.9: one version, `data_sources/sources.yaml` with URL, SHA-256 and upstream version for every cached file, the license matrix, honest cards, commands and notebooks run by the suite | `pyproject.toml`, `CITATION.cff` and the cards state one version; `vcat-verify` passes |
| E-007 (D7) | `voynich-eva` | `line_id` (`f1r:1`) kept no IVTFF locus type (`@P0`, `&Lz`), so labels, circles and radii lost their structure | item 1.2: `locus_type`, `source_line` and the markup fields on every row | rows have a `locus_type` field |
| E-006 (D6) | `voynich-eva` | `text_clean` had no reproducible definition: it kept 2,422 uncertain spaces in 1,668 rows and 80 high-ASCII codes in 75 rows, and silently took the first reading of each alternate | item 1.6: `text_clean` is the named profile `analysis-v1`, its rules published in `docs/data_model.md` and pinned by the suite | the build report's `text_clean_policy` is `analysis-v1` |
| E-005 (D5) | `voynich-transcription-mismatch` | the headline "83.9% agreement, 16.1% substantive disagreement" was wrong in method: ligatures and alternates deleted, words fused at drawing breaks, `,` not a word space, 4,072 loci only, lines at least 95% similar counted as agreeing | item 1.8: exact verdicts through `analysis-v1`, no similarity threshold, every locus of either source; the rebuilt numbers are the erratum table in README, rendered from the build | rows carry `comparison_profile` and one of the six statuses |
| E-004 (D4) | the test suite and validators | tests and validators hard-coded the defective counts (4,072 lines, 206 and 226 pages, thresholds `>4000`, `>200`, `>=220`, `>3000`), so they passed on the defect; 7 real-file tests always skipped | items 1.5 and the S10 gate: counts derived from the sources, a no-literal-count detector, no skip and no xfail (static and at run time) | the suite runs every test; no count is hand-written |
| E-003 (D3) | `voynich-eva`, the metadata datasets | the parser rejected letter subtypes (`Lz Lf Ls Lc Ln Lt Ri Ro Cc Pb Pc Pt Pr`), the `&` and `~` locators and the `<fRos>` page, silently: 1,313 of ZL's 5,385 loci were dropped, all 160 `fRos` loci among them, and of the zodiac pages f70 to f73 only `f70r2` kept rows (14) | items 1.1 and 1.5: the parser accepts every IVTFF 2.0 locus; the build accounts for every source locus and fails on one unaccounted | 5,385 rows for ZL; `unaccounted_loci` is empty in the build report |
| E-002 (D2) | `voynich-eva`, `voynich-transcription-mismatch` | `<->` (an interruption by a drawing) was removed with no separator, fusing the words on either side in 616 rows (`cthyd<->otar` became `cthydotar`) | items 1.2 and 1.6: `<->` is a word space in every profile that reads words | `text_clean` separates the two words |
| E-001 (D1) | `voynich-eva`, `voynich-transcription-mismatch` | `{...}` was stripped as a comment, but in IVTFF 2.0 it marks a ligature (glyph data): 351 rows lost glyphs (`dlo{ct}o` became `dloo`) | items 1.2 and 1.3: ligature glyphs kept, listed in `ligatures` | `text_raw` keeps the braces; `text_clean` keeps the glyphs |

## Retired identifiers

None. An identifier a release retires is listed here with that release (`STABILITY.md`, Identifiers).
