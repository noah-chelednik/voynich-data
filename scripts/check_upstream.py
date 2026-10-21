#!/usr/bin/env python3
"""Check every fetched source against voynich.nu (roadmap item 2.1).

    python scripts/check_upstream.py [--report report.json] [--markdown report.md]

For each cached source `data_sources/sources.yaml` marks `url_fetched`, fetch its URL and compare the bytes' SHA-256
with the pinned one; for a changed file, the loci added, removed and changed against the cached copy (`vcat.upstream`).
Exit 0 when every source is unchanged, 1 when any changed, 2 when any was unreachable, 3 when both, 4 when the check
itself failed (an exception, reported on stderr). Nothing is
written but the reports asked for: a changed upstream file is reported, never adopted. The scheduled workflow
`.github/workflows/upstream.yml` runs this and opens an issue on exit 1.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# imported here but failing soft: an import that fails is re-raised by main(), inside the wrapper that exits 4, so the
# check's own failure never reads as a change (review 5af7b31a finding 2)
try:
    from vcat.upstream import check_upstream  # noqa: E402
except Exception as _error:  # noqa: BLE001
    _IMPORT_ERROR: Exception | None = _error
    check_upstream = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None


def markdown(results: list[dict], when: str) -> str:
    """The report as an issue body: one row per source, then each changed source's diff."""
    lines = [
        f"# Upstream check, {when}",
        "",
        "| Source | Status | Pinned SHA-256 | Served SHA-256 |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['status']} | `{r['pinned_sha256'][:16]}` | `{r.get('served_sha256', '-')[:16]}` |"
        )
    for r in results:
        if r["status"] == "changed":
            d = r.get("diff")
            lines += ["", f"## {r['id']} changed upstream ({r['url']})", ""]
            if d is None:
                lines.append(f"The served file could not be compared: {r.get('diff_error')}")
                continue
            lines.append(
                f"Loci added: {len(d['added'])}; removed: {len(d['removed'])}; changed: {len(d['changed'])}; "
                f"moved: {len(d['moved'])}; other lines added: {d['other_lines_added']}, "
                f"removed: {d['other_lines_removed']}."
            )
            # the bytes decide, whatever the counts say (review bfd4e0ad finding 1)
            lines.append(
                "The served file differs from the pinned one in its bytes (its SHA-256 above)."
            )
            for kind in ("added", "removed", "changed", "moved"):
                if d[kind]:
                    shown = ", ".join(d[kind][:50]) + (" ..." if len(d[kind]) > 50 else "")
                    lines.append(f"- {kind}: {shown}")
        elif r["status"] == "unreachable":
            lines += ["", f"## {r['id']} unreachable ({r['url']})", "", r.get("error", "")]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--report", type=Path, help="write the results as JSON here")
    parser.add_argument("--markdown", type=Path, help="write the results as Markdown here")
    args = parser.parse_args(argv)
    when = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if check_upstream is None:
        assert _IMPORT_ERROR is not None
        raise _IMPORT_ERROR
    results = check_upstream()
    if args.report:
        args.report.write_text(
            json.dumps({"checked": when, "sources": results}, indent=2) + "\n", encoding="utf-8"
        )
    if args.markdown:
        args.markdown.write_text(markdown(results, when), encoding="utf-8")
    for r in results:
        print(
            f"{r['id']}: {r['status']}"
            + (f" ({r.get('error')})" if r["status"] == "unreachable" else "")
        )
    statuses = {r["status"] for r in results}
    # one code per state, so an unreachable source fails the run even when another changed (reach 966f955a gap 6)
    return (1 if "changed" in statuses else 0) + (2 if "unreachable" in statuses else 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (
        Exception
    ):  # noqa: BLE001 - the check's own failure is its own exit code, never "changed"
        import traceback

        traceback.print_exc()
        sys.exit(4)
