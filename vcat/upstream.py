"""Upstream tracking (roadmap item 2.1): whether voynich.nu still serves the bytes VCAT pinned, and what changed if not.

- `check_upstream` fetches every cached source the registry marks `url_fetched` from its URL and compares the bytes'
  SHA-256 with the pinned one: `unchanged`, `changed` (with the locus diff against the cached file) or `unreachable`.
- `locus_diff` compares two IVTFF texts locus by locus: a locus is identified by its page, its number and (in an
  interlinear file) its transcriber; it is `added` or `removed` when only one text holds it, `changed` when both do and
  any byte of its lines differs (identifier, spacing, text, line ending), `moved` when its place among the loci both
  texts hold changed. Every other line is compared as its bytes, in order, within the gap after the locus it follows,
  so a repeated line, a moved line, lines reordered and a line in no encoding are compared too (`other_lines`). Lines
  are cut as the parser cuts them. `identical` is whether the two files are the same bytes, whatever the lists say.

Nothing here writes into the repository or the cache: a changed upstream file is reported, never adopted (adopting a
new upstream version is a reviewed change: a new pin in `data_sources/sources.yaml`, a rebuild, an erratum if needed).
"""

from __future__ import annotations

import difflib
import hashlib
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from parsers import IVTFFParser
from vcat.sources import cached_sources, load_sources

Key = tuple[str, int, str]


@dataclass
class LocusDiff:
    """The loci of a new text against an old one, each list sorted by key."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    other_lines_added: int = 0
    other_lines_removed: int = 0
    identical: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "moved": self.moved,
            "other_lines_added": self.other_lines_added,
            "other_lines_removed": self.other_lines_removed,
            "identical": self.identical,
        }


#: A line as the parser cuts it (`IVTFFParser.parse_file`): its bytes and its terminator, CR LF, LF or CR
LINE = re.compile(rb"([^\r\n]*)(\r\n|\n|\r|$)")
TERMINATOR = re.compile(r"\r\n|\n|\r")


def lines_of(data: bytes) -> list[bytes]:
    """The file's lines, each with its terminator, as bytes: nothing decoded, nothing normalised."""
    return [m.group(0) for m in LINE.finditer(data) if m.group(0)]


def _loci(
    data: bytes, encoding: str
) -> tuple[dict[Key, tuple[str, bytes]], dict[Key | None, list[bytes]], list[Key]]:
    """The loci of an IVTFF file by key, each with its identifier as written and the exact bytes of its lines (the
    identifier line and any wrapped continuation, terminators included); every other line, in order, in the gap after
    the locus it follows; and the loci's keys in file order."""
    lines = lines_of(data)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "source.txt"
        path.write_bytes(data)
        parser = IVTFFParser()
        loci: dict[Key, tuple[str, bytes]] = {}
        order: list[Key] = []
        owner: dict[int, Key] = {}
        for page in parser.parse_file(path, encoding=encoding):
            for locus in page.loci:
                key = (locus.page_id, locus.locus_number, locus.transcriber or "")
                if key in loci:
                    raise ValueError(f"two loci with the key {key}: the diff would lose one")
                ident = f"{locus.page_id}.{locus.number_text or locus.locus_number}"
                if locus.transcriber:
                    ident += f";{locus.transcriber}"
                span = range(
                    locus.source_line - 1,
                    locus.source_line + len(TERMINATOR.findall(locus.text_raw)),
                )
                owner.update(dict.fromkeys(span, key))
                order.append(key)
                loci[key] = (ident, b"".join(lines[i] for i in span))
    # every line outside a parsed locus (page headers, comments, a line the parser reports instead of reading as a
    # locus, whatever its encoding), kept in order in the gap after the locus it follows (None before the first): a
    # repeated line, a line moved to another gap and lines reordered within one gap are all seen (reach 966f955a gap
    # 1; reviews 5af7b31a and bfd4e0ad, finding 1 each)
    other: dict[Key | None, list[bytes]] = {}
    previous: Key | None = None
    for i, line in enumerate(lines):
        if i in owner:
            previous = owner[i]
        else:
            other.setdefault(previous, []).append(line)
    return loci, other, order


