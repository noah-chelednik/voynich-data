# Charset Decisions

This document records the decisions made when defining ALLOWED_TEXT_CLEAN_CHARSET.

## Covenant

**Once the charset is decided for a version, it is LOCKED for that version.**

Changing the allowed characters requires:
1. A version bump (at least minor version, e.g., 0.2.x → 0.3.0)
2. Documentation of the rationale in this file
3. CHANGELOG entry explaining the change

This covenant prevents silent policy drift that could break downstream analysis
depending on the v0.2.1 charset definition.

---

## v0.2.1 Charset Definition

### Empirical Analysis

**Date:** 2026-01-18  
**Source:** ZL3b-n.txt  
**Source SHA256:** bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc  
**Script:** scripts/analyze_charset.py

### Analysis Results

```
============================================================
VCAT Charset Empirical Analysis
============================================================

Total text segments analyzed: 5612
Unique characters found: 42

All characters found (with counts):
  ✓ '.' (U+002E): 30,129
  ✓ 'o' (U+006F): 25,619
  ✓ 'e' (U+0065): 20,425
  ✓ 'y' (U+0079): 17,879
  ✓ 'h' (U+0068): 17,613
  ✓ 'a' (U+0061): 14,818
  ✓ 'd' (U+0064): 13,215
  ✓ 'c' (U+0063): 13,087
  ✓ 'i' (U+0069): 11,872
  ✓ 'k' (U+006B): 10,970
  ✓ 'l' (U+006C): 10,658
  ✓ 'r' (U+0072): 7,595
  ✓ 's' (U+0073): 7,356
  ✓ 't' (U+0074): 6,908
  ✓ 'n' (U+006E): 6,186
  ✓ 'q' (U+0071): 5,435
  ✓ ',' (U+002C): 2,748
  ✓ 'p' (U+0070): 1,643
  ✓ 'm' (U+006D): 1,071
  ✓ 'f' (U+0066): 483
  ? '?' (U+003F): 209
  ✓ 'g' (U+0067): 154
  ✓ '@' (U+0040): 116
  ✓ ';' (U+003B): 116
  ✓ '1' (U+0031): 107
  ✓ '2' (U+0032): 41
  ✓ 'x' (U+0078): 41
  ✓ '7' (U+0037): 35
  ✓ '6' (U+0036): 29
  ? ''' (U+0027): 27
  ✓ '4' (U+0034): 27
  ✓ '0' (U+0030): 25
  ✓ '5' (U+0035): 25
  ✓ '3' (U+0033): 22
  ✓ '9' (U+0039): 20
  ✓ '8' (U+0038): 17
  ✓ 'v' (U+0076): 15
  ✓ 'b' (U+0062): 15
  ? 'j' (U+006A): 14
  ✓ 'u' (U+0075): 9
  ✓ 'z' (U+007A): 9
  ? 'I' (U+0049): 1

⚠ Characters NOT in initial expected EVA set:
  - ''' (U+0027): 27 occurrences
  - '?' (U+003F): 209 occurrences
  - 'I' (U+0049): 1 occurrences
  - 'j' (U+006A): 14 occurrences
```

### Decisions

#### Apostrophe (')

**Finding:** Present in 27 occurrences  
**Decision:** Included in VARIANT_CHARS  
**Rationale:** The apostrophe is used as a legitimate variant marker in EVA transcription. 
Examples include `c'y`, `c'o`, `e'a'iin`, `qo'ky`. These represent glyph variants in the 
original manuscript where the transcriber noted uncertainty about the exact form. This is 
standard EVA practice and the apostrophe should be preserved in text_clean for analysis.

#### Question Mark (?)

**Finding:** Present in 209 occurrences  
**Decision:** Stripped from text_clean, preserved in has_uncertain flag  
**Rationale:** The question mark is an uncertainty marker, not manuscript content. It 
indicates the transcriber was uncertain about a reading. It is stripped AFTER the 
has_uncertain flag is computed from the flag_basis, so the uncertainty information is 
preserved in the structured data even though the marker is removed from text_clean.

#### Lowercase j

**Finding:** Present in 14 occurrences  
**Decision:** Added to EVA_CORE  
**Rationale:** While rare, 'j' is a valid EVA character. The original EVA_CORE definition 
was missing 'j'. This has been corrected.

#### Uppercase I

**Finding:** Present in 1 occurrence (f48r.13)  
**Decision:** Lowercased to 'i' during text cleaning  
**Rationale:** This single uppercase 'I' appears to be a transcription error/typo. It is 
normalized to lowercase 'i' in clean_text_for_analysis() to maintain charset consistency.

### Final Charset for v0.2.1

```python
EVA_CORE = frozenset('abcdefghijklmnopqrstuvxyz')
SEPARATORS = frozenset('., ')
HIGH_ASCII_CHARS = frozenset('@;0123456789')
VARIANT_CHARS = frozenset("'")

ALLOWED_TEXT_CLEAN_CHARSET = EVA_CORE | SEPARATORS | HIGH_ASCII_CHARS | VARIANT_CHARS
```

This charset is LOCKED for all v0.2.x releases.

---

## Changelog

- **v0.2.1** (2026-01-18): Initial charset definition based on empirical analysis of ZL3b-n.txt
  - Added 'j' to EVA_CORE (14 occurrences)
  - Added apostrophe (') to VARIANT_CHARS (27 occurrences)
  - Added handling for uppercase 'I' (1 occurrence, normalized to lowercase)
