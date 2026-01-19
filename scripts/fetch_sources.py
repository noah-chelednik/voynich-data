#!/usr/bin/env python3
"""
Fetch and verify VCAT source files.

This script downloads the required transcription files and verifies their
SHA256 hashes match expected values. It fails hard if verification fails.

Usage:
    python scripts/fetch_sources.py

The script is idempotent: if files already exist and verify correctly,
it does nothing. If files are missing or corrupted, it fetches fresh copies.
"""

import hashlib
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# =============================================================================
# SOURCE DEFINITIONS
# =============================================================================

# The expected hash will be determined after first successful download.
# For now, we'll compute and display the hash, then you can lock it.
SOURCES = {
    "ZL3b-n.txt": {
        "url": "https://www.voynich.nu/data/ZL3b-n.txt",
        # Hash verified 2026-01-18
        "sha256": "bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc",
        "description": "Zandbergen-Landini EVA transcription v3b",
    },
}

CACHE_DIR = Path(__file__).parent.parent / "data_sources" / "cache"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def verify_file(filepath: Path, expected_hash: str) -> bool:
    """Verify a file's SHA256 hash matches expected value."""
    if not filepath.exists():
        return False
    if expected_hash is None:
        return True  # Skip verification if hash not yet known
    actual_hash = compute_sha256(filepath)
    return actual_hash == expected_hash


def fetch_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination."""
    print(f"  Downloading from {url}...")
    try:
        # Use a proper user-agent to avoid 406 errors
        request = Request(url)
        request.add_header("User-Agent", "VCAT/0.2.1 (Voynich Computational Analysis Toolkit)")
        with urlopen(request) as response:
            dest.write_bytes(response.read())
        return True
    except URLError as e:
        print(f"  ERROR: Failed to download: {e}")
        return False


def main():
    print("=" * 60)
    print("VCAT Source Acquisition and Verification")
    print("=" * 60)
    print()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True

    for filename, info in SOURCES.items():
        filepath = CACHE_DIR / filename
        expected_hash = info["sha256"]

        print(f"Checking {filename}...")
        if expected_hash:
            print(f"  Expected SHA256: {expected_hash[:16]}...")
        else:
            print("  Expected SHA256: (will compute on download)")

        # If file exists and hash matches (or no hash requirement), we're done
        if filepath.exists():
            actual_hash = compute_sha256(filepath)
            if expected_hash and actual_hash == expected_hash:
                print("  ✓ File exists and hash matches")
                print(f"  SHA256: {actual_hash}")
                continue
            elif expected_hash:
                print("  ⚠ File exists but hash mismatch!")
                print(f"    Expected: {expected_hash[:16]}...")
                print(f"    Actual:   {actual_hash[:16]}...")
                filepath.unlink()
            else:
                # No expected hash, file exists
                print("  ✓ File exists")
                print(f"  SHA256: {actual_hash}")
                print("  NOTE: Lock this hash in fetch_sources.py for reproducibility")
                continue

        # File doesn't exist or was deleted, fetch it
        if not fetch_file(info["url"], filepath):
            print(f"  ✗ FAILED to fetch {filename}")
            all_ok = False
            continue

        # Compute and display hash
        actual_hash = compute_sha256(filepath)

        if expected_hash:
            if actual_hash == expected_hash:
                print("  ✓ Downloaded and verified")
                print(f"  SHA256: {actual_hash}")
            else:
                print("  ✗ VERIFICATION FAILED after download!")
                print(f"    Expected: {expected_hash}")
                print(f"    Actual:   {actual_hash}")
                all_ok = False
        else:
            print("  ✓ Downloaded successfully")
            print(f"  SHA256: {actual_hash}")
            print("  NOTE: Lock this hash in fetch_sources.py for reproducibility")

    print()
    print("=" * 60)
    if all_ok:
        print("✓ All sources verified successfully")
        return 0
    else:
        print("✗ Source verification FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