def locus_diff(old: bytes, new: bytes, encoding: str = "utf-8") -> LocusDiff:
    """The loci added, removed, changed (any byte of their lines) and moved from `old` to `new`, the other lines added
    and removed, and whether the files are the same bytes."""
    before, before_other, before_order = _loci(old, encoding)
    after, after_other, after_order = _loci(new, encoding)
    common = before.keys() & after.keys()
    # the loci both hold that lie outside the longest common runs of their order moved (review 5af7b31a finding 1)
    old_seq = [k for k in before_order if k in common]
    new_seq = [k for k in after_order if k in common]
    kept: set[Key] = set()
    for block in difflib.SequenceMatcher(
        None, old_seq, new_seq, autojunk=False
    ).get_matching_blocks():
        kept.update(old_seq[block.a : block.a + block.size])
    # each gap's lines compared in order: a line outside the gap's longest common run is removed (old) or added (new)
    added_lines = removed_lines = 0
    for gap in before_other.keys() | after_other.keys():
        old_gap, new_gap = before_other.get(gap, []), after_other.get(gap, [])
        matcher = difflib.SequenceMatcher(None, old_gap, new_gap, autojunk=False)
        common_lines = sum(block.size for block in matcher.get_matching_blocks())
        removed_lines += len(old_gap) - common_lines
        added_lines += len(new_gap) - common_lines
    return LocusDiff(
        added=[after[k][0] for k in sorted(after.keys() - before.keys())],
        removed=[before[k][0] for k in sorted(before.keys() - after.keys())],
        changed=[after[k][0] for k in sorted(common) if before[k][1] != after[k][1]],
        moved=[after[k][0] for k in sorted(common - kept)],
        other_lines_added=added_lines,
        other_lines_removed=removed_lines,
        identical=old == new,
    )


def fetch(url: str, timeout: int = 60) -> bytes:
    """The bytes the URL serves now (the only network call of this module)."""
    request = Request(url, headers={"User-Agent": "vcat-upstream-check"})
    with urlopen(
        request, timeout=timeout
    ) as response:  # noqa: S310 - the registry's own https URLs
        data: bytes = response.read()
    return data


def check_upstream(fetcher: Callable[[str], bytes] = fetch) -> list[dict[str, Any]]:
    """Every fetched source's state upstream: its id, URL, pinned and served SHA-256, status, and (when changed) the
    locus diff from the cached file to the served one."""
    # every cached source states whether it is fetched, as a Boolean; none fetched is no check at all (audit
    # 20261021-vcat F1: a registry without the flag checked nothing and exited 0)
    entries = load_sources()["cached"]
    unstated = [e.get("id") for e in entries if not isinstance(e.get("url_fetched"), bool)]
    if unstated:
        raise ValueError(f"cached sources without a Boolean url_fetched: {unstated}")
    fetched = {entry["id"] for entry in entries if entry["url_fetched"]}
    if not fetched:
        raise ValueError(
            "no cached source is marked url_fetched: there is nothing to check upstream"
        )
    results: list[dict[str, Any]] = []
    for source in cached_sources():
        if source.id not in fetched:
            continue
        row: dict[str, Any] = {
            "id": source.id,
            "url": source.url,
            "upstream_version": source.upstream_version,
            "pinned_sha256": source.sha256,
        }
        try:
            data = fetcher(source.url)
        except (
            Exception
        ) as error:  # noqa: BLE001 - every failure is reported as unreachable, with its reason
            row.update(status="unreachable", error=f"{type(error).__name__}: {error}")
            results.append(row)
            continue
        served = hashlib.sha256(data).hexdigest()
        row["served_sha256"] = served
        row["bytes"] = len(data)
        if served == source.sha256:
            row["status"] = "unchanged"
        else:
            row["status"] = "changed"
            try:
                row["diff"] = locus_diff(source.path.read_bytes(), data, source.encoding).as_dict()
            except (
                Exception
            ) as error:  # noqa: BLE001 - a changed file the parser cannot read is still reported
                row["diff_error"] = f"{type(error).__name__}: {error}"
        results.append(row)
    return results
