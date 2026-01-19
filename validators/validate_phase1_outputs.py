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
    1. Schema validation: JSONL conforms to schema
    2. Field presence: All required fields exist (including line_index, has_high_ascii)
    3. line_index correctness: Sequential 1..n per page with no gaps
    4. @NNN; preservation: Lines with only @NNN; in raw have non-empty text_clean
    5. Build report completeness: Required fields present
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

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
    at_code_pattern = re.compile(r"@\d+;")

    for rec in records:
        if "has_high_ascii" not in rec:
            errors.append(f"{rec.get('line_id', '?')}: missing has_high_ascii field")
            continue

        raw = rec.get("text", "")
        has_code = bool(at_code_pattern.search(raw))

        if has_code and not rec["has_high_ascii"]:
            errors.append(f"{rec.get('line_id', '?')}: contains @NNN; but has_high_ascii=False")
        elif not has_code and rec["has_high_ascii"]:
            errors.append(f"{rec.get('line_id', '?')}: no @NNN; but has_high_ascii=True")

    return errors


def check_build_report(report_path: Path) -> list[str]:
    """Check that build report has required fields."""
    errors = []

    if not report_path.exists():
        return [f"Build report not found: {report_path}"]

    with open(report_path) as f:
        report = json.load(f)

    required_fields = [
        "source_file",
        "source_hash",
        "build_date",
        "format_version",
        "format_options",
        "text_clean_policy",
        "total_pages",
        "total_lines",
        "lines_with_high_ascii",
    ]

    missing = [f for f in required_fields if f not in report]
    if missing:
        errors.append(f"Build report missing fields: {missing}")

    # Check text_clean_policy is set
    if report.get("text_clean_policy") is None:
        errors.append("Build report: text_clean_policy is None (should be 'lossless_v1')")

    return errors


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
    ]

    # Run checks
    print("\nRunning validation checks...")

    print("  [1/5] Required fields...")
    errors = check_required_fields(records, required_fields)
    if errors:
        all_errors.extend(errors[:5])  # Limit output
        if len(errors) > 5:
            all_errors.append(f"  ... and {len(errors) - 5} more field errors")

    print("  [2/5] line_index sequential...")
    errors = check_line_index_sequential(records)
    all_errors.extend(errors)

    print("  [3/5] @NNN; preservation...")
    errors = check_high_ascii_preservation(records)
    all_errors.extend(errors)

    print("  [4/5] has_high_ascii consistency...")
    errors = check_has_high_ascii_field(records)
    if errors:
        all_errors.extend(errors[:5])
        if len(errors) > 5:
            all_errors.append(f"  ... and {len(errors) - 5} more has_high_ascii errors")

    print("  [5/5] Build report completeness...")
    errors = check_build_report(report_path)
    all_errors.extend(errors)

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
