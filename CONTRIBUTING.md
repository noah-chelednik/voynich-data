# Contributing to voynich-data

Thanks for your interest! This project aims to be boring in the best way:
reproducible builds, validated data, documented decisions.

## Getting set up

```bash
git clone https://github.com/noah-chelednik/voynich-data.git
cd voynich-data
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
vcat-verify           # the cached sources match data_sources/sources.yaml
```

## Before submitting a PR

```bash
ruff check .          # lint
black --check .       # formatting
mypy vcat parsers builders validators hf   # types
pytest                # the suite, reviewer proofs included (no path; no skips or xfails)
```

All four must pass; CI runs the same checks. The suite runs them too (`tests/test_ci_checks.py`).
`.pre-commit-config.yaml` holds the same checks for `pre-commit install`.

## Ground rules

- **Data changes need provenance.** Any change to dataset content must trace
  back to a source file in `data_sources/sources.yaml` (with checksum) or a
  documented decision in `docs/decisions.md`.
- **Text processing is centralized.** Every reading of the source text is a
  named profile in `vcat/profiles.py`; `text_clean` is `analysis-v1`. Do not
  duplicate the rules: builders and validators use the same profiles.
- **The source text is kept exactly** (`text_raw`; the faithfulness contract in
  `docs/data_model.md`). A change to a profile's rules is a new profile name and
  a decision-log entry.
- **Methodology changes get documented.** If you change how something is
  computed (e.g., the mismatch categories), update the relevant doc and
  dataset card in the same PR.

## Reporting issues

Use the issue templates. A **data bug** (VCAT's data differs from its source or its documentation) is
corrected and logged in [ERRATA.md](ERRATA.md); a **transcription error** (the source itself reads wrongly) is
reported upstream, never corrected here. What VCAT keeps stable is in [STABILITY.md](STABILITY.md).

- Data errors: include the `line_id` (e.g., `f1r:5`) and the source you
  checked against.
- Licensing/attribution concerns: see
  [docs/SOURCES_LICENSE.md](docs/SOURCES_LICENSE.md); these are acted on
  promptly.
