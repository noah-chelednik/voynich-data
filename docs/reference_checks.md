# Reference checks

Roadmap item 2.10. VCAT's character and word statistics are compared with values published in the literature, as
acceptance tests (`tests/test_reference_checks.py`): a parse that loses text, keeps markup in a reading, or fuses words
moves these statistics, and each check names the damage it is shown to catch (below). Not every damage moves every
source away from the published values: for FG, keeping uncertain readings moves them closer. These are checks
of VCAT's data, not a statistics suite and not an analysis of the text.

## The values

Each value is quoted verbatim from a page of voynich.nu, the upstream site of the transliterations, fetched on the date
recorded in `data_sources/references.yaml` and pinned there by the SHA-256 of its bytes. The pages are kept offline under
`docs/reference/` (not in the repository: their redistribution rights are not established);
`python scripts/check_references.py` checks every pin and every quote against them (`--fetch` reads the site instead).

| Check | Source | Measure | Published value | Tolerance | Where |
|---|---|---|---|---|---|
| `zl-characters` | ZL | characters | 188,862 | 0.05 of the value | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS ZL transcr. (Eva)', column 'Nr. of chars.' |
| `zl-h1` | ZL | h1 | 3.862 | 0.03 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS ZL transcr. (Eva)', column 'Character entropy' |
| `zl-h2` | ZL | h2 | 1.836 | 0.05 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 2, row 'Voynich MS ZL transcr (Eva)', conditional character entropy |
| `fg-characters` | FG | characters | 142,770 | 0.05 of the value | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS FSG transcr.', column 'Nr. of chars.' |
| `fg-h1` | FG | h1 | 3.829 | 0.03 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS FSG transcr.', column 'Character entropy' |
| `fg-h2` | FG | h2 | 2.052 | 0.05 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 2, row 'Voynich MS FSG transcr', conditional character entropy |
| `cd-characters` | CD | characters | 66,587 | 0.05 of the value | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS (part) C-D transcr.', column 'Nr. of chars.' |
| `cd-h1` | CD | h1 | 3.857 | 0.03 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 1, row 'Voynich MS (part) C-D transcr.', column 'Character entropy' |
| `cd-h2` | CD | h2 | 2.085 | 0.05 bits | [Voynich MS - what we learn from entropy](https://www.voynich.nu/extra/sol_ent.html), Table 2, row 'Voynich MS (part) C-D transcr', conditional character entropy |
| `zl-word-tokens` | ZL | tokens | 37,919 | 0.05 of the value | [Voynich MS - Analysis - Words](https://www.voynich.nu/a4_word.html), Section 4.1, citing Reddy and Knight, with note 2 (the file 'voynich.now', Currier alphabet) |
| `zl-word-types` | ZL | types | 8,114 | 0.1 of the value | [Voynich MS - Analysis - Words](https://www.voynich.nu/a4_word.html), Section 4.1, citing Reddy and Knight, with note 2 (the file 'voynich.now', Currier alphabet) |

## How VCAT computes them

`vcat/reference.py`, over the committed build read through `vcat.load` under the profile `analysis-v1`:

- the words of a reading are the EVA tokenizer's (`vcat/words.py`); uncertain spaces are word boundaries;
- a character is a glyph of a word: a high-ASCII code `@NNN;` is one character, the apostrophe of a ligature's glyphs is
  a character as written;
- word spaces are not characters, and character pairs are counted within words, as the published tables count them
  ("In these figures, spaces have not been counted as characters");
- `h1` is the single-character entropy in bits; `h2` the conditional character entropy, the pair entropy less `h1`, the
  published table's definition.

## Why the tolerances

The published counting rules for ligatures, rare glyphs and uncertain readings are not stated, the files compared may be
of different dates (ZL is cached here as version 3b of 13/05/2025; the entropy page was updated 10/12/2024), and the word
counts were measured on another transliteration in another alphabet. Each tolerance (a fraction of the value for a count, bits for an entropy), and why it is the size it is, is
recorded with its value (`why` in `data_sources/references.yaml`). Every check also names the kinds of damage it is shown to fail on (`control`), and the suite shows each one failing
there: markup left in the reading (the `raw-v1` profile) fails every `h1` check; uncertain readings kept
(`diplomatic-v1`) fails ZL's and CD's `h1` and ZL's `h2`; a tenth of the loci lost fails every character and word-token
count; every locus but paragraph text lost fails ZL's character and token counts; word division lost (a reading's words
fused) fails every `h2` check and ZL's word counts. A check is only as sharp as its control: a damage not named there may
pass it.

## What the checks do not establish

That VCAT's statistics agree with the literature within these tolerances is evidence that the data is complete and
cleanly read, at the level of whole-text counts and only against the damages the controls show the checks catch. It does not check any single reading, and it states nothing about what the text means.
