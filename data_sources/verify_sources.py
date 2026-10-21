#!/usr/bin/env python3
"""
VCAT source verification (`vcat-verify`)
========================================

Checks the cached sources against `data_sources/sources.yaml` (roadmap item 1.9, D8, B-064):

    - every file in data_sources/cache/ has a record, and every record a file;
    - each file's SHA-256 is the one its record pins, and data_sources/checksums_all.txt agrees;
    - each file's header carries the upstream version its record states, or, for a file whose header carries no
      version line (`version_from: listing`), its file name carries the version voynich.nu's table lists;
    - each file is IVTFF (its first line is an IVTFF header).

It writes the machine receipt `reports/source_verification.json` and renders the human receipt
`reports/source_verification_report.md` from it, so the two cannot disagree. The exit status is 0 only
when every check passes. No network access is made unless `--online` is given, which also fetches every fetched
source from its pinned voynich.nu URL and checks the served bytes against the pin (`vcat.upstream`, roadmap item 2.1),
recording each result in the receipt.

Usage:
    vcat-verify                      # after pip install -e ., from a checkout
    python -m data_sources.verify_sources [--online]

Example:
    >>> from data_sources.verify_sources import verify_cache
    >>> verify_cache()["_metadata"]["all_pass"]
    True
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class VerificationResult:
    """Result of verifying a single data source.

    Contains all verification information for a source including
    accessibility, content analysis, and any errors or warnings.

    Attributes:
        source_name: Human-readable name of the source.
        url: URL that was verified.
        accessible: Whether the URL was accessible (HTTP 200).
        status_code: HTTP status code received.
        content_type: Content-Type header from response.
        sample_hash: SHA256 hash of the content.
        sample_size: Size of content in bytes.
        can_parse_pages: Whether IVTFF page markers were found.
        can_parse_lines: Whether IVTFF line/locus markers were found.
        page_count: Number of unique pages found.
        line_count: Number of lines/loci found.
        errors: List of error messages (blocking issues).
        warnings: List of warning messages (non-blocking issues).
        notes: List of informational notes.

    Example:
        >>> result = VerificationResult(
        ...     source_name="ZL Transcription",
        ...     url="http://example.com/file.txt"
        ... )
        >>> result.is_success()
        False  # Not yet verified
    """

    source_name: str
    url: str
    accessible: bool = False
    status_code: int | None = None
    content_type: str | None = None
    sample_hash: str | None = None
    sample_size: int | None = None
    can_parse_pages: bool | None = None
    can_parse_lines: bool | None = None
    page_count: int | None = None
    line_count: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def is_success(self) -> bool:
        """Return True if source is usable (accessible with no errors).

        Returns:
            True if source was accessible and has no errors.
        """
        return self.accessible and len(self.errors) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation including computed is_success.
        """
        return {
            "source_name": self.source_name,
            "url": self.url,
            "accessible": self.accessible,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "sample_hash": self.sample_hash,
            "sample_size": self.sample_size,
            "can_parse_pages": self.can_parse_pages,
            "can_parse_lines": self.can_parse_lines,
            "page_count": self.page_count,
            "line_count": self.line_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "notes": self.notes,
            "is_success": self.is_success(),
        }


def run_all_verifications(fetcher: Callable[[str], bytes] | None = None) -> dict:
    """The online check: every source the registry marks fetched, fetched from its pinned URL on voynich.nu and its
    bytes compared with the pinned SHA-256 (`vcat.upstream.check_upstream`, roadmap item 2.1). A source passes only
    when it is served and its bytes are the pinned ones. No other host is contacted (B-087: the Phase 0 reachability
    checks, one of them on a site the roadmap does not fetch from, are gone).

    Returns:
        Per source id its result (as `VerificationResult.to_dict`), and `_metadata` with the date and `all_pass`.
    """
    from vcat.upstream import check_upstream
    from vcat.upstream import fetch as fetch_upstream

    results: dict = {}
    try:
        rows = check_upstream(fetcher or fetch_upstream)
    except (
        Exception
    ) as error:  # noqa: BLE001 - a registry the check cannot read is a failed check, recorded (review be0dc250 finding 1)
        failed = VerificationResult(source_name="registry", url="data_sources/sources.yaml")
        failed.errors.append(f"the upstream check could not run: {type(error).__name__}: {error}")
        results["registry"] = failed.to_dict()
        print_result(failed)
        rows = []
    for row in rows:
        result = VerificationResult(source_name=row["id"], url=row["url"])
        result.accessible = row["status"] != "unreachable"
        result.sample_hash = row.get("served_sha256")
        result.sample_size = row.get("bytes")
        if row["status"] == "unreachable":
            result.errors.append(f"unreachable: {row.get('error')}")
        elif row["status"] == "changed":
            result.errors.append(
                f"the served bytes are not the pinned ones (served {row['served_sha256']}, pinned"
                f" {row['pinned_sha256']})"
            )
        else:
            result.notes.append("served as pinned")
        results[row["id"]] = result.to_dict()
        print_result(result)
    results["_metadata"] = {
        "verification_date": datetime.now().isoformat(),
        "all_pass": all(v["is_success"] for v in results.values()),
    }
    return results


