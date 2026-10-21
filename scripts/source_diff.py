#!/usr/bin/env python3
"""The loci added, removed and changed between two IVTFF files (roadmap item 2.1: each release's source diff report).

    python scripts/source_diff.py OLD NEW [--encoding utf-8] [--json]

A locus is identified by its page, its number and (in an interlinear file) its transcriber; it is changed when its
lines differ in any byte, moved when its place changed (`vcat.upstream.locus_diff`). Exit 0 when the files are the same
bytes, 1 when they differ, 2 when a file cannot be compared (unreadable, or refused: a repeated locus key), the reason
on stderr, so a refusal never reads as a difference (B-124).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vcat.upstream import locus_diff  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--json", action="store_true", help="print the diff as JSON")
    args = parser.parse_args(argv)
    try:
        diff = locus_diff(args.old.read_bytes(), args.new.read_bytes(), args.encoding).as_dict()
    except (
        OSError,
        ValueError,
    ) as error:  # a file that cannot be read or is refused is no comparison (B-124)
        print(f"source_diff: cannot compare: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(diff, indent=2))
    else:
        for kind in ("added", "removed", "changed", "moved"):
            shown = f" ({', '.join(diff[kind][:20])})" if diff[kind] else ""
            print(f"{kind}: {len(diff[kind])}{shown}")
        print(
            f"other lines added: {diff['other_lines_added']}, removed: {diff['other_lines_removed']}"
        )
        print("identical" if diff["identical"] else "the files differ")
    # the files' bytes decide, whatever the lists say: a difference no list names still exits 1 (review 5af7b31a)
    return 0 if diff["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
