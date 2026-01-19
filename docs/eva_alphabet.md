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

### Frequency Distribution

Based on the ZL transcription (170,607 characters):

```
e ████████████████████████████████ ~17%
o ███████████████████████████████  ~16%
a ████████████████████████████     ~14%
i ██████████████████████████       ~12%
y █████████████████                ~9%
c ██████████████                   ~7%
h █████████████                    ~6%
l ████████████                     ~5%
d ███████████                      ~5%
s ██████████                       ~4%
r █████████                        ~3%
n ███████                          ~2%
q ███                              ~1%
k ██                               ~1%
t ██                               ~1%
p █                                ~0.5%
m █                                ~0.5%
```

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
- Token `chedy` = 3 glyphs: `ch` + `e` + `d` + `y`
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

### Word Separators

| Mark | Meaning | Usage |
|------|---------|-------|
| `.` | Definite word break | Standard separator |
| `,` | Possible word break | Uncertain boundary |
| ` ` | Space | Also word break |

### Line and Paragraph Markers

| Mark | Meaning | Usage |
|------|---------|-------|
| `-` | Line break/continuation | Word split across lines |
| `=` | Paragraph break | End of paragraph |

### Editorial Markers

| Mark | Meaning | Usage |
|------|---------|-------|
| `?` | Uncertain reading | Transcriber unsure |
| `!` | Illegible | Cannot be read |
| `*` | Editorial insertion | Added by editor |

### IVTFF Markup

| Markup | Meaning |
|--------|---------|
| `[a:b]` | Alternative readings (a or b) |
| `{comment}` | Inline comment |
| `<->` | Line continuation |
| `<%>` | Paragraph start |
| `<$>` | End marker |
| `<~>` | Column separator |
| `<!...>` | Processing instruction |
| `@NNN;` | High-ASCII code |

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

| Word | Count | % |
|------|-------|---|
| daiin | ~500+ | ~1.5% |
| chedy | ~400+ | ~1.2% |
| qokeedy | ~300+ | ~0.9% |
| ol | ~200+ | ~0.6% |
| ar | ~200+ | ~0.6% |

---

## Notes for Analysts

### Counting Characters

When counting characters:
1. Exclude word separators (`.`, `,`, space)
2. Count compound glyphs as single units for some analyses
3. Exclude editorial marks (`?`, `!`, etc.)

### Tokenization

VCAT provides both:
- `text` — Raw transcription with all markup
- `text_clean` — Cleaned text for analysis

### Uncertain Readings

A `?` after a character indicates transcriber uncertainty:
- `a?` — "probably a, but not certain"
- Handle as variant or exclude depending on analysis

---

## References

1. Zandbergen, R. "The European Voynich Alphabet." voynich.nu
2. Landini, G. "EVA Extensions." Various publications
3. Stolfi, J. "Voynich Manuscript Transcription Files." UNICAMP

---

*This document is part of VCAT v0.1.0. Last updated: 2026-01-17*
