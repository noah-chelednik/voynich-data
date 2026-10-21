#!/usr/bin/env python3
"""
Fetch and verify VCAT source files.

It fetches each source data_sources/sources.yaml marks url_fetched (every cached
source since S12) that is missing from data_sources/cache/, and checks every
such file against its pinned SHA-256. It fails if a check fails.

Usage:
    python scripts/fetch_sources.py

The script is idempotent: a present file with the pinned hash is left alone. A
present file with another hash is reported and left in place (the cache is
never edited); a missing one is downloaded to a temporary file beside it and
moved into the cache only when it has the pinned hash, so a failed download
leaves the cache as it was.
"""

import hashlib
import os
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# =============================================================================
# SOURCE DEFINITIONS
# =============================================================================

# The sources to fetch are the records of data_sources/sources.yaml marked url_fetched: true, each with
# its URL and pinned SHA-256 (D8: one record of the sources).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vcat.sources import cached_sources, load_sources  # noqa: E402

_FETCHED = {entry["id"] for entry in load_sources()["cached"] if entry.get("url_fetched")}
SOURCES = {
    Path(source.file).name: {
        "url": source.url,
        "sha256": source.sha256,
        "description": source.name,
        # where under the cache it goes: LSI, not ASCII, sits in latin-1/ (S13)
        "path": Path(source.file).relative_to("data_sources/cache").as_posix(),
    }
    for source in cached_sources()
    if source.id in _FETCHED
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
    except (URLError, HTTPException, OSError) as e:  # a refused, failed or truncated download
        print(f"  ERROR: Failed to download: {e}")
        return False


def install(url: str, filepath: Path, expected_hash: str) -> bool:
    """Download `url` into a temporary file of this run's own beside `filepath`, and move it in only once its SHA-256 is
    the pinned one. A shared name would let an overlapping run replace the bytes between the hash and the move (review
    3eacd8a0 finding 1); the temporary file is removed on every other outcome, an exception included, so a failed or
    interrupted download leaves the cache as it was (review 0ba7d188 finding 1)."""
    handle, name = tempfile.mkstemp(
        dir=filepath.parent, prefix=f".{filepath.name}.", suffix=".part"
    )
    os.close(handle)
    partial = Path(name)
    try:
        if not fetch_file(url, partial):
            print(f"  ✗ FAILED to fetch {filepath.name}")
            return False
        actual_hash = compute_sha256(partial)
        if (
            actual_hash != expected_hash
        ):  # every record pins one (the registry rejects a record that does not)
            print("  ✗ VERIFICATION FAILED after download; nothing was written to the cache")
            print(f"    Expected: {expected_hash}")
            print(f"    Actual:   {actual_hash}")
            return False
        partial.replace(filepath)
        print("  ✓ Downloaded and verified")
        print(f"  SHA256: {actual_hash}")
        return True
    finally:
        partial.unlink(missing_ok=True)  # gone already when it was moved in


def main():
    print("=" * 60)
    print("VCAT Source Acquisition and Verification")
    print("=" * 60)
    print()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True

    for filename, info in SOURCES.items():
        filepath = CACHE_DIR / info.get("path", filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
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
                # The cached file is evidence and is never removed: report it and stop
                print("  ✗ File exists but its SHA-256 is not the pinned one; left in place")
                print(f"    Expected: {expected_hash}")
                print(f"    Actual:   {actual_hash}")
                all_ok = False
                continue
            else:
                # No expected hash, file exists
                print("  ✓ File exists")
                print(f"  SHA256: {actual_hash}")
                print("  NOTE: Lock this hash in fetch_sources.py for reproducibility")
                continue

        # File doesn't exist or was deleted: fetch, verify and install it
        if not install(info["url"], filepath, expected_hash):
            all_ok = False

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
