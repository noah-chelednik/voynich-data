#!/usr/bin/env python3
"""
Phase 1 Output Validator
========================

Validates that shipped output artifacts match the current code and schema.
This prevents shipping stale outputs that don't reflect code changes.

Run this before any release to ensure consistency.

Usage:
    python -m validators.validate_phase1_outputs
    python -m validators.validate_phase1_outputs --output-dir ./output

Checks performed:
    1. Field presence: All required fields exist (including line_index, has_high_ascii)
    2. line_index correctness: Sequential 1..n per page with no gaps
    3. @NNN; preservation: Lines with only @NNN; in raw have non-empty text_clean
    4. has_high_ascii consistency
    5. Build report: required fields; no reported errors; source verified; non-negative
       totals; the source file's bytes hash to the recorded source_hash
    6. Schema validation: every row conforms to schemas/transcription_lines.schema.json
    7. Rows agree with the build report (nonempty; total_lines; pages_with_lines)
    8. Loss accounting: every source locus is a row or reported, recomputed from the
       source file (vcat.loss_accounting) and checked against the report's own accounting
    9. text_clean is the current cleaning function applied to text
   10. The structured layer (item 1.2): each row's text_raw, locus_type and source_line are
       the source file's, its markup fields are the markup of text_raw, and its flags and
       counts follow from them
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from parsers import page_order_key
from parsers.ivtff_markup import parse_markup
from validators.schema import validate_mismatch_index, validate_transcription_lines
from vcat import validate_eva_text
from vcat.iiif import CANVASES_JSON as IIIF_CANVASES
from vcat.loss_accounting import account, census_source, resolve_source
from vcat.profiles import PROFILES
from vcat.sources import pinned_sha256
from vcat.text_processing import clean_text_for_analysis, compute_flags

#: Row fields that hold the markup of text_raw (parsers.ivtff_markup.Markup.fields).
MARKUP_FIELDS = [
    "alternates",
    "ligatures",
    "uncertain_spaces",
    "illegible",
    "high_ascii",
    "comments",
    "drawing_breaks",
    "markers",
]

#: A locus identifier line: page, number, code (with an optional transcriber), the separating
#: whitespace and the text (IVTFF 2.0 section 6.4), read here without the parser.
#: How many errors of one kind are listed before the rest are summarized (a display limit).
ERRORS_SHOWN = 5

#: The row's line_type for each generic locus type (IVTFF 2.0 Table 9), written here from the
#: specification rather than taken from the builder, so a builder error cannot pass (AV3 F2, B-044).
LINE_TYPES = {"P": "paragraph", "L": "label", "C": "circle", "R": "radius"}

_LOCUS_LINE = re.compile(r"^<([^<>.,\s]+)\.(\d+),([^<>;]*)(?:;[^<>]*)?>([ \t]*)(.*)$")

#: Loss-accounting fields every build report must carry (builders.build_eva_lines.BuildReport).
ACCOUNTING_FIELDS = [
    "source_loci",
    "loci_emitted",
    "loci_reported",
    "reported_loci",
    "unaccounted_loci",
    "unexpected_loci",
    "unaccounted_pages",
]

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load records from JSONL file."""
    records = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON at line {line_num}: {e}") from e
    return records


def check_required_fields(records: list[dict], required: list[str]) -> list[str]:
    """Check that all required fields exist on every record."""
    errors = []
    for i, rec in enumerate(records):
        missing = [f for f in required if f not in rec]
        if missing:
            errors.append(f"Record {i} ({rec.get('line_id', '?')}): missing fields {missing}")
    return errors


def check_line_index_sequential(records: list[dict]) -> list[str]:
    """Check that line_index is sequential 1..n per page with no gaps."""
    errors = []

    # Group by page_id
    pages: dict[str, list[int]] = {}
    for rec in records:
        page_id = rec.get("page_id")
        line_index = rec.get("line_index")
        if page_id and line_index is not None:
            if page_id not in pages:
                pages[page_id] = []
            pages[page_id].append(line_index)

    # Check each page
    for page_id, indices in pages.items():
        sorted_indices = sorted(indices)
        expected = list(range(1, len(indices) + 1))
        if sorted_indices != expected:
            errors.append(
                f"Page {page_id}: line_index not sequential. Got {sorted_indices[:5]}... expected {expected[:5]}..."
            )

    return errors


def check_high_ascii_preservation(records: list[dict]) -> list[str]:
    """Check that @NNN; codes are preserved in text_clean (not stripped to empty)."""
    errors = []
    at_code_pattern = re.compile(r"^@\d+;$")

    for rec in records:
        raw = rec.get("text", "")
        clean = rec.get("text_clean", "")

        # If raw is ONLY an @NNN; code, clean should not be empty
        if at_code_pattern.match(raw.strip()):
            if not clean.strip():
                errors.append(
                    f"{rec.get('line_id', '?')}: raw='{raw}' but text_clean is empty (data loss)"
                )

    return errors


def check_has_high_ascii_field(records: list[dict]) -> list[str]:
    """Check that has_high_ascii field exists and is consistent with content."""
    errors = []

    for rec in records:
        if "has_high_ascii" not in rec:
            errors.append(f"{rec.get('line_id', '?')}: missing has_high_ascii field")
            continue

        # A code in the transliterated text, comments excluded (DECISIONS Q25)
        raw = rec.get("text_raw", rec.get("text", ""))
        has_code = bool(parse_markup(str(raw)).fields()["high_ascii"])

        if has_code and not rec["has_high_ascii"]:
            errors.append(f"{rec.get('line_id', '?')}: contains @NNN; but has_high_ascii=False")
        elif not has_code and rec["has_high_ascii"]:
            errors.append(f"{rec.get('line_id', '?')}: no @NNN; but has_high_ascii=True")

    return errors


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load_build_report(report_path: Path) -> dict[str, Any]:
    with open(report_path) as f:
        report: dict[str, Any] = json.load(f)
    return report


def check_build_report(report_path: Path) -> list[str]:
    """Check that the build report is complete, reports success, and names its real source."""
    errors = []

    if not report_path.exists():
        return [f"Build report not found: {report_path}"]

    report = load_build_report(report_path)

    required_fields = [
        "source_file",
        "source_hash",
        "build_date",
        "format_version",
        "format_options",
        "text_clean_policy",
        "total_pages",
        "total_lines",
        "total_words",
        "total_characters",
        "lines_with_high_ascii",
        "lines_by_type",
    ]

    missing = [f for f in required_fields if f not in report]
    if missing:
        errors.append(f"Build report missing fields: {missing}")

    # Check text_clean_policy is set
    if report.get("text_clean_policy") is None:
        errors.append("Build report: text_clean_policy is None (it names a profile, vcat.profiles)")

    if report.get("errors"):
        errors.append(f"Build report records build errors: {report['errors'][:5]}")
    if report.get("source_verified") is not True:
        errors.append(f"Build report: source_verified is {report.get('source_verified')!r}")
    for name in (
        "total_lines",
        "total_pages",
        "total_words",
        "total_characters",
        "lines_with_high_ascii",
    ):
        if name in report and not _is_count(report[name]):
            errors.append(f"Build report: {name} is not a non-negative integer: {report[name]!r}")

    if "source_file" in report:
        source = resolve_source(report["source_file"])
        if source is None:
            errors.append(f"Build report: source file not found: {report['source_file']!r}")
        elif hashlib.sha256(source.read_bytes()).hexdigest() != report.get("source_hash"):
            errors.append(f"Build report: source_hash does not match the bytes of {source}")

    return errors


def check_rows_against_report(records: list[dict], report: dict[str, Any]) -> list[str]:
    """Rows exist and agree with the totals the build report records."""
    errors = []
    if not records:
        errors.append("No records: the dataset is empty")
    if report.get("total_lines") != len(records):
        errors.append(
            f"{len(records)} records, but the build report total_lines is "
            f"{report.get('total_lines')!r}"
        )
    stale = [
        str(r.get("line_id"))
        for r in records
        if r.get("line_id") != f"{r.get('page_id')}:{r.get('line_number')}"
    ]
    if stale:
        errors.append(
            f"{len(stale)} rows whose line_id is not page_id:line_number, first {stale[:5]}"
        )
    ids = [r.get("line_id") for r in records]
    if len(set(ids)) != len(ids):
        repeated = sorted({str(i) for i in ids if ids.count(i) > 1})
        errors.append(f"{len(ids) - len(set(ids))} duplicate line_id rows, ids {repeated[:5]}")
    pages = {str(r.get("page_id")) for r in records}
    without = report.get("page_ids_without_lines", [])
    if len(set(without)) != len(without):
        errors.append(f"Build report page_ids_without_lines repeats a page: {without}")
    if "pages_without_lines" in report and report["pages_without_lines"] != len(without):
        errors.append(
            f"Build report pages_without_lines is {report['pages_without_lines']!r} but it lists "
            f"{len(without)} page_ids_without_lines"
        )
    if pages & set(without):
        errors.append(f"Pages listed without lines carry records: {sorted(pages & set(without))}")
    parsed = len(pages) + len(without)
    for name in ("total_pages", "total_pages_in_source"):
        if name in report and report[name] != parsed:
            errors.append(
                f"Build report {name} is {report[name]!r}, but pages with and without lines "
                f"number {parsed}"
            )
    if "pages_with_lines" in report and report["pages_with_lines"] != len(pages):
        errors.append(
            f"{len(pages)} pages carry records, but the build report pages_with_lines "
            f"is {report['pages_with_lines']!r}"
        )
    # The summary statistics are the rows' (AV2 F2, B-024).
    totals = {
        "total_words": sum(_number(r.get("word_count")) for r in records),
        "total_characters": sum(_number(r.get("char_count")) for r in records),
        "lines_with_high_ascii": sum(1 for r in records if r.get("has_high_ascii") is True),
    }
    for name, value in totals.items():
        if report.get(name) != value:
            errors.append(f"Build report {name} is {report.get(name)!r}, the rows give {value}")
    by_type: dict[str, int] = {}
    for r in records:
        by_type[str(r.get("line_type"))] = by_type.get(str(r.get("line_type")), 0) + 1
    # Required, a mapping of non-negative integers, and the rows' (review 09e1ca3c finding 2)
    recorded = report.get("lines_by_type")
    if not isinstance(recorded, dict) or not all(_is_count(v) for v in recorded.values()):
        errors.append(
            f"Build report lines_by_type is not a mapping of non-negative integers: {recorded!r}"
        )
    elif recorded != by_type:
        errors.append(
            f"Build report lines_by_type is {report['lines_by_type']!r}, the rows give {by_type}"
        )
    return errors


