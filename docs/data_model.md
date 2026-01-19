# VCAT Data Model

This document describes the data model used in the Voynich Computational Analysis Toolkit (VCAT). It covers identifier formats, normalization rules, text representation, and entity relationships.

## Overview

The VCAT data model is designed around these principles:

1. **Source-Faithful**: We preserve the structure and numbering of source transcriptions
2. **Explicit Uncertainty**: Ambiguous or disputed information is explicitly marked
3. **Joinable**: All entities can be linked through consistent identifiers
4. **Pre-1.0 Provisional**: Schema may evolve; changes are documented

## Identifier Formats

### Page ID (`page_id`)

The canonical identifier for a manuscript page (folio side).

**Format**: `f{folio_number}{side}{panel?}`

| Component      | Description                                  | Values                        |
|----------------|----------------------------------------------|-------------------------------|
| `f`            | Prefix (always present)                      | Literal "f"                   |
| `folio_number` | Numeric folio, no leading zeros              | 1-116                         |
| `side`         | Recto (front) or verso (back)                | `r` or `v`                    |
| `panel`        | Optional panel number for foldout pages      | Integer (1-6)                 |

**Examples**:
- `f1r` — Folio 1 recto
- `f1v` — Folio 1 verso
- `f85v3` — Folio 85 verso, panel 3 (foldout)
- `f116v` — Final folio verso

**Normalization Rules**:
- Remove leading zeros: `f01r` → `f1r`
- Remove "fol." prefix: `fol. 1r` → `f1r`
- Standardize panel notation: `f85v-1` → `f85v1`
- Always lowercase: `F1R` → `f1r`

### Line ID (`line_id`)

Unique identifier for a text line within the manuscript.

**Format**: `{page_id}:{line_number}`

| Component     | Description                               |
|---------------|-------------------------------------------|
| `page_id`     | Canonical page identifier                 |
| `:`           | Separator                                 |
| `line_number` | 1-indexed line number within the page     |

**Examples**:
- `f1r:1` — First line of folio 1 recto
- `f1r:15` — Fifteenth line of folio 1 recto
- `f85v3:7` — Seventh line of panel 3, folio 85 verso

### Folio ID (`folio_id`)

Identifier for a physical leaf (both sides).

**Format**: `f{folio_number}`

**Examples**:
- `f1` — First folio (includes f1r and f1v)
- `f85` — Folio 85 (includes foldout panels)

### Quire ID (`quire_id`)

Identifier for a gathering of folios.

**Format**: `q{quire_number}`

**Examples**:
- `q1` — First quire
- `qA` — Quire A (some sources use letters)

## Line Numbering Policy

We follow a **source-faithful numbering** policy:

1. **Preserve Source Numbers**: Each dataset preserves its source's original line numbers
2. **Composite IDs**: The `line_id` field combines page and line number
3. **No Renumbering**: We do not "correct" or standardize source numbering
4. **Track Mismatches**: When sources disagree, differences are recorded in the mismatch index

### Handling Discrepancies

| Situation                           | Handling                                    |
|-------------------------------------|---------------------------------------------|
| Same line count, same content       | `status: "ok"`                              |
| Same line count, different content  | `status: "content_mismatch"`                |
| Different line counts               | `status: "line_count_mismatch"`             |
| Line only in source A               | `status: "missing_in_B"`                    |
| Reflow (different wrapping)         | `status: "reflow"`                          |

## Text Representation

### Raw Text (`text`)

The original transcription text exactly as it appears in the source, including all markup:

```
fachys.ykal{comment}.ar[a:b].ataiin<->shol
```

**May contain**:
- Word separators (`.`, `,`)
- Inline comments (`{like this}`)
- Alternative readings (`[a:b]`)
- IVTFF markers (`<->`, `<%>`, `<$>`)
- Uncertainty markers (`?`, `!`, `*`)
- High-ASCII codes (`@123;`)

### Clean Text (`text_clean`)

Processed text with markup removed, suitable for analysis:

```
fachys ykal ar a ataiin shol
```

