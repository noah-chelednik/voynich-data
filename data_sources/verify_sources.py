#!/usr/bin/env python3
"""
VCAT Source Verification Script
================================

Phase 0 verification script for VCAT data sources.

This script verifies that all data sources are accessible and match
expected formats BEFORE beginning implementation. It checks:
    - URL accessibility
    - Content type and size
    - IVTFF format structure
    - EVA character presence
    - Transcriber codes (for interlinear files)

Run this script BEFORE implementing any parsers.

Usage:
    python data_sources/verify_sources.py

Output:
    - Console report with pass/fail status for each source
    - JSON results saved to reports/source_verification.json

Example:
    >>> from data_sources.verify_sources import verify_lsi_file
    >>> result = verify_lsi_file("http://www.voynich.nu/data/...")
    >>> result.is_success()
    True
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests


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


def compute_sha256(content: bytes) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Bytes to hash.

    Returns:
        Hexadecimal SHA256 hash string.
    """
    return hashlib.sha256(content).hexdigest()


def fetch_content(url: str, timeout: int = 30) -> tuple[bytes, int, str]:
    """Fetch content from URL.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Tuple of (content_bytes, status_code, content_type).

    Raises:
        requests.exceptions.RequestException: On network errors.
    """
    headers = {"User-Agent": "VCAT-SourceVerifier/1.0 (Voynich Computational Analysis Toolkit)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    content_type = response.headers.get("Content-Type", "unknown")
    return response.content, response.status_code, content_type


def check_ivtff_structure(content: str) -> tuple[bool, bool, int, int]:
    """Check if content looks like IVTFF format.

    Searches for IVTFF page headers and locus identifiers to
    determine if the content is parseable.

    Args:
        content: Text content to check.

    Returns:
        Tuple of (can_parse_pages, can_parse_lines, page_count, line_count).
    """
    # IVTFF page headers look like: <f1r> or ## <f1r>
    page_pattern = r"<f\d+[rv]\d*>"
    # IVTFF line patterns look like: <f1r.P1.1;H> or similar
    line_pattern = r"<f\d+[rv]\d*\.\w+\.\d+[;\w]*>"

    pages = re.findall(page_pattern, content)
    lines = re.findall(line_pattern, content)

    unique_pages = len(set(pages))
    line_count = len(lines)

    can_parse_pages = unique_pages > 0
    can_parse_lines = line_count > 0

    return can_parse_pages, can_parse_lines, unique_pages, line_count


def check_eva_characters(content: str) -> tuple[set[str], set[str]]:
    """Check what EVA characters are present in content.

    Extracts text from IVTFF locus lines and identifies which
    characters are known EVA and which are unknown.

    Args:
        content: IVTFF file content.

    Returns:
        Tuple of (known_chars, unknown_chars) as sets.
    """
    # Basic EVA characters
    EVA_BASIC = set("acdehiklmnopqrsty")
    EVA_RARE = set("fgxjvbuz")
    EVA_ALL = EVA_BASIC | EVA_RARE

    # Extract text content (crude - ignores comments and metadata)
    # Look for text after locators like <f1r.P1.1;H>
    text_pattern = r"<f\d+[rv]\d*\.\w+\.\d+[;\w]*>\s*(.+?)(?=<|$)"
    text_matches = re.findall(text_pattern, content)

    all_text = " ".join(text_matches)
    # Remove common separators and markers
    all_text = re.sub(r"[.\-=,\s\[\]{}!?*@\d<>]", "", all_text.lower())

    chars_found = set(all_text)
    known = chars_found & EVA_ALL
    unknown = chars_found - EVA_ALL

    return known, unknown


def verify_lsi_file(url: str) -> VerificationResult:
    """Verify a Landini-Stolfi Interlinear or similar IVTFF file.

    Fetches the file and checks for IVTFF structure, EVA characters,
    and transcriber codes.

    Args:
        url: URL of the IVTFF file to verify.

    Returns:
        VerificationResult with verification details.
    """
    result = VerificationResult(
        source_name="Landini-Stolfi Interlinear (LSI)",
        url=url,
    )

    try:
        content, status_code, content_type = fetch_content(url)
        result.status_code = status_code
        result.content_type = content_type

        if status_code != 200:
            result.errors.append(f"HTTP {status_code} - not accessible")
            return result

        result.accessible = True
        result.sample_hash = compute_sha256(content)
        result.sample_size = len(content)

        # Decode and check structure
        text = content.decode("utf-8", errors="replace")

        # Check for IVTFF format
        if "#=IVTFF" in text or "EVA" in text.upper()[:1000]:
            result.notes.append("File appears to be in IVTFF/EVA format")

        # Check for page/line structure
        can_pages, can_lines, page_count, line_count = check_ivtff_structure(text)
        result.can_parse_pages = can_pages
        result.can_parse_lines = can_lines
        result.page_count = page_count
        result.line_count = line_count

        if not can_pages:
            result.errors.append("Cannot identify page boundaries")
        if not can_lines:
            result.errors.append("Cannot identify line boundaries")

        # Check EVA characters
        known_chars, unknown_chars = check_eva_characters(text)
        result.notes.append(f"Found {len(known_chars)} known EVA characters")
        if unknown_chars:
            result.warnings.append(
                f"Found {len(unknown_chars)} unknown characters: {unknown_chars}"
            )

        # Check for transcriber codes
        transcribers = set(re.findall(r";([A-Z])\>", text))
        if transcribers:
            result.notes.append(f"Transcriber codes found: {sorted(transcribers)}")
            if "H" in transcribers:
                result.notes.append("Takahashi transcription (H) present")

    except requests.exceptions.RequestException as e:
        result.errors.append(f"Network error: {e}")
    except Exception as e:
        result.errors.append(f"Error: {e}")

    return result


def verify_voynich_nu(url: str) -> VerificationResult:
    """Verify voynich.nu metadata source.

    Checks that the voynich.nu website is accessible and contains
    expected Voynich-related content.

    Args:
        url: URL on voynich.nu to verify.

    Returns:
        VerificationResult with verification details.
    """
    result = VerificationResult(
        source_name="voynich.nu",
        url=url,
    )

    try:
        content, status_code, content_type = fetch_content(url)
        result.status_code = status_code
        result.content_type = content_type

        if status_code != 200:
            result.errors.append(f"HTTP {status_code} - not accessible")
            return result

        result.accessible = True
        result.sample_hash = compute_sha256(content)
        result.sample_size = len(content)

        text = content.decode("utf-8", errors="replace")

        # Check for expected content
        if "voynich" in text.lower():
            result.notes.append("Content appears to be Voynich-related")
        if "transcr" in text.lower() or "transliteration" in text.lower():
            result.notes.append("Transcription/transliteration content found")

    except requests.exceptions.RequestException as e:
        result.errors.append(f"Network error: {e}")
    except Exception as e:
        result.errors.append(f"Error: {e}")

    return result


def verify_stolfi(url: str) -> VerificationResult:
    """Verify Stolfi's UNICAMP page.

    Checks that Jorge Stolfi's Voynich resources at UNICAMP
    are accessible.

    Args:
        url: URL of Stolfi's page to verify.

    Returns:
        VerificationResult with verification details.
    """
    result = VerificationResult(
        source_name="Stolfi UNICAMP",
        url=url,
    )

    try:
        content, status_code, content_type = fetch_content(url)
        result.status_code = status_code
        result.content_type = content_type

        if status_code != 200:
            result.errors.append(f"HTTP {status_code} - not accessible")
            return result

        result.accessible = True
        result.sample_hash = compute_sha256(content)
        result.sample_size = len(content)

        text = content.decode("utf-8", errors="replace")

        # Look for key files
        if "interln" in text.lower() or "concordance" in text.lower():
            result.notes.append("Interlinear/concordance files referenced")
        if "Takahashi" in text or "takahashi" in text.lower():
            result.notes.append("Takahashi transcription referenced")

    except requests.exceptions.RequestException as e:
        result.errors.append(f"Network error: {e}")
    except Exception as e:
        result.errors.append(f"Error: {e}")

    return result


def run_all_verifications() -> dict:
    """Run verification on all configured sources.

    Verifies all primary data sources and returns results
    as a dictionary suitable for JSON serialization.

    Returns:
        Dictionary with results for each source and metadata.
    """
    print("=" * 60)
    print("VCAT Source Verification")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    results: dict = {}

    # 1. Verify LSI file (primary source)
    print("Checking Landini-Stolfi Interlinear file...")
    lsi_result = verify_lsi_file("http://www.voynich.nu/data/beta/LSI_ivtff_0d.txt")
    results["lsi"] = lsi_result.to_dict()
    print_result(lsi_result)

    # 2. Verify voynich.nu
    print("\nChecking voynich.nu...")
    vnu_result = verify_voynich_nu("https://www.voynich.nu/transcr.html")
    results["voynich_nu"] = vnu_result.to_dict()
    print_result(vnu_result)

    # 3. Verify Stolfi's page
    print("\nChecking Stolfi UNICAMP...")
    stolfi_result = verify_stolfi("https://www.ic.unicamp.br/~stolfi/voynich/")
    results["stolfi"] = stolfi_result.to_dict()
    print_result(stolfi_result)

    # 4. Check ZL transcription (if available)
    print("\nChecking Zandbergen-Landini transcription...")
    zl_result = verify_lsi_file("http://www.voynich.nu/data/ivtff/ZL3a-n.txt")
    zl_result.source_name = "Zandbergen-Landini (ZL)"
    results["zl"] = zl_result.to_dict()
    print_result(zl_result)

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_pass = True
    for name, res in results.items():
        status = "✓ PASS" if res["is_success"] else "✗ FAIL"
        if not res["is_success"]:
            all_pass = False
        print(f"{name}: {status}")

    print()
    if all_pass:
        print("All sources verified. Ready to proceed with implementation.")
    else:
        print("WARNING: Some sources failed verification. Review before proceeding.")

    # Add metadata
    results["_metadata"] = {
        "verification_date": datetime.now().isoformat(),
        "all_pass": all_pass,
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


def main() -> None:
    """Main entry point for the verification script."""
    # Ensure reports directory exists
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Run verifications
    results = run_all_verifications()

    # Save results
    output_path = reports_dir / "source_verification.json"
    save_results(results, output_path)

    # Exit with appropriate code
    if results["_metadata"]["all_pass"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
