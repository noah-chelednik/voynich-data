#!/usr/bin/env python3
"""Check the published reference values of data_sources/references.yaml against their pages (roadmap item 2.10).

    python scripts/check_references.py            # the offline copies under docs/reference/
    python scripts/check_references.py --fetch    # the pages on voynich.nu (network)

For each page: its bytes have the pinned SHA-256, and its text holds the page's `method` sentence and every reference's
`quote` verbatim (tags removed, entities decoded, runs of whitespace one space). Exit 0 when all hold, 1 otherwise. Not
part of the suite: the copies are git-ignored (their redistribution rights are not established), like the IVTFF spec.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data_sources" / "references.yaml"


def page_text(data: bytes) -> str:
    """The page's text as the quotes are written: tags removed, entities decoded, whitespace collapsed."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", data.decode("latin-1")))
    return re.sub(r"\s+", " ", text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--fetch", action="store_true", help="read the pages from the site, not the offline copies"
    )
    args = parser.parse_args(argv)
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    failures = 0
    pinned = {page["id"] for page in registry["pages"]}
    for reference in registry["references"]:
        # a quote on no pinned page is confirmed by nothing (reach 7ea91938 gap 4)
        if reference.get("page") not in pinned:
            print(
                f"{reference.get('id', reference.get('quote'))}: its page {reference.get('page')!r} is not pinned"
            )
            failures += 1
    for page in registry["pages"]:
        if args.fetch:
            with urllib.request.urlopen(page["url"], timeout=60) as response:
                data = response.read()
        else:
            path = ROOT / page["file"]
            if not path.is_file():
                print(
                    f"{page['id']}: no offline copy at {page['file']} (run with --fetch, or fetch it there)"
                )
                failures += 1
                continue
            data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != page["sha256"]:
            print(
                f"{page['id']}: SHA-256 {digest} is not the pinned {page['sha256']} (the page changed)"
            )
            failures += 1
        text = page_text(data)
        quotes = [page["method"]] + [
            r["quote"] for r in registry["references"] if r["page"] == page["id"]
        ]
        for quote in quotes:
            # the quote as a whole on the page: neither end inside one of the page's numbers, so a quote cut short
            # ("188,862 3.86" of "188,862 3.862") or begun inside a number confirms nothing (review c5c2dbe8 finding 1)
            if not re.search(r"(?<![\d.,])" + re.escape(quote) + r"(?!\d|[.,]\d)", text):
                print(f"{page['id']}: quote not found: {quote!r}")
                failures += 1
        print(
            f"{page['id']}: {len(quotes)} quotes checked, SHA-256 {'pinned' if digest == page['sha256'] else 'CHANGED'}"
        )
    print("check_references:", "OK" if failures == 0 else f"{failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