def _number(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _source_lines(source: Path) -> list[str | None]:
    """The source's lines, each with its terminator, each decoded strictly on its own; a line
    that is not UTF-8 is None (the parser reported it, and no row can name it; reach 5bb6a8d4
    gap 3)."""
    lines: list[str | None] = []
    for match in re.finditer(rb"[^\r\n]*(?:\r\n|\n|\r|$)", source.read_bytes()):
        if not match.group(0):
            continue
        try:
            lines.append(match.group(0).decode("utf-8"))
        except UnicodeDecodeError:
            lines.append(None)
    return lines


def _expected_text_raw(lines: list[str | None], index: int, first: str) -> str:
    """text_raw from the source: the first line's text, then, while a line ends with '/', the
    line terminator and the continuation line (DECISIONS Q24)."""
    text_raw = first
    while text_raw.rstrip(" \t").endswith("/") and index + 1 < len(lines):
        current, following_line = lines[index], lines[index + 1]
        if current is None or following_line is None:
            break
        ending = re.search(r"(\r\n|\n|\r)$", current)
        index += 1
        following = following_line.rstrip("\r\n")
        if not following.startswith("/"):
            break
        text_raw += (ending.group(1) if ending else "") + following
    return text_raw


def check_structured_layer(records: list[dict], report: dict[str, Any]) -> list[str]:
    """Each row's raw and structured layer is the source's (roadmap item 1.2, DECISIONS Q24, Q25).

    Read from the source file without the parser: the line at ``source_line`` is the locus
    identifier of the row's ``line_id``; ``locus_type`` is its code without the transcriber;
    ``position`` is the code's locator and ``line_type`` names its generic type (B-044);
    ``text_raw`` is its text, exactly. Then ``text`` and the markup fields are those of
    ``text_raw``, which must hold only markup IVTFF 2.0 defines; ``has_alternatives`` and
    ``has_high_ascii`` say whether those fields are empty (AV2 F3, B-025); ``char_count`` and
    ``word_count`` are those of ``text_clean``.
    """
    errors: list[str] = []
    source = resolve_source(report.get("source_file", ""))
    if source is None:
        return ["Structured layer: the source file cannot be found to read the rows against"]
    lines = _source_lines(source)
    for r in records:
        line_id = str(r.get("line_id", "?"))
        number = r.get("source_line")
        if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= len(lines):
            errors.append(f"{line_id}: source_line {number!r} is not a line of {source.name}")
            continue
        line = lines[number - 1]
        if line is None:
            errors.append(f"{line_id}: line {number} of {source.name} is not UTF-8")
            continue
        match = _LOCUS_LINE.match(line.rstrip("\r\n"))
        if not match or f"{match.group(1)}:{int(match.group(2))}" != line_id:
            errors.append(f"{line_id}: line {number} of {source.name} is not this locus")
            continue
        if r.get("locus_type") != match.group(3):
            errors.append(
                f"{line_id}: locus_type {r.get('locus_type')!r}, the source has {match.group(3)!r}"
            )
        # The locator and the generic type of the code are the row's position and line_type
        # (AV3 F2, B-044).
        code = match.group(3)
        if r.get("position") != code[:1]:
            errors.append(f"{line_id}: position {r.get('position')!r}, the source has {code[:1]!r}")
        if r.get("line_type") != LINE_TYPES.get(code[1:2]):
            errors.append(
                f"{line_id}: line_type {r.get('line_type')!r}, the source's locus type is "
                f"{code[1:2]!r} ({LINE_TYPES.get(code[1:2])!r})"
            )
        expected_raw = _expected_text_raw(lines, number - 1, match.group(5))
        if r.get("text_raw") != expected_raw:
            errors.append(f"{line_id}: text_raw is not the source text {expected_raw!r}")
            continue
        markup = parse_markup(expected_raw)
        if markup.problems:
            errors.append(f"{line_id}: text_raw holds undefined markup: {markup.problems[:2]}")
        if r.get("text") != markup.text:
            errors.append(f"{line_id}: text is not the text of text_raw")
        fields = markup.fields()
        wrong = [name for name in MARKUP_FIELDS if r.get(name) != fields[name]]
        if wrong:
            errors.append(f"{line_id}: markup fields {wrong} are not the markup of text_raw")
        if r.get("has_alternatives") is not bool(fields["alternates"]):
            errors.append(f"{line_id}: has_alternatives does not say whether it has alternates")
        if r.get("has_high_ascii") is not bool(fields["high_ascii"]):
            errors.append(f"{line_id}: has_high_ascii does not say whether it has high-ASCII codes")
        counted = validate_eva_text(str(r.get("text_clean", "")))
        if (r.get("char_count"), r.get("word_count")) != (counted.char_count, counted.word_count):
            errors.append(f"{line_id}: char_count or word_count is not that of text_clean")
    return errors


#: The file header, read here without the parser: alphabet, version, the rest (IVTFF 2.0 Table 4).
_FILE_HEADER = re.compile(r"^#=IVTFF\s+(\S+)(?:\s+(\S+))?\s*(.*)$")
#: A page header line: the page name and what follows it.
_PAGE_HEADER = re.compile(r"^<([^<>.,\s]+)>(.*)$")
#: A row's source_version: the first hex digits of the source's SHA-256 (the dataset's convention).
SOURCE_VERSION_DIGITS = 12
#: The row field each page variable fills (the builder's page metadata).
PAGE_FIELDS = {"Q": "quire", "H": "hand", "I": "illustration_type", "L": "currier_language"}
#: VCAT's section name for each `$I` illustration code, as `docs/data_model.md` lists the names (AV9 F2); a row's
#: `section` is the name of its page's code. Kept here, not imported from the builder, so the check is independent.
SECTION_OF_ILLUSTRATION = {
    "H": "herbal",
    "A": "astronomical",
    "C": "cosmological",
    "B": "biological",
    "P": "pharmaceutical",
    "S": "stars",
    "T": "text_only",
    "Z": "zodiac",
}
#: Table 6 values of the variables the dataset constrains (DECISIONS Q36).
_TABLE_6 = {"B": "123456", "L": "AB"}


def _page_settings(header_text: str) -> dict[str, str]:
    """The page variables a page header sets, by the rule of DECISIONS Q36, read without the
    parser: the settings ``$X=y`` of the leading ``<! ... >`` comment; a variable set more than once,
    or a ``$B`` or ``$L`` outside Table 6, or ``@`` (set by text tags), gives no value."""
    match = re.match(r"<!([^<>]*)>", header_text.lstrip(" \t"))
    if not match:
        return {}
    counts: dict[str, int] = {}
    values: dict[str, str] = {}
    for item in match.group(1).split():
        setting = re.fullmatch(r"\$([A-Z])=([^\s<>$])", item)
        if setting:
            counts[setting.group(1)] = counts.get(setting.group(1), 0) + 1
            values[setting.group(1)] = setting.group(2)
    return {
        name: value
        for name, value in values.items()
        # '@' says text tags set the variable on the page, so it has no value before the first tag (IVTFF 2.0 section
        # 6.8, conventions 2 and 3; S13, reach 8e09e8e7 gap 2)
        if counts[name] == 1 and value != "@" and (name not in _TABLE_6 or value in _TABLE_6[name])
    }


def check_against_source(records: list[dict], report: dict[str, Any]) -> list[str]:
    """What the rows and the report say about the source is what the source says (B-045, B-046,
    B-052), checked by both validators.

    Read from the source file without the parser: the report's ``alphabet``, ``format_version``
    and ``format_options`` are the file header's; every row's ``source_version`` is the start of
    the report's ``source_hash``; every row's ``quire``, ``hand``, ``illustration_type`` and
    ``currier_language`` are its page header's variables. ``text_clean_policy`` names a
    normalization profile (``vcat.profiles``) and every ``text_clean`` is that profile applied to
    ``text_raw``. The flags ``has_uncertain`` and ``has_illegible`` are those of ``text``, and the
    rows follow the ordering contract (page order, then ``line_index``). Every row names one and the same ``source``
    (AV7 F4).
    """
    errors: list[str] = []
    named = sorted({str(r.get("source")) for r in records})
    if len(named) > 1:
        errors.append(f"rows name more than one source: {named[:5]}")
    policy = report.get("text_clean_policy")
    profile = PROFILES.get(policy) if isinstance(policy, str) else None
    if profile is None:
        errors.append(
            f"Build report text_clean_policy {policy!r} is not a profile; profiles: {sorted(PROFILES)}"
        )
    source_hash = report.get("source_hash")
    source = resolve_source(report.get("source_file", ""))
    if source is None:
        return errors + ["Source checks: the source file cannot be found"]
    lines = _source_lines(source)
    first = (lines[0] or "").rstrip("\r\n") if lines else ""
    header = _FILE_HEADER.match(first)
    expected = (
        (header.group(1), header.group(2), header.group(3).strip() or None)
        if header
        else (None, None, None)
    )
    for name, value in zip(("alphabet", "format_version", "format_options"), expected, strict=True):
        if report.get(name) != value:
            errors.append(
                f"Build report {name} is {report.get(name)!r}, the source header has {value!r}"
            )
    settings: dict[str, dict[str, str]] = {}
    for line in lines:
        if line is not None and (page := _PAGE_HEADER.match(line.rstrip("\r\n"))):
            if "." not in page.group(1):
                settings[page.group(1)] = _page_settings(page.group(2))
    previous: tuple | None = None
    # Within a page, rows follow the source (source_line increasing) and line_index numbers them 1 to n in that order, so a
    # reordering that renumbers line_index to match is still caught (AV5 F2, B-055).
    on_page: dict[str, tuple[int, int]] = {}
    for r in records:
        line_id = str(r.get("line_id", "?"))
        expected_version = (
            source_hash[:SOURCE_VERSION_DIGITS] if isinstance(source_hash, str) else None
        )
        if r.get("source_version") != expected_version:
            errors.append(
                f"{line_id}: source_version {r.get('source_version')!r} is not the source hash's "
                f"first digits {expected_version!r}"
            )
        page_settings = settings.get(str(r.get("page_id")), {})
        for variable, field in PAGE_FIELDS.items():
            if r.get(field) != page_settings.get(variable):
                errors.append(
                    f"{line_id}: {field} {r.get(field)!r}, the page header has "
                    f"{page_settings.get(variable)!r}"
                )
        code = page_settings.get("I")
        if code in SECTION_OF_ILLUSTRATION and r.get("section") != SECTION_OF_ILLUSTRATION[code]:
            errors.append(
                f"{line_id}: section {r.get('section')!r} is not the name of illustration type {code!r}, "
                f"{SECTION_OF_ILLUSTRATION[code]!r}"
            )
        if profile is not None and r.get("text_clean") != profile.apply(str(r.get("text_raw", ""))):
            errors.append(f"{line_id}: text_clean is not {profile.id} of text_raw")
        flags = compute_flags(str(r.get("text", "")))
        if (r.get("has_uncertain"), r.get("has_illegible")) != flags[:2]:
            errors.append(f"{line_id}: has_uncertain or has_illegible is not that of text")
        key = (*page_order_key(str(r.get("page_id", ""))), r.get("line_index", 0))
        if previous is not None and key < previous:
            errors.append(f"{line_id}: out of order (page order, then line_index)")
        previous = key
        row_page = str(r.get("page_id"))
        count, last_line = on_page.get(row_page, (0, 0))
        number = r.get("source_line")
        if r.get("line_index") != count + 1:
            errors.append(
                f"{line_id}: line_index {r.get('line_index')!r} is not its place on the page, {count + 1}"
            )
        if isinstance(number, int) and number <= last_line:
            errors.append(
                f"{line_id}: source_line {number} does not follow the page's previous row (line {last_line})"
            )
        on_page[row_page] = (count + 1, number if isinstance(number, int) else last_line)
    errors.extend(_report_page_summaries(records, report, settings, source))
    errors.extend(_report_warnings(records, report, source))
    return errors


def _report_page_summaries(
    records: list[dict], report: dict[str, Any], settings: dict[str, dict[str, str]], source: Path
) -> list[str]:
    """The build report's page summaries are the source's (AV9 F1): over every page the parser accepts (review 28813a2e
    finding 1), each page's `$L` and `$I` read from its own header line here, without the parser (review f6e6801f
    finding 1): pages by Currier language (`$L`, or "unknown") and by section (`section_of_page`); every count an
    integer (review f6e6801f finding 2)."""
    errors = []
    for name in ("pages_by_language", "pages_by_section", "warnings"):
        if name not in report:
            errors.append(f"Build report: {name} is missing")
    # the source's lines by the parser's boundaries (CR, LF, CRLF), not str.splitlines (review d0d5afef finding 1)
    lines = _source_lines(source)
    languages: dict[str, int] = {}
    sections: dict[str, int] = {}
    for page_id, header_line in _accepted_pages(str(source), _file_version(source)):
        text = (lines[header_line - 1] or "") if 0 < header_line <= len(lines) else ""
        header = _PAGE_HEADER.match(text.rstrip("\r\n"))
        variables = _page_settings(header.group(2)) if header else {}
        key = variables.get("L") or "unknown"
        languages[key] = languages.get(key, 0) + 1
        section = section_of_page(page_id, variables.get("I"))
        if section:
            sections[section] = sections.get(section, 0) + 1
    for name, expected in (("pages_by_language", languages), ("pages_by_section", sections)):
        if name not in report:
            continue
        recorded = report[name]
        if not isinstance(recorded, dict) or not all(_is_count(v) for v in recorded.values()):
            errors.append(f"Build report: {name} holds a value that is not a count")
        elif recorded != expected:
            errors.append(f"Build report: {name} is not the source's {expected}")
    return errors


def _report_warnings(records: list[dict], report: dict[str, Any], source: Path) -> list[str]:
    """The build report's warnings hold every warning the build gives (AV9 F1): each parser warning, as `parser: <warning>`,
    exactly, and one charset warning for each row whose `text_clean` holds a character outside the allowed set; none can
    be erased. Other notes in the list are not checked (a reviewer proof, cb967c21 finding 2, writes one).
    """
    from vcat.charset import validate_text_clean

    if not isinstance(report.get("warnings"), list):
        return [] if "warnings" not in report else ["Build report: warnings is not a list"]
    # the parser's warnings, from the parse cached per file version
    expected_parser = [f"parser: {w}" for w in _source_loci(str(source), _file_version(source))[2]]
    recorded = [str(w) for w in report["warnings"]]
    errors = []
    if [w for w in recorded if w.startswith("parser: ")] != expected_parser:
        errors.append("Build report: the parser warnings are not the parser's")
    # one charset warning for each flagged row, counted, so a repeated warning is a difference (review 28813a2e finding 3)
    flagged = sorted(
        f"{r.get('page_id')}:{r.get('line_number')}"
        for r in records
        if not validate_text_clean(str(r.get("text_clean", "")))[0]
    )
    charset = sorted(
        w[len("Invalid chars in ") :].split(": ", 1)[0]
        for w in recorded
        if w.startswith("Invalid chars in ")
    )
    if charset != flagged:
        errors.append(
            f"Build report: the charset warnings name {sorted(charset)[:5]}, the rows {sorted(flagged)[:5]}"
        )
    return errors


def _eva_parquet_errors(path: Path, records: list[dict]) -> list[str]:
    try:
        import pyarrow.parquet as pq

        rows = pq.read_table(path).to_pylist()
    except Exception as error:  # an unreadable file is a finding, whatever pyarrow raises
        return [f"{path.name} cannot be read as Parquet: {error}"]
    canonical = [json.dumps(r, sort_keys=True) for r in records]
    if [json.dumps(r, sort_keys=True) for r in rows] != canonical:
        return [f"{path.name} does not hold exactly the rows of eva_lines.jsonl"]
    return []


def check_manifest_files(output_dir: Path, records: list[dict]) -> list[str]:
    """Every file the release manifest lists is there and is what it says (AV5 F3, B-056): the JSONL matches its recorded
    SHA-256; the EVA Parquet, whenever the output holds one, listed or not (AV8 F3), holds exactly the rows of the JSONL;
    the manifest's statistics are the rows' and the build report's (AV8 F2). Without a release manifest (a test build)
    there is nothing listed to check."""
    errors: list[str] = []
    parquet = output_dir / "eva_lines.parquet"
    if parquet.is_file():
        errors.extend(_eva_parquet_errors(parquet, records))
    manifest_path = output_dir / "release_manifest.json"
    if not manifest_path.exists():
        return errors
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        return errors + [f"release manifest is not JSON: {error}"]
    errors.extend(check_manifest_source(output_dir, manifest))
    # Every row is attributed to the source the release names (AV7 F4)
    name = (
        manifest.get("source", {}).get("name") if isinstance(manifest.get("source"), dict) else None
    )
    wrong = [r.get("line_id") for r in records if r.get("source") != name]
    if wrong:
        errors.append(
            f"{len(wrong)} rows name a source other than the release manifest's {name!r}, first {wrong[:5]}"
        )
    # The manifest's statistics are the rows' and the build report's (AV8 F2)
    stats = manifest.get("statistics", {})
    report_path = output_dir / "eva_lines_build_report.json"
    report = load_build_report(report_path) if report_path.exists() else {}
    expected_stats = {
        "total_records": len(records),
        "pages_in_source": report.get("total_pages_in_source"),
        "pages_with_lines": len({r.get("page_id") for r in records}),
        "pages_without_lines": report.get("pages_without_lines"),
    }
    for key, value in expected_stats.items():
        # each side must be a count; a counter missing from the build report authorizes nothing (review 07b7ddfc)
        if not _is_count(value):
            errors.append(
                f"release manifest statistics {key}: the build report gives no count ({value!r})"
            )
        elif stats.get(key) != value or not _is_count(stats.get(key)):
            errors.append(f"release manifest statistics {key} is {stats.get(key)!r}, not {value!r}")
    for entry in manifest.get("files", []):
        path = output_dir / str(entry.get("name"))
        if not path.is_file():
            errors.append(f"release manifest lists {entry.get('name')!r}, which is missing")
            continue
        sha = entry.get("sha256")
        if sha and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            errors.append(f"{path.name} does not match the SHA-256 the release manifest records")
    return errors


def check_manifest_source(output_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """The release manifest's source pin is the build's (AV6 F3, B-074): its SHA-256 is the build report's
    source_hash and the bytes of that source, its "verified" is the report's, and it says "pinned" exactly
    when that is the hash data_sources/sources.yaml pins for the file."""
    source = manifest.get("source")
    if not isinstance(source, dict):
        return ["release manifest names no source"]
    report_path = output_dir / "eva_lines_build_report.json"
    if not report_path.exists():
        return ["release manifest: no build report to check its source against"]
    report = load_build_report(report_path)
    errors = []
    expected = source.get("expected_sha256")
    if expected != report.get("source_hash"):
        errors.append(
            "release manifest: source expected_sha256 is not the build report's source_hash"
        )
    path = resolve_source(report.get("source_file", ""))
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path else None
    if expected != actual:
        errors.append("release manifest: source expected_sha256 is not the SHA-256 of the source")
    if source.get("verified") is not report.get("source_verified"):
        errors.append("release manifest: source verified is not the build report's source_verified")
    pinned = path is not None and actual == expected == pinned_sha256(path)
    if source.get("pinned") is not pinned:
        errors.append(
            f"release manifest: source pinned is {source.get('pinned')!r}, "
            f"but data_sources/sources.yaml says {pinned!r}"
        )
    return errors


def check_mismatch_index(output_dir: Path) -> list[str]:
    """The mismatch index, when the output holds one, conforms to its schema (B-023, review f6661c36 finding 1), is the
    comparison of the sources (B-072) and is matched by its Parquet (B-073). An output that holds the Parquet or the report
    without the JSONL is incomplete (AV7 F2)."""
    path = output_dir / "mismatch_index.jsonl"
    if not path.exists():
        orphans = [
            name
            for name in ("mismatch_index.parquet", "mismatch_report.json")
            if (output_dir / name).exists()
        ]
        return [f"{name} is present without mismatch_index.jsonl" for name in orphans]
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except ValueError as error:
        return [f"mismatch_index.jsonl is not JSON lines: {error}"]
    valid, errors = validate_mismatch_index(rows)
    if not valid:
        return [f"mismatch index: {e}" for e in errors]
    problems = check_mismatch_content(rows)
    problems += check_mismatch_parquet(output_dir, rows)
    problems += check_mismatch_report(output_dir, rows)
    return problems


def _file_version(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


@functools.lru_cache(maxsize=8)
def _source_loci(
    path: str, version: tuple[int, int]
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    """(locus id -> locus, the ids of the loci the parser rejected, every parser warning) of a source file, parsed once per
    file version (the key includes size and mtime)."""
    from parsers import IVTFFParser

    parser = IVTFFParser()
    loci = {locus.locus_id: locus for page in parser.parse_file(Path(path)) for locus in page.loci}
    rejected = tuple(w.locus_id for w in parser.warnings if w.locus_id)
    return loci, rejected, tuple(str(w) for w in parser.warnings)


@functools.lru_cache(maxsize=8)
def _page_locus_counts(path: str, version: tuple[int, int]) -> dict[str, tuple[int, int]]:
    """Per page the parser accepts in a source file: (its paragraph loci, its label loci), parsed once per file version
    (the counts a page's `line_count` and `label_count` give; reach 660862e9 gap 1)."""
    from parsers import IVTFFParser
    from parsers.ivtff_parser import LocusType

    return {
        page.page_id: (
            sum(1 for locus in page.loci if locus.locus_type == LocusType.PARAGRAPH),
            sum(1 for locus in page.loci if locus.locus_type == LocusType.LABEL),
        )
        for page in IVTFFParser().parse_file(Path(path))
    }


@functools.lru_cache(maxsize=8)
def _rejected_pages(path: str, version: tuple[int, int]) -> tuple[str, ...]:
    """The ids of the pages the parser rejected in a source file (its warnings that name a page), in its order, parsed
    once per file version."""
    from parsers import IVTFFParser

    parser = IVTFFParser()
    list(parser.parse_file(Path(path)))
    return tuple(w.page_id for w in parser.warnings if w.page_id)


@functools.lru_cache(maxsize=8)
def _accepted_pages(path: str, version: tuple[int, int]) -> tuple[tuple[str, int], ...]:
    """(page id, the line number of its header) of every page the parser accepts in a source file, in source order,
    parsed once per file version: which pages the build has, whatever the report says (reach f568acf9 gap 1, review
    28813a2e finding 1). The pages' variables are NOT taken from the parser (review f6e6801f finding 1): they are read
    from those header lines by `_page_settings`."""
    from parsers import IVTFFParser

    return tuple((page.page_id, page.source_line) for page in IVTFFParser().parse_file(Path(path)))


def section_of_page(page_id: str, illustration: str | None) -> str | None:
    """VCAT's section name for a page: the name of its `$I` code, else the folio range its number falls in (the rule
    `docs/data_model.md` gives for `section`; review 28813a2e finding 2), else None. The validator's own copy; a test
    checks it against the builder's on every page of every cached source."""
    if illustration in SECTION_OF_ILLUSTRATION:
        return SECTION_OF_ILLUSTRATION[illustration]
    match = re.match(r"f(\d+)", page_id)
    if not match:
        return None
    folio = int(match.group(1))
    for last, name in (
        (66, "herbal"),
        (73, "astronomical"),
        (84, "biological"),
        (86, "cosmological"),
        (102, "pharmaceutical"),
    ):
        if folio <= last:
            return name
    return "recipes"


@functools.lru_cache(maxsize=16)
def _source_readings(path: str, version: tuple[int, int], profile: str) -> dict[str, str]:
    """locus id -> the profile's reading of its text_raw, computed once per file version and profile."""
    from vcat.profiles import apply_profile

    return {
        lid: apply_profile(profile, locus.text_raw)
        for lid, locus in _source_loci(path, version)[0].items()
    }


@functools.lru_cache(maxsize=16384)
def _compare(a: str, b: str, profile: str) -> tuple[str, float]:
    from vcat.comparison import compare

    return compare(a, b, profile)


def _mismatch_sources() -> dict[str, Any]:
    """id -> the registry record, for every source the mismatch dataset's record in `sources.yaml` names (ZL and IT
    compared; CD, FG and GC by presence)."""
    from vcat.sources import cached_sources, load_sources

    dataset = next(
        d for d in load_sources()["datasets"] if d["name"] == "voynich-transcription-mismatch"
    )
    records = {s.id: s for s in cached_sources()}
    return {sid: records[sid] for sid in dataset["sources"]}


def check_mismatch_content(rows: list[dict]) -> list[str]:
    """The mismatch rows are the comparison of the cached sources (AV6 F1, B-072; AV7 F1): one row per locus id of ZL or IT,
    each with its page and number, the sources' raw texts, readings, locus codes and source lines, ZL and IT in
    `sources_present` exactly when they hold the locus, and each verdict and score the one `vcat.comparison.compare` gives
    under the row's profile. The sources are read from `data_sources/sources.yaml` and parsed here; the builder is not
    consulted."""
    if not rows:
        return ["mismatch index holds no rows"]
    registry = _mismatch_sources()
    versions = {
        sid: (str(registry[sid].path), _file_version(registry[sid].path)) for sid in ("ZL", "IT")
    }
    loci = {sid: _source_loci(*versions[sid])[0] for sid in ("ZL", "IT")}
    errors: list[str] = []
    ids = [row["line_id"] for row in rows]
    expected = set(loci["ZL"]) | set(loci["IT"])
    # the documented order: page order, then locus number (docs/data_model.md section 10; B-099, AV11 F4)
    keys = [
        (*page_order_key(str(row.get("page_id", ""))), _number(row.get("line_number")))
        for row in rows
    ]
    if keys != sorted(keys):
        errors.append("mismatch index: rows are not in page order then locus number")
    if len(ids) != len(set(ids)):
        errors.append("mismatch index: a locus id is a row more than once")
    if set(ids) != expected:
        missing, extra = sorted(expected - set(ids)), sorted(set(ids) - expected)
        errors.append(
            f"mismatch index: rows differ from the sources' loci (missing {missing[:5]}, extra {extra[:5]})"
        )
    for row in rows:
        line_id, profile = row["line_id"], row["comparison_profile"]
        page, _, number = line_id.rpartition(":")
        if row.get("page_id") != page or str(row.get("line_number")) != number:
            errors.append(f"mismatch index: {line_id} page_id or line_number is not its locus id's")
        held = {}
        for sid, prefix in (("ZL", "zl"), ("IT", "it")):
            locus = loci[sid].get(line_id)
            held[sid] = locus
            fields = {
                f"{prefix}_text_raw": locus.text_raw if locus else None,
                f"{prefix}_reading": (
                    _source_readings(*versions[sid], profile)[line_id] if locus else None
                ),
                f"{prefix}_locus_type": locus.locus_code if locus else None,
                f"{prefix}_source_line": locus.source_line if locus else None,
            }
            for name, value in fields.items():
                if row.get(name) != value:
                    errors.append(f"mismatch index: {line_id} {name} is not the source's")
            if (prefix in row["sources_present"]) != (locus is not None):
                errors.append(f"mismatch index: {line_id} sources_present is wrong about {prefix}")
        # Presence of every source the dataset names, CD, FG and GC included (AV8 F1)
        for sid in registry:
            if sid in ("ZL", "IT"):
                continue
            holds = (
                line_id
                in _source_loci(str(registry[sid].path), _file_version(registry[sid].path))[0]
            )
            if (sid.lower() in row["sources_present"]) != holds:
                errors.append(
                    f"mismatch index: {line_id} sources_present is wrong about {sid.lower()}"
                )
        a, b = held["ZL"], held["IT"]
        if a is not None and b is not None:
            verdict, score = _compare(a.text_raw, b.text_raw, profile)
            if row["status"] != verdict or row["similarity_score"] != round(score, 6):
                errors.append(
                    f"mismatch index: {line_id} status {row['status']!r} is not {verdict!r}"
                )
        else:
            if row["status"] != ("zl_only" if a is not None else "it_only"):
                errors.append(
                    f"mismatch index: {line_id} status {row['status']!r} for a one-source locus"
                )
            # a locus only one source holds has no comparison, so no score (reach 5d6306ba gap 1)
            if row["similarity_score"] is not None:
                errors.append(
                    f"mismatch index: {line_id} has a similarity score for a one-source locus"
                )
    return errors


def check_mismatch_report(output_dir: Path, rows: list[dict]) -> list[str]:
    """The mismatch report is the rows' and the sources' (AV7 F3, AV8 F2): every summary field is present and recomputed
    from the rows (total, counts per status, the loci both hold, agreement, the different loci's count and median
    similarity); for every source the dataset names, the file, SHA-256 and emitted loci are the source's, and its reported
    loci and warnings are every rejection and warning the parser gives, so none can be erased or invented.
    """
    import statistics

    from vcat.comparison import AGREEING, VERDICTS

    path = output_dir / "mismatch_report.json"
    if not path.is_file():
        return ["mismatch_report.json is missing beside mismatch_index.jsonl"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        return [f"mismatch_report.json is not JSON: {error}"]
    errors: list[str] = []
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    both = sum(counts.get(v, 0) for v in VERDICTS)
    agreeing = sum(counts.get(v, 0) for v in AGREEING)
    different = sorted(
        r["similarity_score"]
        for r in rows
        if r["status"] == "different" and r["similarity_score"] is not None
    )
    statuses = (*VERDICTS, "zl_only", "it_only")
    expected = {
        "total_lines": len(rows),
        "status_counts": {status: counts.get(status, 0) for status in statuses},
        "both_present": both,
        "agreeing": agreeing,
        "agreement_rate": agreeing / both if both else None,
        "different_rate": counts.get("different", 0) / both if both else None,
        "different_similarity": {
            "count": len(different),
            "median": statistics.median(different) if different else None,
        },
    }
    for key, value in expected.items():
        if key not in report:
            errors.append(f"mismatch report: {key} is missing")
        elif report[key] != value:
            errors.append(
                f"mismatch report: {key} is not the rows' ({report[key]!r}, not {value!r})"
            )
    profiles = sorted({r["comparison_profile"] for r in rows})
    if report.get("comparison_profile") not in profiles or len(profiles) != 1:
        errors.append(f"mismatch report: comparison_profile is not the rows' {profiles}")
    for sid, source in _mismatch_sources().items():
        entry = report.get("sources", {}).get(sid.lower())
        if not isinstance(entry, dict):
            errors.append(f"mismatch report: no entry for {sid}")
            continue
        loci, rejected, warnings = _source_loci(str(source.path), _file_version(source.path))
        if entry.get("file") != source.path.name:
            errors.append(f"mismatch report: the {sid} file is not the source's")
        if entry.get("sha256") != hashlib.sha256(source.path.read_bytes()).hexdigest():
            errors.append(f"mismatch report: the {sid} SHA-256 is not the source's")
        if entry.get("loci_emitted") != len(loci):
            errors.append(f"mismatch report: the {sid} emitted loci are not the parser's")
        if entry.get("reported_loci") != list(rejected):
            errors.append(f"mismatch report: {sid} reported loci are not the parser's rejections")
        if entry.get("warnings") != list(warnings):
            errors.append(f"mismatch report: {sid} warnings are not the parser's")
    return errors


def check_mismatch_parquet(output_dir: Path, rows: list[dict]) -> list[str]:
    """The mismatch Parquet delivered beside the JSONL exists and holds exactly its rows (AV6 F2, AB2 F1, B-073)."""
    path = output_dir / "mismatch_index.parquet"
    if not path.is_file():
        return ["mismatch_index.parquet is missing beside mismatch_index.jsonl"]
    try:
        import pyarrow.parquet as pq

        table = pq.read_table(path).to_pylist()
    except Exception as error:  # an unreadable file is a finding, whatever pyarrow raises
        return [f"mismatch_index.parquet cannot be read as Parquet: {error}"]
    # in the same order: the JSONL's order is checked (B-099), so the Parquet's must be the same rows in that order (B-116)
    canonical = [json.dumps(r, sort_keys=True) for r in rows]
    if [json.dumps(r, sort_keys=True) for r in table] != canonical:
        return [
            "mismatch_index.parquet does not hold exactly the rows of mismatch_index.jsonl, in their order"
        ]
    return []


METADATA_TABLES = ("pages", "folios", "quires", "bifolia", "page_orders", "page_canvases", "layers")
#: What identifies a row of each metadata table
METADATA_KEYS = {
    "pages": ("page_id",),
    "folios": ("folio_id",),
    "quires": ("quire_id",),
    "bifolia": ("bifolio_id",),
    "page_orders": ("order", "position"),
    "page_canvases": ("page_id", "canvas_id"),
    "layers": ("layer",),
}


def _expected_words(lines: list[dict]) -> list[dict]:
    """The word rows the EVA lines give, recomputed here without `vcat.words` or the builder (roadmap item 2.6): a word
    is a run of `text_clean` between `.`, `,` or whitespace, the space after it `uncertain` when only commas follow it;
    a paragraph runs from a `P` line with `<%>` to the `P` line with `<$>` on the same page (IVTFF 2.0 section 6.9).
    """
    expected: list[dict] = []
    page = None
    opened: list[dict] | None = None
    number = position = 0
    for line in lines:
        if line.get("page_id") != page:
            page, opened, number, position = line.get("page_id"), None, 0, 0
        text_line = str(line.get("locus_type", ""))[1:2] == "P"
        markers = line.get("markers") or []
        if text_line and "<%>" in markers:
            number, opened, position = number + 1, [], 0
        inside = text_line and opened is not None
        position = position + 1 if inside else position
        pieces = [p for p in re.split(r"([.,\s]+)", str(line.get("text_clean", ""))) if p]
        found: list[tuple[str, str | None]] = []
        for piece in pieces:
            if re.fullmatch(r"[.,\s]+", piece):
                if found and found[-1][1] is None:
                    found[-1] = (
                        found[-1][0],
                        "certain" if re.search(r"[.\s]", piece) else "uncertain",
                    )
            else:
                found.append((piece, None))
        if found:
            found[-1] = (found[-1][0], None)
        for index, (word, space) in enumerate(found, start=1):
            row = {
                "word_id": f"{line.get('line_id')}.{index}",
                "line_id": line.get("line_id"),
                "page_id": line.get("page_id"),
                "line_index": line.get("line_index"),
                "word_index": index,
                "word": word,
                "space_after": space,
                "line_initial": index == 1,
                "line_final": index == len(found),
                "paragraph_id": f"{page}.p{number}" if inside else None,
                "line_in_paragraph": position if inside else None,
                "paragraph_initial": False,
                "paragraph_final": False,
                "line_type": line.get("line_type"),
                "locus_type": line.get("locus_type"),
                "hand": line.get("hand"),
                "currier_language": line.get("currier_language"),
                "section": line.get("section"),
                "quire": line.get("quire"),
            }
            expected.append(row)
            if inside and opened is not None:
                opened.append(row)
        if inside and "<$>" in markers and opened is not None:
            if opened:
                opened[0]["paragraph_initial"] = opened[-1]["paragraph_final"] = True
            opened, position = None, 0
    return expected


def check_words(output_dir: Path) -> list[str]:
    """`_check_words`, remembered for the same four files' content: the validators run it on every call, and a row-by-row
    schema check of every word is seconds each time. The key is a hash of each file's bytes and, for the JSON files, of
    their text as the check reads it, never its size or time, so changed content is always checked again (review
    f66f47d9 finding 1, review 88bdfa1e finding 1)."""
    # each file by its bytes (what the provenance hash reads; a line-ending change is a change: review 88bdfa1e finding 1)
    # and by its text (what the row checks read)
    digest = hashlib.sha256()
    for name in (
        "eva_lines.jsonl",
        "eva_words.jsonl",
        "eva_words_report.json",
        "eva_words.parquet",
    ):
        path = output_dir / name
        digest.update(f"{name}:".encode())
        if not path.is_file():
            digest.update(b"\0absent")
            continue
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        if name.endswith((".jsonl", ".json")):
            digest.update(hashlib.sha256(path.read_text(encoding="utf-8").encode()).digest())
    return list(_words_checked(str(Path(output_dir).resolve()), digest.hexdigest()))


@functools.lru_cache(maxsize=16)
def _words_checked(output_dir: str, key: str) -> tuple[str, ...]:
    """The word check of one state of the files (`key`, the hash of their content), run once."""
    return tuple(_check_words(Path(output_dir)))


def _check_words(output_dir: Path) -> list[str]:
    """The word level beside the EVA lines (`eva_words.jsonl`, roadmap item 2.6), checked by both validators: its rows are
    the lines' words recomputed here, compared as JSON (so a type change is a difference); each row meets
    `schemas/eva_words.schema.json`; the Parquet holds exactly the JSONL's rows; the report names the lines file it read by
    its SHA-256 and its totals are the rows'. No `eva_words.jsonl`, nothing to check (a build of the lines alone).
    """
    words_path = output_dir / "eva_words.jsonl"
    if not words_path.is_file():
        # a word Parquet or report with no JSONL is a word level that lost its rows, not a build of the lines alone
        # (reach 71660867 gap 4)
        present = [
            n for n in ("eva_words.parquet", "eva_words_report.json") if (output_dir / n).exists()
        ]
        return [f"eva_words.jsonl is missing beside {', '.join(present)}"] if present else []
    errors: list[str] = []
    lines_path = output_dir / "eva_lines.jsonl"
    lines = [
        json.loads(x) for x in lines_path.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    rows = [json.loads(x) for x in words_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    expected = _expected_words(lines)

    def as_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    if as_json(rows) != as_json(expected):
        first = next(
            (
                i
                for i, (a, b) in enumerate(zip(rows, expected, strict=False))
                if as_json(a) != as_json(b)
            ),
            min(len(rows), len(expected)),
        )
        errors.append(
            f"eva_words.jsonl is not the lines' words ({len(rows)} rows, {len(expected)} expected; first difference at "
            f"row {first + 1})"
        )
    from validators.schema import validate_against_schema

    valid, problems = validate_against_schema(rows, "eva_words.schema.json")
    if not valid:
        errors.extend(f"eva_words schema: {p}" for p in problems[:5])
    parquet = output_dir / "eva_words.parquet"
    if not parquet.is_file():
        errors.append("eva_words.parquet is missing beside its JSONL")
    else:
        import pyarrow.parquet as pq

        if as_json(pq.read_table(parquet).to_pylist()) != as_json(rows):
            errors.append("eva_words.parquet does not hold exactly the rows of eva_words.jsonl")
    report_path = output_dir / "eva_words_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    totals = {
        "lines_file": lines_path.name,
        "lines_sha256": hashlib.sha256(lines_path.read_bytes()).hexdigest(),
        "tokenizer": "vcat/words.py",
        "total_words": len(expected),
        "lines": len(lines),
        "lines_without_words": len(lines) - len({r["line_id"] for r in expected}),
        "paragraphs": len({r["paragraph_id"] for r in expected if r["paragraph_id"]}),
        "words_in_paragraphs": sum(1 for r in expected if r["paragraph_id"]),
        "uncertain_spaces": sum(1 for r in expected if r["space_after"] == "uncertain"),
    }
    if report != totals:
        wrong = sorted(k for k in set(report) | set(totals) if report.get(k) != totals.get(k))
        errors.append(f"eva_words_report.json is not the words' provenance and totals: {wrong}")
    return errors


#: Yale's canvases of MS 408, as `vcat.iiif` extracts them from the manifest (roadmap item 2.4)
# the path `vcat.iiif` names, not one spelled again here (B-120; imported at the top)


def _check_page_canvases(tables: dict[str, list[dict]], report: dict[str, Any]) -> list[str]:
    """The page-to-canvas links are Yale's canvases read by the rule `vcat.iiif` documents, recomputed here with the
    validator's own reading of the labels: a page lies on each canvas whose label names its folio side, `part` when the
    label says that side is shown in part. Every page has a link; the extract is the one its hash names, and the
    report's manifest, hash and counts are the extract's and the links'."""
    errors: list[str] = []
    extract = json.loads(IIIF_CANVASES.read_text(encoding="utf-8"))
    canvases = extract.get("canvases") or []
    text = json.dumps(canvases, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if hashlib.sha256(text.encode()).hexdigest() != extract.get("canvases_sha256"):
        errors.append(
            f"{IIIF_CANVASES.name}: the canvases are not the ones its canvases_sha256 names"
        )
    from parsers.metadata_parser import SPANNING_PAGES

    def sides(page_id: str) -> set[tuple[int, str]]:
        if page_id in SPANNING_PAGES:
            return {(int(folio[1:]), side[0]) for folio, side in SPANNING_PAGES[page_id]}
        named = re.fullmatch(r"f(\d+)([rv])\d*", page_id)
        return {(int(named.group(1)), named.group(2))} if named else set()

    shown = [
        (
            canvas,
            [
                (int(folio), side, bool(part))
                for folio, side, part in re.findall(
                    r"(\d+)([rv])((?:\s*\(part\))?)",
                    re.sub(r"\((?:part of [^)]*|foldout)\)", "", str(canvas.get("label"))),
                )
            ],
        )
        for canvas in canvases
    ]
    expected = []
    for page in tables.get("pages", []):
        page_id = str(page.get("page_id"))
        on = sides(page_id)
        for canvas, named in shown:
            parts = [part for folio, side, part in named if (folio, side) in on]
            if parts:
                expected.append(
                    {
                        "page_id": page_id,
                        "canvas_index": canvas.get("index"),
                        "canvas_id": canvas.get("canvas_id"),
                        "canvas_label": canvas.get("label"),
                        "coverage": "part" if any(parts) else "whole",
                        "image_service": canvas.get("image_service"),
                    }
                )
    links = tables.get("page_canvases", [])

    # compared as JSON, so a number of another type (a float index, 1.0 for 1) is a difference (review f6b7579c
    # finding 2)
    def as_json(rows: list[dict]) -> str:
        return json.dumps(rows, sort_keys=True, ensure_ascii=False)

    if as_json(links) != as_json(expected):
        errors.append(
            f"metadata/page_canvases.jsonl is not the pages' links to Yale's canvases ({len(links)} rows, "
            f"{len(expected)} expected)"
        )
    unlinked = sorted(
        {str(p.get("page_id")) for p in tables.get("pages", [])}
        - {str(r.get("page_id")) for r in links}
    )
    if unlinked:
        errors.append(f"pages with no link to Yale's images: {unlinked[:5]}")
    for name, value in (
        ("iiif_manifest", extract.get("manifest")),
        ("iiif_manifest_sha256", extract.get("manifest_sha256")),
        ("total_page_canvases", len(expected)),
        ("partial_page_canvases", sum(1 for r in expected if r["coverage"] == "part")),
    ):
        if report.get(name) != value:
            errors.append(
                f"metadata report {name} is {report.get(name)!r}, the links give {value!r}"
            )
    return errors


def check_metadata(output_dir: Path) -> list[str]:
    """The metadata datasets beside the EVA rows (`metadata/`), checked by both validators (B-095, AB5 F1): each table's
    Parquet file holds exactly its JSONL's rows, and the physical structure (roadmap item 2.5) is the source's, read here
    without the parser: each named page order lists the source's page headers (`zl_file` in their order, `foliation` in
    folio order), and each bifolio is the pages whose headers share a quire `$Q` and a bifolio `$B`. No `metadata/`
    directory, nothing to check (a build of the EVA rows alone)."""
    meta = output_dir / "metadata"
    if not meta.is_dir():
        return []
    errors: list[str] = []
    tables: dict[str, list[dict]] = {}
    for stem in METADATA_TABLES:
        jsonl, parquet = meta / f"{stem}.jsonl", meta / f"{stem}.parquet"
        if not jsonl.is_file():
            errors.append(f"metadata/{stem}.jsonl is missing")
            continue
        # read here, not through load_jsonl: that loads the EVA rows, and a check of the EVA rows may stand it in
        tables[stem] = [
            json.loads(line)
            for line in jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not parquet.is_file():
            errors.append(f"metadata/{stem}.parquet is missing beside its JSONL")
            continue
        try:
            import pyarrow.parquet as pq

            parquet_rows = pq.read_table(parquet).to_pylist()
        except Exception as error:  # an unreadable file is an error, not a crash
            errors.append(f"metadata/{stem}.parquet cannot be read as Parquet: {error}")
            continue
        # compared as canonical JSON, so a Boolean stored as an integer differs (`True == 1` in Python; review 020f7450
        # finding 2)
        if json.dumps(parquet_rows, sort_keys=True) != json.dumps(tables[stem], sort_keys=True):
            errors.append(
                f"metadata/{stem}.parquet does not hold exactly the rows of metadata/{stem}.jsonl"
            )
    # each row once: a repeated row passes every comparison by content, so the tables' keys are counted (reach 6e91b4a2
    # gap 1: a duplicated sheet)
    # a sheet's id is the one its quire and number give, so a sheet repeated under another id is still caught (review
    # caac4571 finding 1), and its quire and number are counted as its key besides
    for row in tables.get("bifolia", []):
        expected_id = f"{row.get('quire_id')}.b{row.get('bifolio_number')}"
        if row.get("bifolio_id") != expected_id:
            errors.append(
                f"bifolio {row.get('bifolio_id')!r} is not named {expected_id!r}, its quire and number"
            )
    for stem, key in [*METADATA_KEYS.items(), ("bifolia", ("quire_id", "bifolio_number"))]:
        keys = [tuple(row.get(k) for k in key) for row in tables.get(stem, [])]
        repeated = sorted({str(k) for k in keys if keys.count(k) > 1})
        if repeated:
            errors.append(f"metadata/{stem}.jsonl repeats {', '.join(key)}: {repeated[:5]}")
    # the published layers are the registry's, and the metadata's VCAT judgements say whose they are (roadmap item 2.8)
    from vcat.layers import load_layers, metadata_layer_names

    # for the transliteration the report says the metadata was built from (review 7454c2f9 finding 3)
    report_file = meta / "metadata_report.json"
    built_from = (
        json.loads(report_file.read_text(encoding="utf-8")).get("source_file", "")
        if report_file.is_file()
        else ""
    )
    built_source = resolve_source(str(built_from)) if built_from else None
    layers = load_layers(None, *metadata_layer_names(built_source or str(built_from)))
    if "layers" in tables and tables["layers"] != layers:
        errors.append("metadata/layers.jsonl is not data_sources/layers.yaml")
    vcat_fields = {f for r in layers if r["kind"] == "vcat" for f in r["fields"]}
    for stem in ("pages", "folios"):
        if f"voynich-manuscript-metadata:{stem}.section" in vcat_fields:
            wrong = sorted(
                {str((row.get("section") or {}).get("attribution")) for row in tables.get(stem, [])}
                - {"vcat"}
            )
            if wrong:
                errors.append(
                    f"metadata/{stem}.jsonl attributes its sections to {wrong}, not to VCAT"
                )
    # a Boolean is a Boolean: a string or an integer under the same name passes a comparison of content (B-107)
    for row in tables.get("bifolia", []):
        if not isinstance(row.get("is_complete"), bool):
            errors.append(
                f"bifolio {row.get('bifolio_id')}: is_complete {row.get('is_complete')!r} is not a Boolean"
            )
    report_path = meta / "metadata_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    source = resolve_source(str(report.get("source_file", "")))
    if source is None:
        return errors + ["metadata/metadata_report.json names no source file this repository holds"]
    headers: list[tuple[str, dict[str, str]]] = []
    for line in _source_lines(source):
        if line is not None and (page := _PAGE_HEADER.match(line.rstrip("\r\n"))):
            if "." not in page.group(1):
                headers.append((page.group(1), _page_settings(page.group(2))))
    listed = [page_id for page_id, _ in headers]
    # the file order is named after the source the report names (review 020f7450 finding 1)
    from vcat.sources import registered_source

    registered = registered_source(source)
    file_order_name = f"{registered.id.lower()}_file" if registered else "source_file"
    expected_orders = {file_order_name: listed, "foliation": sorted(listed, key=page_order_key)}
    orders: dict[str, list[tuple[int, str]]] = {}
    for row in tables.get("page_orders", []):
        orders.setdefault(str(row.get("order")), []).append(
            (_number(row.get("position")), str(row.get("page_id")))
        )
        if not str(row.get("attribution") or "").strip():
            errors.append(
                f"page order {row.get('order')!r} row {row.get('position')} has no attribution"
            )
    for name, expected in expected_orders.items():
        got = [page_id for _, page_id in sorted(orders.get(name, []))]
        positions = sorted(position for position, _ in orders.get(name, []))
        if got != expected or positions != list(range(1, len(expected) + 1)):
            errors.append(
                f"page order {name!r} is not the source's ({len(got)} rows, {len(expected)} pages)"
            )
    if set(orders) - set(expected_orders):
        errors.append(
            f"page orders the source does not define: {sorted(set(orders) - set(expected_orders))}"
        )
    groups: dict[tuple[str, str], set[str]] = {}
    for page_id, settings in headers:
        if "Q" in settings and "B" in settings:
            groups.setdefault((settings["Q"], settings["B"]), set()).add(page_id)
    # Each page's folio from the page's own name, read here (the one page drawn across two folios, `fRos`, by the
    # metadata layer's documented table), never from the candidate's pages table, which must agree; the quire from the
    # headers' `$Q`; the leaves in folio order; each leaf on one sheet (review deca4e05 finding 1: consistent changes to
    # two tables, another quire prefix and a reversed leaf list all passed)
    from parsers.metadata_parser import SPANNING_PAGES

    def page_folio(page_id: str) -> str:
        if page_id in SPANNING_PAGES:
            return SPANNING_PAGES[page_id][0][0]
        number = re.match(r"f(\d+)", page_id)
        return f"f{int(number.group(1))}" if number else page_id

    def folio_key(folio_id: str) -> tuple[int, str]:
        return (int(folio_id[1:]), "") if folio_id[1:].isdigit() else (10**6, folio_id)

    folio_of = {page_id: page_folio(page_id) for page_id, _ in headers}
    for r in tables.get("pages", []):
        page_id = str(r.get("page_id"))
        if r.get("folio_id") != folio_of.get(page_id):
            errors.append(
                f"page {page_id} lies on {folio_of.get(page_id)}, not {r.get('folio_id')}"
            )
    # each page's lines and labels are the source's paragraph and label loci on it, and its section is the metadata
    # layer's documented folio ranges (`parsers.metadata_parser.SECTION_MAPPING`, VCAT's judgement, with a medium
    # confidence and a dispute flag at a range's ends), so the quires' and the report's totals and sections, summed from
    # the pages, are the source's too (reach 660862e9 gaps 1 and 2: one line or one section moved between quires passed)
    from parsers.metadata_parser import SECTION_MAPPING

    def page_section(page_id: str) -> dict[str, Any]:
        return folio_section(folio_of[page_id])

    def folio_section(folio_id: str) -> dict[str, Any]:
        number = int(folio_id[1:]) if folio_id[1:].isdigit() else None
        value, boundary = "unknown", False
        for start, end, section in SECTION_MAPPING.values():
            if number is not None and start <= number <= end:
                value = section.value
                break
        if number is not None:
            boundary = any(number in (start, end) for start, end, _ in SECTION_MAPPING.values())
        return {
            "value": value,
            "attribution": "vcat",
            "confidence": "medium" if boundary else "high",
            "disputed": boundary,
            "alternatives": [],
        }

    locus_counts = _page_locus_counts(str(source), _file_version(source))
    header_settings = dict(headers)
    for r in tables.get("pages", []):
        page_id = str(r.get("page_id"))
        if page_id not in folio_of:
            continue  # a page the source lacks is reported below, with the population
        lines, labels = locus_counts.get(page_id, (0, 0))
        if r.get("line_count") != lines or r.get("label_count") != labels:
            errors.append(
                f"page {page_id}: {r.get('line_count')!r} lines and {r.get('label_count')!r} labels, the source"
                f" {lines} and {labels}"
            )
        if r.get("section") != page_section(page_id):
            errors.append(
                f"page {page_id}: section {r.get('section')!r} is not {page_section(page_id)!r}"
            )
        # the page's own header gives its quire, place in the quire, language, hand and illustration type, so a page
        # moved to another quire in the pages table alone is refused (review 71df94e6 finding 1)
        settings = header_settings[page_id]
        own = {
            "quire_letter": settings.get("Q"),
            "quire_id": f"q{settings['Q']}" if settings.get("Q") else None,
            "page_in_quire": settings.get("P"),
            "currier_language": settings.get("L"),
            "hand": settings.get("H"),
            "illustration_type": settings.get("I"),
        }
        for field, header_value in own.items():
            if r.get(field) != header_value:
                errors.append(
                    f"page {page_id}: {field} {r.get(field)!r}, its header {header_value!r}"
                )

    # each page's folio number, side and panel fields, and each folio's page lists and foldout fields, read from the
    # page names (the one spanning page by the metadata layer's documented table), never from the candidate's tables
    # (audit 20261021-validators F1: erased page lists and flipped sides passed; audit 20261021-parsers F1, F2: a panel
    # total is the highest panel number on its folio side, a foldout's panel count the highest panel number on its sides;
    # review 1d0b83fe finding 3)
    def page_place(page_id: str) -> tuple[int | None, str | None, int | None]:
        if page_id in SPANNING_PAGES:
            folio, side = SPANNING_PAGES[page_id][0]
            return int(folio[1:]), side, None
        named = re.fullmatch(r"f(\d+)([rv])(\d+)?", page_id)
        if not named:
            return None, None, None
        return (
            int(named.group(1)),
            "recto" if named.group(2) == "r" else "verso",
            int(named.group(3)) if named.group(3) else None,
        )

    places = {page_id: page_place(page_id) for page_id, _ in headers}
    highest_panel: dict[tuple[int | None, str | None], int] = {}
    for number, side, panel in places.values():
        if panel is not None:
            highest_panel[(number, side)] = max(highest_panel.get((number, side), 0), panel)
    for r in tables.get("pages", []):
        page_id = str(r.get("page_id"))
        if page_id not in places:
            continue
        number, side, panel = places[page_id]
        own_place = {
            "folio_number": number,
            "side": side,
            "panel_number": panel,
            "is_foldout_panel": panel is not None,
            "total_panels": highest_panel[(number, side)] if panel is not None else None,
        }
        for field, place_value in own_place.items():
            if r.get(field) != place_value:
                errors.append(
                    f"page {page_id}: {field} {r.get(field)!r}, its name gives {place_value!r}"
                )
    for row in tables.get("folios", []):
        folio_id = str(row.get("folio_id"))
        sides: dict[str, list[str]] = {"recto": [], "verso": []}
        own_panels = False
        for page_id, _ in headers:
            number, side, panel = places[page_id]
            if folio_of.get(page_id) == folio_id and side in sides:
                sides[side].append(page_id)
                own_panels = own_panels or panel is not None
        for page_id, _ in headers:
            if page_id in SPANNING_PAGES:
                also_folio, also_side = SPANNING_PAGES[page_id][1]
                if also_folio == folio_id:
                    sides[also_side].append(page_id)
        for side in sides:
            sides[side].sort(key=lambda p: places[p][2] or 0)
        is_foldout = len(sides["verso"]) > 1 or own_panels
        expected_folio = {
            "recto_page_ids": sides["recto"],
            "verso_page_ids": sides["verso"],
            "recto_page_id": sides["recto"][0] if sides["recto"] else None,
            "is_foldout": is_foldout,
            "panel_count": (
                max(
                    (places[p][2] or 0)
                    for p in sides["recto"] + sides["verso"]
                    if folio_of.get(p) == folio_id
                )
                or None
                if is_foldout
                else None
            ),
        }
        for field, folio_value in expected_folio.items():
            if row.get(field) != folio_value:
                errors.append(
                    f"folio {folio_id}: {field} {row.get(field)!r}, its pages give {folio_value!r}"
                )
    # each folio's lines are its own pages' (a spanning page's under the folio its record lives in) and its section the
    # documented range of its number (review 71df94e6 finding 2)
    lines_by_page = {
        str(r.get("page_id")): _number(r.get("line_count")) for r in tables.get("pages", [])
    }
    for row in tables.get("folios", []):
        folio_id = str(row.get("folio_id"))
        own_lines = sum(lines_by_page.get(p, 0) for p, f in folio_of.items() if f == folio_id)
        if row.get("total_lines") != own_lines:
            errors.append(
                f"folio {folio_id}: total_lines {row.get('total_lines')!r}, its pages {own_lines}"
            )
        if row.get("section") != folio_section(folio_id):
            errors.append(
                f"folio {folio_id}: section {row.get('section')!r} is not {folio_section(folio_id)!r}"
            )
    # every table holds its whole population: the source's pages, the folios they lie on, the quires their headers name
    # (B-108, AV11 F1: an empty table matching its empty Parquet passed)
    page_ids = [str(r.get("page_id")) for r in tables.get("pages", [])]
    if sorted(page_ids) != sorted(folio_of):
        errors.append(
            f"metadata/pages.jsonl holds {len(page_ids)} pages, the source {len(folio_of)}"
        )
    # the folios are the ones the pages lie on, no fewer and no more (review 7454c2f9 finding 5: an invented folio with
    # a recounted total passed); a spanning page's other folios are its own
    # every folio a spanning page lies on is required too, not only allowed (review d66fcb6d finding 2: `fRos`'s second
    # folio could be dropped)
    spanned = {
        folio
        for page_id in folio_of
        if page_id in SPANNING_PAGES
        for folio, *_ in SPANNING_PAGES[page_id]
    }
    required = set(folio_of.values()) | spanned
    folio_ids = {str(r.get("folio_id")) for r in tables.get("folios", [])}
    if not required <= folio_ids:
        errors.append(
            f"metadata/folios.jsonl lacks folios the pages lie on: {sorted(required - folio_ids)[:5]}"
        )
    invented = folio_ids - required
    if invented:
        errors.append(f"metadata/folios.jsonl holds folios no page lies on: {sorted(invented)[:5]}")
    quires = {f"q{settings['Q']}" for _, settings in headers if "Q" in settings}
    if {str(r.get("quire_id")) for r in tables.get("quires", [])} != quires:
        errors.append(
            f"metadata/quires.jsonl is not the {len(quires)} quires the source's headers name"
        )
    # each quire's contents are its pages' (B-114, AV12 F1: every membership and count erased passed): the pages are
    # those whose headers give its `$Q`, the folios they lie on (a spanning page's every folio), and the lines and
    # sections the pages table gives those pages, which are themselves checked against the source above and below
    pages_by_id = {str(r.get("page_id")): r for r in tables.get("pages", [])}
    for row in tables.get("quires", []):
        quire_id = str(row.get("quire_id"))
        members = [page_id for page_id, settings in headers if f"q{settings.get('Q')}" == quire_id]
        quire_folios = {folio_of[p] for p in members} | {
            folio for p in members if p in SPANNING_PAGES for folio, *_ in SPANNING_PAGES[p]
        }
        member_rows = [pages_by_id.get(p, {}) for p in members]
        quire_expected = {
            "folio_ids": sorted(quire_folios, key=folio_key),
            "folio_count": len(quire_folios),
            "page_count": len(members),
            "total_lines": sum(_number(r.get("line_count")) for r in member_rows),
            "sections": sorted(
                {
                    str((r.get("section") or {}).get("value"))
                    for r in member_rows
                    if (r.get("section") or {}).get("value")
                }
            ),
        }
        for name, value in quire_expected.items():
            if row.get(name) != value:
                errors.append(
                    f"quire {quire_id}: {name} is {row.get(name)!r}, its pages give {value!r}"
                )
    # the report's provenance and totals are the source's and the tables' (B-109, AV11 F2)
    import hashlib

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    hash_value = str(report.get("source_hash", ""))
    # the whole digest or its first SOURCE_VERSION_DIGITS characters, as the builder writes it; never a shorter prefix
    # (B-115: one character passed a prefix check)
    if hash_value not in (digest, digest[:SOURCE_VERSION_DIGITS]):
        errors.append(f"metadata report source_hash {hash_value!r} is not the source's SHA-256")
    totals: dict[str, object] = {
        "total_pages": len(tables.get("pages", [])),
        "total_folios": len(tables.get("folios", [])),
        "total_quires": len(tables.get("quires", [])),
        "total_bifolia": len(tables.get("bifolia", [])),
        "incomplete_bifolia": sum(
            1 for r in tables.get("bifolia", []) if r.get("is_complete") is False
        ),
    }
    # and every other summary the report gives, counted from the tables as the builder counts them (review 7454c2f9
    # finding 4: total_lines, total_labels, complete_quires and pages_by_hand went unchecked)
    pages_rows = tables.get("pages", [])

    def counts(values: Iterable[str]) -> dict[str, int]:
        counted: dict[str, int] = {}
        for value in values:
            counted[value] = counted.get(value, 0) + 1
        return counted

    totals.update(
        {
            "pages_with_text": sum(1 for r in pages_rows if r.get("has_text") is True),
            "pages_by_section": counts(
                str((r.get("section") or {}).get("value") or "unknown") for r in pages_rows
            ),
            "pages_by_language": counts(
                str(r.get("currier_language") or "unknown") for r in pages_rows
            ),
            "pages_by_hand": counts(str(r.get("hand") or "unknown") for r in pages_rows),
            "foldout_folios": sum(
                1 for r in tables.get("folios", []) if r.get("is_foldout") is True
            ),
            "missing_folios": sum(
                1 for r in tables.get("folios", []) if r.get("is_missing") is True
            ),
            "complete_quires": sum(
                1 for r in tables.get("quires", []) if r.get("is_complete") is True
            ),
            "total_lines": sum(_number(r.get("line_count")) for r in pages_rows),
            "total_labels": sum(_number(r.get("label_count")) for r in pages_rows),
            "page_orders": sorted({str(r.get("order")) for r in tables.get("page_orders", [])}),
        }
    )
    for name, value in totals.items():
        if report.get(name) != value:
            errors.append(
                f"metadata report {name} is {report.get(name)!r}, the tables give {value}"
            )
    errors.extend(_check_page_canvases(tables, report))
    # the warnings are the parser's for the source, and the loci and pages reported as not emitted are the ones its
    # warnings reject; a warning about a line emitted all the same rejects nothing (review 69aa93cc finding 2: CD's `<->`
    # warning was refused)
    _, rejected, parser_warnings = _source_loci(str(source), _file_version(source))
    if list(report.get("warnings") or []) != [f"parser: {w}" for w in parser_warnings]:
        errors.append("metadata report warnings are not the parser's for the source")
    if list(report.get("reported_loci") or []) != list(rejected):
        errors.append(
            f"metadata report reported_loci {report.get('reported_loci')!r} are not the loci the parser rejected"
        )
    # exactly the pages the parser rejected, as it names them, in its order: an id a warning merely mentions (an
    # emitted locus's) is not a rejected page (B-112, review 52a893a1 finding 2)
    rejected_pages = list(_rejected_pages(str(source), _file_version(source)))
    if list(report.get("reported_pages") or []) != rejected_pages:
        errors.append(
            f"metadata report reported_pages {report.get('reported_pages')!r} are not the pages the parser rejected"
            f" {rejected_pages[:5]!r}"
        )
    seen = set()
    on_sheets: list[str] = []
    for row in tables.get("bifolia", []):
        key = (str(row.get("quire_id", ""))[1:], str(row.get("bifolio_number")))
        seen.add(key)
        pages = groups.get(key)
        # the lists exactly, each member once and in order (review caac4571 finding 1: a repeated leaf in a list)
        if pages is None or list(row.get("page_ids") or []) != sorted(pages, key=page_order_key):
            errors.append(
                f"bifolio {row.get('bifolio_id')} is not the pages the source puts on {key}"
            )
            continue
        if row.get("quire_id") != f"q{key[0]}":
            errors.append(
                f"bifolio {row.get('bifolio_id')} is in q{key[0]}, not {row.get('quire_id')}"
            )
        folios = sorted({folio_of[p] for p in pages}, key=folio_key)
        listed = list(row.get("folio_ids") or [])
        on_sheets.extend(listed)
        if listed != folios or row.get("is_complete") is not (len(folios) == 2):
            errors.append(
                f"bifolio {row.get('bifolio_id')} lists {listed}, its pages lie on {folios}"
            )
    repeated_leaves = sorted({f for f in on_sheets if on_sheets.count(f) > 1})
    if repeated_leaves:
        errors.append(f"leaves on more than one sheet: {repeated_leaves[:5]}")
    if set(groups) - seen:
        errors.append(
            f"bifolia the source defines and the table lacks: {sorted(set(groups) - seen)[:5]}"
        )
    return errors


def check_loss_accounting(records: list[dict], report: dict[str, Any]) -> list[str]:
    """Every source locus is a row or reported: recomputed from the source, and as reported."""
    errors = []
    missing = [name for name in ACCOUNTING_FIELDS if name not in report]
    if missing:
        errors.append(f"Build report carries no loss accounting (missing {missing})")
    for name in ("unaccounted_loci", "unexpected_loci", "unaccounted_pages"):
        if report.get(name):
            errors.append(f"Build report {name}: {len(report[name])}, first {report[name][:5]}")
    source = resolve_source(report.get("source_file", ""))
    if source is None:
        return errors + ["Loss accounting: the source file cannot be found to recount it"]
    reported = report.get("reported_loci", [])
    if not isinstance(reported, list) or not all(isinstance(x, str) for x in reported):
        errors.append(f"Build report reported_loci is not a list of locus ids: {reported!r}")
        reported = []
    # Page headers the parser reported (optional: reports from before item 1.1 have none).
    reported_pages = report.get("reported_pages", [])
    if not isinstance(reported_pages, list) or not all(isinstance(x, str) for x in reported_pages):
        errors.append(f"Build report reported_pages is not a list of page ids: {reported_pages!r}")
        reported_pages = []
    held = {str(r.get("page_id", "")) for r in records} | {
        str(p) for p in report.get("page_ids_without_lines", [])
    }
    accepted = _accepted_pages(str(source), _file_version(source))
    result = account(
        census_source(source),
        emitted_loci=[r.get("line_id", "") for r in records],
        # one entry per page header the parser accepts whose page the build holds (it has rows, or the report lists it
        # as a page without lines), so a header the source repeats is accounted for once per occurrence (review
        # 8f69a2eb finding 1); and every page the build holds that the source does not, so `account` reports it as
        # unexpected (review cbb8806f finding 1: an invented page without lines passed)
        emitted_pages=[page_id for page_id, _ in accepted if page_id in held]
        + sorted(held - {page_id for page_id, _ in accepted}),
        reported_loci=reported,
        reported_pages=reported_pages,
    )
    for problem in result.problems():
        errors.append(f"Loss accounting against {source.name}: {problem}")
    # the lines starting with `<` that are neither a locus nor a page header, as the census counts them (B-100, AV11 F5)
    unrecognized = list(census_source(source).unrecognized)
    if (
        "unrecognized_source_lines" in report
        and report["unrecognized_source_lines"] != unrecognized
    ):
        errors.append(
            f"Build report unrecognized_source_lines is {report['unrecognized_source_lines']!r}, the census gives "
            f"{unrecognized}"
        )
    recounted = {
        "source_loci": result.source_loci,
        "source_page_headers": result.source_pages,
        "loci_emitted": result.loci_emitted,
        "loci_reported": result.loci_reported,
    }
    for name, value in recounted.items():
        if name in report and report[name] != value:
            errors.append(f"Build report {name} is {report[name]!r}, the recount gives {value}")
    if "reported_loci" in report and report.get("loci_reported") != len(reported):
        errors.append(
            f"Build report loci_reported is {report.get('loci_reported')!r} but it lists "
            f"{len(reported)} reported_loci"
        )
    return errors


def check_schema(records: list[dict]) -> list[str]:
    """Every row conforms to schemas/transcription_lines.schema.json."""
    valid, errors = validate_transcription_lines(records)
    return [] if valid else [f"Schema: {e}" for e in errors]


def check_text_clean_correspondence(records: list[dict]) -> list[str]:
    """text_clean is the current cleaning function applied to text (item 1.6 redefines it)."""
    return [
        f"{r.get('line_id', '?')}: text_clean is not clean_text_for_analysis(text)"
        for r in records
        if r.get("text_clean") != clean_text_for_analysis(r.get("text", ""))
    ]


def _limited(errors: list[str], what: str, limit: int = 5) -> list[str]:
    if len(errors) <= limit:
        return errors
    return errors[:limit] + [f"  ... and {len(errors) - limit} more {what} errors"]


def validate_outputs(output_dir: Path) -> tuple[bool, list[str]]:
    """
    Run all validation checks on output directory.

    Returns:
        (success, list of error messages)
    """
    all_errors: list[str] = []

    jsonl_path = output_dir / "eva_lines.jsonl"
    report_path = output_dir / "eva_lines_build_report.json"

    # Check files exist
    if not jsonl_path.exists():
        return False, [f"JSONL file not found: {jsonl_path}"]

    # Load records
    print(f"Loading {jsonl_path}...")
    records = load_jsonl(jsonl_path)
    print(f"  Loaded {len(records)} records")

    # Required fields (v0.2.0 schema)
    required_fields = [
        "page_id",
        "line_number",
        "line_index",  # NEW in v0.2.0
        "line_id",
        "text",
        "text_clean",
        "line_type",
        "has_uncertain",
        "has_illegible",
        "has_alternatives",
        "has_high_ascii",  # NEW in v0.2.0
        "source",
        "source_version",
        "text_raw",  # the structured layer, item 1.2
        "locus_type",
        "source_line",
        *MARKUP_FIELDS,
    ]

    # Run checks
    print("\nRunning validation checks...")

    print("  [1/12] Required fields...")
    errors = check_required_fields(records, required_fields)
    if errors:
        all_errors.extend(errors[:ERRORS_SHOWN])  # Limit output
        if errors[ERRORS_SHOWN:]:
            all_errors.append(f"  ... and {len(errors[ERRORS_SHOWN:])} more field errors")

    print("  [2/12] line_index sequential...")
    errors = check_line_index_sequential(records)
    all_errors.extend(errors)

    print("  [3/12] @NNN; preservation...")
    errors = check_high_ascii_preservation(records)
    all_errors.extend(errors)

    print("  [4/12] has_high_ascii consistency...")
    errors = check_has_high_ascii_field(records)
    if errors:
        all_errors.extend(errors[:ERRORS_SHOWN])
        if errors[ERRORS_SHOWN:]:
            all_errors.append(f"  ... and {len(errors[ERRORS_SHOWN:])} more has_high_ascii errors")

    print("  [5/12] Build report...")
    errors = check_build_report(report_path)
    all_errors.extend(errors)

    print("  [6/12] Schema...")
    all_errors.extend(_limited(check_schema(records), "schema"))

    report: dict[str, Any] = load_build_report(report_path) if report_path.exists() else {}
    print("  [7/12] Rows against the build report...")
    all_errors.extend(check_rows_against_report(records, report))

    print("  [8/12] Loss accounting...")
    all_errors.extend(check_loss_accounting(records, report))

    print("  [9/12] text_clean correspondence...")
    all_errors.extend(_limited(check_text_clean_correspondence(records), "text_clean"))

    print("  [10/12] Structured layer against the source...")
    all_errors.extend(_limited(check_structured_layer(records, report), "structured layer"))

    print("  [11/12] Provenance, page metadata, profile, flags and order against the source...")
    all_errors.extend(_limited(check_against_source(records, report), "source"))

    print("  [12/12] The files the release manifest lists, and the mismatch index...")
    all_errors.extend(check_manifest_files(output_dir, records))
    all_errors.extend(_limited(check_mismatch_index(output_dir), "mismatch index"))
    all_errors.extend(_limited(check_metadata(output_dir), "metadata"))
    all_errors.extend(_limited(check_words(output_dir), "words"))

    return len(all_errors) == 0, all_errors


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Phase 1 output artifacts match current code/schema"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory containing output artifacts (default: ./output)",
    )
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print("VCAT Phase 1 Output Validator")
    print(f"{'=' * 60}")
    print(f"Output directory: {args.output_dir.absolute()}")

    success, errors = validate_outputs(args.output_dir)

    print()
    if success:
        print(f"{GREEN}✓ All validation checks passed{RESET}")
        return 0
    else:
        print(f"{RED}✗ Validation failed with {len(errors)} error(s):{RESET}")
        for error in errors:
            print(f"  {RED}•{RESET} {error}")
        print()
        print(f"{YELLOW}Run the builder to regenerate outputs:{RESET}")
        print("  python -m builders.build_eva_lines")
        return 1


if __name__ == "__main__":
    sys.exit(main())