def print_result(result: VerificationResult) -> None:
    """Print a verification result to console.

    Args:
        result: VerificationResult to print.
    """
    status = "✓" if result.is_success() else "✗"
    print(f"  {status} {result.source_name}")
    print(f"    URL: {result.url}")
    print(f"    Status: HTTP {result.status_code}")
    if result.sample_size:
        print(f"    Size: {result.sample_size:,} bytes")
    if result.sample_hash:
        print(f"    SHA256: {result.sample_hash[:16]}...")
    if result.page_count:
        print(f"    Pages found: {result.page_count}")
    if result.line_count:
        print(f"    Lines found: {result.line_count}")
    for note in result.notes:
        print(f"    Note: {note}")
    for warn in result.warnings:
        print(f"    ⚠ Warning: {warn}")
    for err in result.errors:
        print(f"    ✗ Error: {err}")


def save_results(results: dict, output_path: Path) -> None:
    """Save verification results to JSON file.

    Args:
        results: Results dictionary to save.
        output_path: Path to output JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
CHECKSUMS = ROOT / "data_sources" / "checksums_all.txt"
IVTFF_HEADER = re.compile(r"^#=IVTFF ")


def cache_name(path: Path) -> str:
    """A cached file's path relative to data_sources/cache/, as data_sources/checksums_all.txt names it (``ZL3b-n.txt``,
    ``latin-1/LSI_ivtff_0d.txt``), so ``sha256sum -c`` run in the cache checks every file."""
    # The entry's own path, links NOT followed: a symbolic link in the cache is an entry of its own, never its target's
    # (review 094aaa5d finding 1). A file outside the cache (a test's stand-in) is named by its file name.
    entry, cache = Path(os.path.abspath(path)), Path(
        os.path.abspath(ROOT / "data_sources" / "cache")
    )
    return entry.relative_to(cache).as_posix() if entry.is_relative_to(cache) else entry.name


def read_checksums(path: Path = CHECKSUMS) -> dict[str, str]:
    """cache path -> SHA-256, as data_sources/checksums_all.txt lists them (sha256sum format; `cache_name`)."""
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            name = name.strip().lstrip("*")
            # A file listed twice is an error, never resolved by the later line (reach b09d5b4b gap 3)
            if name in sums:
                raise ValueError(f"{path.name} lists {name} more than once")
            sums[name] = digest
    return sums


def verify_cache() -> dict:
    """Check every cached source against data_sources/sources.yaml and checksums_all.txt (offline).

    Returns:
        A receipt: one entry per source id, plus "_metadata" with the date, the mode and all_pass.
    """
    from vcat.sources import cached_sources

    try:
        records = cached_sources()
    except (
        ValueError
    ) as error:  # a malformed registry fails the verification (review 729a5385 finding 1)
        return {
            "_metadata": {
                "verification_date": datetime.now(UTC).isoformat(),
                "mode": "cache",
                "registry_error": str(error),
                "unlisted_cache_files": [],
                "checksums_without_record": [],
                "checksum_file_error": None,
                "all_pass": False,
            }
        }
    try:
        checksums = read_checksums()
        checksum_error = None
    except ValueError as error:  # a duplicated entry fails the verification, it does not stop it
        checksums, checksum_error = {}, str(error)
    results: dict = {}
    listed = {cache_name(r.path) for r in records}
    cache = ROOT / "data_sources" / "cache"
    for source in records:
        errors: list[str] = []
        actual = source.actual_sha256()
        if actual is None:
            errors.append(f"{source.file} is missing")
        else:
            if actual != source.sha256:
                errors.append("SHA-256 is not the one sources.yaml pins")
            if checksums.get(cache_name(source.path)) != actual:
                errors.append("data_sources/checksums_all.txt does not list this SHA-256")
            # the whole preamble, every line before the first page header, not a fixed number of lines (reach e85b7f33
            # gap 1): a version comment anywhere in it is the file's own
            lines = source.path.read_text(encoding="utf-8", errors="replace").splitlines()
            head = lines[
                : next((i for i, line in enumerate(lines) if line.startswith("<")), len(lines))
            ]
            if not head or not IVTFF_HEADER.match(head[0]):
                errors.append("the first line is not an IVTFF header")
            versions = [line[1:].strip() for line in head if line.startswith("#")]
            if source.version_from == "listing":
                # the header carries no version line, so the version is the upstream table's, which the file name
                # also carries (S12)
                if versions[1:]:
                    errors.append(
                        "the header has comment lines; its version is read from them, not the listing"
                    )
                token = source.upstream_version.removeprefix("v. ")
                if not token or token not in Path(source.file).name:
                    errors.append(
                        f"the file name does not carry the listed version {source.upstream_version!r}"
                    )
            elif (
                source.upstream_version not in versions
            ):  # the line verbatim (reach b09d5b4b gap 2)
                errors.append(f"the header does not carry {source.upstream_version!r}")
        results[source.id] = {
            "file": source.file,
            "url": source.url,
            "sha256": actual,
            "upstream_version": source.upstream_version,
            "errors": errors,
            "is_success": not errors,
        }
    # every file anywhere under the cache, by its path there (S13: LSI is under latin-1/)
    unlisted = sorted(
        cache_name(p) for p in cache.rglob("*") if p.is_file() and cache_name(p) not in listed
    )
    stray = sorted(set(checksums) - listed)
    results["_metadata"] = {
        "verification_date": datetime.now(UTC).isoformat(),
        "mode": "cache",
        "unlisted_cache_files": unlisted,
        "checksums_without_record": stray,
        "checksum_file_error": checksum_error,
        "all_pass": all(r["is_success"] for r in results.values())
        and not unlisted
        and not stray
        and not checksum_error,
    }
    return results


def render_report(results: dict) -> str:
    """The human receipt, rendered from the machine receipt (B-064): it states exactly what the JSON says."""
    meta = results["_metadata"]
    lines = [
        "# Source verification receipt",
        "",
        "Rendered by `vcat-verify` from `reports/source_verification.json`; do not edit by hand.",
        "",
        f"- Date: {meta['verification_date']}",
        f"- Mode: {meta['mode']}",
        f"- Result: {'PASS' if meta['all_pass'] else 'FAIL'}",
        "",
        "| source | file | upstream version | SHA-256 | result |",
        "|---|---|---|---|---|",
    ]
    for key, entry in results.items():
        if key.startswith("_") or "file" not in entry:
            continue
        verdict = "pass" if entry["is_success"] else "FAIL: " + "; ".join(entry["errors"])
        lines.append(
            f"| {key} | `{entry['file']}` | {entry['upstream_version']} | `{entry['sha256']}` | {verdict} |"
        )
    for label, names in (
        ("Cache files without a record", meta["unlisted_cache_files"]),
        ("Checksums without a record", meta["checksums_without_record"]),
    ):
        if names:
            lines += ["", f"{label}: " + ", ".join(f"`{n}`" for n in names)]
    if meta.get("registry_error"):
        lines += ["", f"data_sources/sources.yaml: {meta['registry_error']}"]
    if meta.get("checksum_file_error"):
        lines += ["", f"Checksums file: {meta['checksum_file_error']}"]
    online = {k: v for k, v in results.items() if not k.startswith("_") and "file" not in v}
    if online:
        lines += ["", "## Upstream: served bytes against the pins (`--online`)", ""]
        for key, entry in online.items():
            lines.append(
                f"- {key}: {'pass' if entry['is_success'] else 'FAIL'} ({entry.get('url')})"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Verify the cached sources, write both receipts, and return 0 only when every check passes."""
    import argparse

    arg_parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1] if __doc__ else None)
    arg_parser.add_argument(
        "--online",
        action="store_true",
        help="also check every fetched source's served bytes against its pin (network access, voynich.nu only)",
    )
    arg_parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    args = arg_parser.parse_args(argv)

    results = verify_cache()
    if args.online:
        online = run_all_verifications()
        online.pop("_metadata")
        results.update({f"online_{k}": v for k, v in online.items()})
        results["_metadata"]["mode"] = "cache+online"
        # The online checks add to the cache verification, never replace its verdict (review cc2c2127 finding 1)
        results["_metadata"]["all_pass"] = bool(results["_metadata"]["all_pass"]) and all(
            v["is_success"] for k, v in results.items() if k.startswith("online_")
        )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    save_results(results, args.reports_dir / "source_verification.json")
    (args.reports_dir / "source_verification_report.md").write_text(
        render_report(results), encoding="utf-8"
    )
    for key, entry in results.items():
        if not key.startswith("_"):
            print(f"{key}: {'PASS' if entry['is_success'] else 'FAIL'} {entry.get('errors') or ''}")
    print("ALL PASS" if results["_metadata"]["all_pass"] else "VERIFICATION FAILED")
    return 0 if results["_metadata"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
