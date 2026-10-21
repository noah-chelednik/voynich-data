# Stability policy

What a user of VCAT's datasets can rely on from one release to the next (roadmap item 2.2). It binds every release from
1.0.0 on. The suite checks the parts of it that can be checked mechanically (`tests/test_stability.py`).

## Versions

Every release has one version, `MAJOR.MINOR.PATCH`, stated alike in `pyproject.toml`, `vcat.__version__`, `CITATION.cff`,
the `voynich-eva` card and the metadata build report (`tests/test_paperwork.py`). The version says what kind of change a release carries for the data:

| part | goes up when a release... | a user's code or analysis written for the previous release... |
|---|---|---|
| MAJOR | removes or renames a field, changes a field's type or meaning, retires an identifier, or switches a field to another profile (`text_clean` from `analysis-v1` to `analysis-v2`) | may need changes; the CHANGELOG gives migration notes |
| MINOR | adds fields, rows (loci a source gained), datasets or profiles, or announces a deprecation | keeps working |
| PATCH | corrects data that was wrong against its own source and documentation, with nothing else changed (each correction listed in `ERRATA.md`) | keeps working, on corrected values |

A release before 1.0.0 (the last was 0.2.3) promised none of this; the corrections it needed are in `ERRATA.md`.

## Identifiers

These identifiers are permanent, in every release, MAJOR ones included. Once a release publishes one, it always names the
same thing, and it is never given to anything else:

| identifier | names | pattern (from the schemas) |
|---|---|---|
| `page_id` | a page of the manuscript, by its IVTFF page name | `^(f\d+[rv]\d*\|fRos)$` |
| `line_id` | one locus of a page: `{page_id}:{line_number}`, the locus number the source gives | `^(f\d+[rv]\d*\|fRos):\d+$` |
| `folio_id`, `quire_id` | a folio and a quire of the metadata datasets | as the metadata builder writes them (`f1`, `qA`) |
| a profile id (`raw-v1`, `diplomatic-v1`, `analysis-v1`, `no-uncertain-spaces-v1`) | one fixed set of normalization rules | `<name>-v<n>` |

- **Never reused, never silently changed.** If an upstream correction removes a locus or renumbers it, the old identifier is
  retired: it is listed in `ERRATA.md` with the release that retired it, and no later row ever carries it again.
- **A profile's rules never change.** Different rules are a new profile with a new id (`analysis-v2`), added in a MINOR
  release; the published rule table of every profile is pinned by `tests/test_profiles.py`.
- `line_number` is the source's numbering and may have gaps; `line_index` is a row's position on its page and is not an
  identifier.

## Deprecations

A field, dataset, profile or configuration is removed only after a release that announces it:

1. The announcing release (MINOR) marks it deprecated: the schema property gets `"deprecated": true` and a description
   naming its replacement, the CHANGELOG lists it, and the table below records it.
2. The next MAJOR release may remove it; never earlier.

| deprecated | announced in | replacement | removable from |
|---|---|---|---|

(No deprecation is in force.)

## Corrections

Data that is wrong against its source is corrected, and every correction is logged in `ERRATA.md` with what was wrong,
which releases carried it, and how to tell. Transcription errors (a reading the source itself gets wrong) are not corrected
here: VCAT distributes the transliterations faithfully, so they are reported upstream to the transliteration's maintainer
(the issue template "Transcription error" explains how), and a corrected upstream file reaches VCAT as a new source version
(`data_sources/sources.yaml`).