**Processing applied**:
1. Remove inline comments `{...}`
2. Keep first alternative `[a:b]` → `a`
3. Remove IVTFF markers `<...>`
4. Remove high-ASCII codes `@NNN;`
5. Normalize separators to spaces
6. Collapse multiple spaces

## IVTFF Markup Reference

IVTFF (Intermediate Voynich Transliteration File Format) is the standard format for Voynich transcriptions.

### Format Header

```
#=IVTFF Eva- 2.0 M 5
```

| Component   | Meaning                                      |
|-------------|----------------------------------------------|
| `#=IVTFF`   | Format identifier                            |
| `Eva-`      | Alphabet (EVA with rare characters)          |
| `2.0`       | Format version                               |
| `M`         | Mode (M=mixed transcribers)                  |
| `5`         | Number of interlinear slots                  |

### Page Header

```
<f1r>      <! $Q=A $P=A $L=A $H=1 $I=H>
```

| Variable | Meaning           | Values                           |
|----------|-------------------|----------------------------------|
| `$Q`     | Quire             | A-Z, numeric                     |
| `$P`     | Position in quire | A-Z, numeric                     |
| `$F`     | Folio             | Folio identifier                 |
| `$B`     | Bifolio           | Numeric                          |
| `$I`     | Illustration type | H/A/C/B/P/S/T/Z                  |
| `$L`     | Currier language  | A or B                           |
| `$H`     | Hand/scribe       | 1, 2, etc.                       |
| `$C`     | Cluster           | Numeric                          |
| `$X`     | Extraneous text   | V, etc.                          |

### Line/Locus Format

```
<f1r.1,@P0>       fachys.ykal.ar.ataiin
```

| Component | Meaning                                      |
|-----------|----------------------------------------------|
| `f1r`     | Page ID                                      |
| `.1`      | Locus number                                 |
| `,@`      | Position: `@`=new unit, `+`=continue, `=`=end, `*`=new para |
| `P`       | Type: `P`=paragraph, `L`=label, `C`=circle, `R`=radius |
| `0`       | Subtype (optional)                           |

### Inline Markup

| Markup           | Meaning                                      |
|------------------|----------------------------------------------|
| `.`              | Word separator                               |
| `,`              | Possible word boundary                       |
| `{comment}`      | Inline comment (ignored in analysis)         |
| `[a:b]`          | Alternative readings (a or b)                |
| `<->`            | Line continuation                            |
| `<%>`            | Paragraph start                              |
| `<$>`            | End marker                                   |
| `<!comment>`     | Processing instruction                       |
| `@NNN;`          | High-ASCII character code                    |
| `?`              | Uncertain reading                            |
| `!` / `*`        | Illegible/editorial insertion                |

## Character Sets

See [eva_alphabet.md](eva_alphabet.md) for the complete EVA character specification.

**Quick Reference**:
- Basic glyphs: `acdehiklmnopqrsty` (17 characters)
- Rare glyphs: `fgxjvbuz` (8 characters)
- Compound glyphs: `ch`, `sh`, `cth`, `ckh`, `cph`, `cfh`

## Metadata Fields

### Page-Level Metadata

| Field              | Type           | Description                                |
|--------------------|----------------|--------------------------------------------|
| `page_id`          | string         | Canonical page identifier                  |
| `folio_id`         | string         | Parent folio                               |
| `side`             | enum           | "recto" or "verso"                         |
| `quire`            | string?        | Quire identifier                           |
| `section`          | object         | Manuscript section with attribution        |
| `currier_language` | string?        | "A" or "B"                                 |
| `hand`             | string?        | Scribe identifier                          |
| `illustration_type`| string?        | Type code (H/A/C/B/P/S/T/Z)                |
| `line_count`       | integer?       | Number of text lines                       |

### Uncertainty Representation

For fields where scholarly consensus is lacking, we use structured uncertainty:

```json
{
  "section": {
    "value": "herbal",
    "attribution": "zandbergen_2020",
    "confidence": "high",
    "disputed": false,
    "alternatives": []
  }
}
```

