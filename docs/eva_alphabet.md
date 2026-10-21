# EVA Alphabet Reference

The European Voynich Alphabet (EVA) is the standard transcription system for the Voynich Manuscript. This document provides a complete reference for the EVA character set used in VCAT.

## History and Purpose

EVA was developed in the late 1990s by:
- René Zandbergen
- Gabriel Landini
- Jacques Guy

**Purpose**: Provide a standardized, ASCII-compatible way to represent Voynich glyphs for computer processing and scholarly communication.

**Key Design Principles**:
1. One-to-one mapping (mostly) between Voynich glyphs and ASCII characters
2. Easily typed on standard keyboards
3. Designed for searchability and computation

**Reference**: [voynich.nu EVA page](http://www.voynich.nu/extra/eva.html)

---

## Basic Glyphs (17 Characters)

These form the core EVA alphabet and account for the vast majority of text.

| Char | Description | Position | Frequency | Notes |
|------|-------------|----------|-----------|-------|
| `a` | Bench-loop | Common everywhere | High | Often word-initial |
| `c` | C-shape | Often with h | High | Forms compounds |
| `d` | Daiin-like | Common | High | Core character |
| `e` | e-shape | Often word-final | High | Very common |
| `h` | h-shape | After c, s | High | Part of compounds |
| `i` | Single stroke | Sequences (ii, iii) | High | Often repeated |
| `k` | Gallows tall | Paragraph start | Medium | Gallows character |
| `l` | l-shape | Common | Medium | Core character |
| `m` | m-shape | Less common | Medium | Lower frequency |
| `n` | n-shape | Common | Medium | Core character |
| `o` | Circle | Word-initial | High | Often starts words |
| `p` | Gallows looped | Various | Low | Gallows character |
| `q` | q-shape | Word-initial | High | Usually +o follows |
| `r` | r-shape | Common | Medium | Core character |
| `s` | s-shape | Common | High | Part of compounds |
| `t` | Gallows simple | Various | Medium | Gallows character |
| `y` | y-shape | Word-final | High | Very common ending |

### Frequency

This document gives no glyph counts or percentages: any number about the transliteration is computed from the source by the
build or by the user (for example from `text_clean` of `output/eva_lines.jsonl`), never typed here (principle 2).

---

## Compound Glyphs (6 Sequences)

These represent single visual units written as character pairs or triplets.

| Compound | Description | Frequency | Notes |
|----------|-------------|-----------|-------|
| `ch` | Benched C-gallows | Very High | Most common compound |
| `sh` | Benched S-gallows | High | Second most common |
| `cth` | C with tall gallows | Low | Gallows with pedestal |
| `ckh` | C with k gallows | Low | Gallows with pedestal |
| `cph` | C with looped gallows | Rare | Gallows with pedestal |
| `cfh` | C with f gallows | Rare | Gallows with pedestal |

### Recognition

In analysis, compound glyphs should generally be treated as single units:
- Token `chedy` = 4 glyphs: `ch` + `e` + `d` + `y`
- Token `shol` = 3 glyphs: `sh` + `o` + `l`

---

## Rare Glyphs (8 Characters)

These appear infrequently but are valid EVA characters.

| Char | Description | Frequency | Notes |
|------|-------------|-----------|-------|
| `f` | f-gallows | Low | Rare gallows variant |
| `g` | g-shape | Rare | Uncertain identification |
| `x` | x-shape | Rare | Cross-like glyph |
| `j` | j-shape | Rare | Hook character |
| `v` | v-shape | Rare | V-like glyph |
| `b` | b-shape | Rare | Added in extended EVA |
| `u` | u-shape | Rare | Added in extended EVA |
| `z` | z-shape | Rare | Added in extended EVA |

**Note**: `b`, `u`, `z` were added to EVA to handle visual variants not captured by the original alphabet.

---

## Special Marks and Separators

These are not glyphs: they are the special characters of IVTFF 2.0 (Table 3, the `< > . , { } [ : ] @ ; ? /` set) and its
in-line comments (Table 11). Their meanings below are the specification's; `docs/data_model.md` (section 4) says where
each goes in the dataset.

### Word spaces

| Mark | Meaning (IVTFF 2.0) |
|------|---------------------|
| `.` | An apparent word space (Table 10) |
| `,` | An uncertain word space: the transcriber doubted the space was wide enough (Table 10) |
| `<->` | The text is interrupted by a drawing; implies a word space (Table 11) |
| `<~>` | As `<->`, and the text left and right is not well aligned vertically (Table 11) |

### Uncertain and unreadable text

| Mark | Meaning (IVTFF 2.0) |
|------|---------------------|
| `?` | One unreadable character (Table 10) |
| `???` | An unknown number of unreadable characters (Table 10) |
| `[a:b]`, `[a:b:c]` | An uncertain reading: two or three options, the most likely first (Table 10) |

`!` and `*` have no special meaning in IVTFF 2.0. Older EVA transcriptions used them as illegibility markers, and VCAT's
`has_illegible` flag and the `analysis-v1` profile still read them that way in EVA files (DECISIONS Q39).

### Glyph data written with markup

| Markup | Meaning (IVTFF 2.0) |
|--------|---------------------|
| `{ct}` | A ligature: the glyphs inside are written joined (Table 10). Braces are NOT a comment; the glyphs are text |
| `@NNN;` | A high-ASCII character, NNN from 128 to 255 (Table 10); a glyph, not markup to remove |

### Structure and comments

| Markup | Meaning (IVTFF 2.0) |
|--------|---------------------|
| ` /` at a line end, `/ ` at the start of the next | The locus text continues on the next line (Table 10, section 5.5) |
| `<%>` | Start of a paragraph (Table 11, section 6.9) |
| `<$>` | End of a paragraph (Table 11, section 6.9) |
| `<!text>` | A free textual comment, at most 80 characters with `<` and `>` (Table 11) |
| `<@X=y>` | A text tag: sets variable X to y from this line on (Table 11, section 6.8) |

---

## Character Categories

VCAT categorizes EVA characters for validation:

```python
from vcat import CharacterCategory

# Categories
CharacterCategory.BASIC      # a, c, d, e, h, i, k, l, m, n, o, p, q, r, s, t, y
CharacterCategory.RARE       # f, g, x, j, v, b, u, z
CharacterCategory.COMPOUND   # ch, sh, cth, ckh, cph, cfh
CharacterCategory.SPECIAL    # ., ,, space
CharacterCategory.EDITORIAL  # ?, !, *, [, ], etc.
CharacterCategory.UNKNOWN    # Not recognized
```

---

## Validation

### Valid EVA Text

```python
from vcat import validate_eva_text

result = validate_eva_text("fachys.ykal.ar.ataiin")
print(result.is_valid)      # True
print(result.char_count)    # 18
print(result.word_count)    # 4
```

### Character Check

```python
from vcat import EVA_BASIC, EVA_RARE, EVA_SINGLE

'a' in EVA_BASIC     # True
'x' in EVA_RARE      # True
'z' in EVA_SINGLE    # True (BASIC | RARE)
'@' in EVA_SINGLE    # False (editorial)
```

---

## Comparison with Currier Alphabet

Prescott Currier developed an earlier transcription system in the 1970s. Key differences:

| Feature | EVA | Currier |
|---------|-----|---------|
| Case | Lowercase | Uppercase |
| Gallows | k, t, p, f | K, T, P, F |
| Compounds | ch, sh | C, S (single char) |
| Character set | 25+ chars | ~20 chars |
| Resolution | More detail | More collapsed |

### Approximate Mapping

| EVA | Currier | Notes |
|-----|---------|-------|
| a | A | Direct |
| ch | C | EVA compound → Currier single |
| o | O | Direct |
| e | E | Direct |
| sh | S | EVA compound → Currier single |
| k | K | Direct |
| ... | ... | ... |

**Note**: Mapping is not perfectly bijective; some distinctions are lost.

---

## Common Patterns

### Word-Initial Patterns

| Pattern | Example | Frequency |
|---------|---------|-----------|
| `q` + `o` | qokeedy | Very common |
| `o` | okaiin | Common |
| `ch` | chedy | Common |
| `sh` | shedy | Common |
| `d` | daiin | Common |

### Word-Final Patterns

| Pattern | Example | Frequency |
|---------|---------|-----------|
| `y` | chedy | Very common |
| `dy` | chedy | Very common |
| `n` | daiin | Common |
| `m` | cheom | Less common |
| `l` | chol | Common |

### Common Words

Frequent words include `daiin`, `chedy`, `qokeedy`, `ol` and `ar`. Their counts are not typed here: they depend on the
transliteration and on how uncertain spaces are read, so compute them from a named profile, for example by splitting
`text_clean` of `output/eva_lines.jsonl` at `.` (and at `,`, or not: `no-uncertain-spaces-v1`).

---

## Notes for Analysts

### Counting Characters

When counting characters:
1. Exclude word separators (`.`, `,`, space)
2. Count compound glyphs as single units for some analyses
3. Exclude the illegibility mark `?` and, in EVA text, the legacy markers `!` and `*`, as the profile `analysis-v1`
   does (`vcat/profiles.py`)

### Tokenization

VCAT provides `text_raw` (the source text, byte for byte), `text` (wraps joined) and `text_clean` (the profile
`analysis-v1`), plus the other named profiles in `vcat/profiles.py`; see `docs/data_model.md`, section 5.

### Uncertain readings

In IVTFF 2.0 a `?` stands for an unreadable character, not for doubt about the character before it. Doubt between readings is
written `[a:b]`; `text_clean` keeps the first, and `alternates` keeps them all.

---

## References

1. Zandbergen, R. "The European Voynich Alphabet." voynich.nu
2. Landini, G. "EVA Extensions." Various publications
3. Stolfi, J. "Voynich Manuscript Transcription Files." UNICAMP

---

*Last updated: 2026-10-17 (roadmap item 1.7).*