| Field         | Description                                  |
|---------------|----------------------------------------------|
| `value`       | The assigned value                           |
| `attribution` | Source of this assignment                    |
| `confidence`  | "high", "medium", or "low"                   |
| `disputed`    | Whether other sources disagree               |
| `alternatives`| Other proposed values                        |

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                           MANUSCRIPT                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                          QUIRE                                │  │
│  │  quire_id: q1                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │                      FOLIO                               │ │  │
│  │  │  folio_id: f1                                            │ │  │
│  │  │  ┌──────────────────────────────────────────────────┐   │ │  │
│  │  │  │                   PAGE                            │   │ │  │
│  │  │  │  page_id: f1r (recto)                             │   │ │  │
│  │  │  │  ┌─────────────────────────────────────────────┐  │   │ │  │
│  │  │  │  │                 LINE                         │  │   │ │  │
│  │  │  │  │  line_id: f1r:1                              │  │   │ │  │
│  │  │  │  │  text: "fachys.ykal.ar.ataiin..."            │  │   │ │  │
│  │  │  │  └─────────────────────────────────────────────┘  │   │ │  │
│  │  │  │  ┌─────────────────────────────────────────────┐  │   │ │  │
│  │  │  │  │  line_id: f1r:2                              │  │   │ │  │
│  │  │  │  └─────────────────────────────────────────────┘  │   │ │  │
│  │  │  └──────────────────────────────────────────────────┘   │ │  │
│  │  │  ┌──────────────────────────────────────────────────┐   │ │  │
│  │  │  │  page_id: f1v (verso)                             │   │ │  │
│  │  │  │    ...                                            │   │ │  │
│  │  │  └──────────────────────────────────────────────────┘   │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key relationships**:
- A **quire** contains multiple **folios**
- A **folio** has two **pages** (recto and verso)
- A **page** contains multiple **lines**
- All entities join on their respective ID fields

## Foldout Page Handling

Folios 85 and 86 are foldout pages with multiple panels.

### Policy

1. **Panel-level page IDs**: Each panel gets its own `page_id` (e.g., `f85v1`, `f85v2`)
2. **Left-to-right numbering**: Panels numbered from left to right when unfolded
3. **Independent line numbering**: Each panel has lines starting at 1
4. **Metadata linkage**: `is_foldout_panel: true` with `panel_number` and `total_panels`

### Foldout Structure

| Folio | Side  | Panels | Page IDs                                    |
|-------|-------|--------|---------------------------------------------|
| f85   | verso | 6      | f85v1, f85v2, f85v3, f85v4, f85v5, f85v6    |
| f86   | verso | 4      | f86v1, f86v2, f86v3, f86v4                  |

## Missing Folios

The following folios are known to be missing from the manuscript:

| Folio Range | Notes                                       |
|-------------|---------------------------------------------|
| f12         | Missing                                     |
| f59-64      | Missing (6 folios)                          |
| f74         | Missing                                     |
| f91-96      | Missing (6 folios)                          |
| f109        | Missing                                     |
| f110        | Missing                                     |

**Note**: Folio numbering continues through gaps. f65 follows f58.

## Manuscript Sections

| Section        | Approximate Folios | Illustration Type | Currier Language |
|----------------|--------------------|--------------------|------------------|
| Herbal A       | f1-f25             | H (plant)          | A                |
| Herbal B       | f26-f66            | H (plant)          | B                |
| Astronomical   | f67-f73            | A/S/Z (zodiac)     | A/B              |
| Biological     | f75-f84            | B (figures)        | B                |
| Cosmological   | f85-f86            | C (foldouts)       | B                |
| Pharmaceutical | f87-f102           | P (plant parts)    | A                |
| Recipes        | f103-f116          | T (text only)      | A                |

**Note**: Section boundaries are approximate and subject to scholarly debate.

## Version History

| Version | Date       | Changes                                     |
|---------|------------|---------------------------------------------|
| 0.1.0   | 2026-01-17 | Initial data model specification            |

---

*This document is part of the VCAT project. Schema is pre-1.0 and may change.*
