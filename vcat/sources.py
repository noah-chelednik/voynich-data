"""The cached sources VCAT builds from, as `data_sources/sources.yaml` records them (roadmap item 1.9, D8).

`sources.yaml` lists every file in `data_sources/cache/` with its upstream URL, SHA-256, upstream version and license. This module reads it, so a builder, the verifier (`vcat-verify`) and the tests use one record:

- `cached_sources()`: the records, in file order;
- `license_statement()`: the upstream's license statement and the tables of files it covers; `not_cached_sources()`: the
  sources pinned but not cached (S12);
- `pinned_sha256(path)`: the SHA-256 the record of a cached file pins, or None for a file it does not list;
- `repo_relative(path)`: a path as a build report records it, relative to the repository when it lies inside it, so no
  report names a local checkout (B-070).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = ROOT / "data_sources" / "sources.yaml"

# The fields every cached source's record carries (the ROADMAP's "URL + SHA-256 + upstream version", and its license).
REQUIRED_FIELDS = (
    "id",
    "file",
    "name",
    "url",
    "sha256",
    "upstream_version",
    "license",
    "license_basis",
    "license_verified",
    "redistributed",
    "listed_at",
)

# How a record's `upstream_version` is read: from the file's header (its version line, verbatim), or, for a file whose
# header carries none, from voynich.nu's table that lists the file (`version_from: listing`; S12).
VERSION_FROM = ("header", "listing")

# How a cached file's bytes are read. IVTFF files are ASCII (IVTFF 2.0, section 5.1); every cached file is ASCII or
# UTF-8 except LSI, whose few bytes above 127 are Latin-1 (measured at S13, DECISIONS Q63), so its record says so.
ENCODINGS = ("utf-8", "latin-1")


@dataclass(frozen=True)
class CachedSource:
    """One cached source file, as `sources.yaml` records it."""

    id: str
    file: str
    name: str
    url: str
    sha256: str
    upstream_version: str
    license: str
    license_basis: str
    license_verified: bool
    redistributed: bool
    listed_at: str
    version_from: str = "header"
    encoding: str = "utf-8"

    @property
    def path(self) -> Path:
        return ROOT / self.file

    def actual_sha256(self) -> str | None:
        """The SHA-256 of the cached file, or None when it is missing."""
        return sha256_of(self.path) if self.path.is_file() else None


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_sources(path: Path = SOURCES_YAML) -> dict[str, Any]:
    """The parsed `sources.yaml`."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cached"), list):
        raise ValueError(f"{path}: expected a mapping with a 'cached' list")
    return data


def cached_sources(path: Path = SOURCES_YAML) -> list[CachedSource]:
    """Every cached source's record, in file order. A record missing a required field is an error."""
    records = []
    for entry in load_sources(path)["cached"]:
        missing = [name for name in REQUIRED_FIELDS if name not in entry]
        if missing:
            raise ValueError(f"{path}: source {entry.get('id')!r} lacks {missing}")
        if not isinstance(entry["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", entry["sha256"]
        ):
            # a null or empty pin would let the fetch script install any bytes (reach e85b7f33 gap 3)
            raise ValueError(
                f"{path}: source {entry.get('id')!r} pins no SHA-256: {entry['sha256']!r}"
            )
        for flag in ("license_verified", "redistributed"):
            if not isinstance(entry[flag], bool):
                # a quoted "false" is truthy: a verdict must be a Boolean (B-092)
                raise ValueError(
                    f"{path}: source {entry.get('id')!r} has {flag} {entry[flag]!r}, not true or false"
                )
        version_from = entry.get("version_from", "header")
        if version_from not in VERSION_FROM:
            raise ValueError(
                f"{path}: source {entry.get('id')!r} has version_from {version_from!r}"
            )
        encoding = entry.get("encoding", "utf-8")
        if encoding not in ENCODINGS:
            raise ValueError(f"{path}: source {entry.get('id')!r} has encoding {encoding!r}")
        records.append(
            CachedSource(
                **{name: entry[name] for name in REQUIRED_FIELDS},
                version_from=version_from,
                encoding=encoding,
            )
        )
    # One record per source and per file: a second record could replace the first unseen (review 729a5385 finding 1)
    for field_name in ("id", "file"):
        values = [getattr(r, field_name) for r in records]
        repeated = sorted({v for v in values if values.count(v) > 1})
        if repeated:
            raise ValueError(f"{path}: {field_name} listed more than once: {repeated}")
    return records


def license_statement(path: Path = SOURCES_YAML) -> dict[str, Any]:
    """The upstream's license statement as `sources.yaml` records it: its page, the date it was read, the quote, and the
    tables of files it covers (S12)."""
    statement = load_sources(path).get("license_statement")
    if not isinstance(statement, dict) or not {"url", "read", "quote", "tables"} <= set(statement):
        raise ValueError(f"{path}: expected a license_statement with url, read, quote and tables")
    return statement


def not_cached_sources(path: Path = SOURCES_YAML) -> list[dict[str, Any]]:
    """The sources pinned by URL and SHA-256 but not cached, each with its reason (S12, DECISIONS Q61)."""
    return list(load_sources(path).get("not_cached") or [])


def require_licensed(source_path: str | Path) -> None:
    """Refuse a registered source whose license is not a verified CC0-1.0 verdict: a builder calls this before it reads a
    source, so a source whose license is unclear is kept out of every built output (S12; reach e85b7f33 gap 2).

    A source is the registered one when it has the record's file name, is the same file on disk (a symbolic or hard link
    to it), or has the record's bytes (a copy): the verdict cannot depend on how a caller names the file (review 3eacd8a0
    finding 2). A file that is none of these (a test's synthetic input) is not a registered source and passes.
    """
    path = Path(source_path)

    def refuse(what: str) -> None:
        raise PermissionError(
            f"{path.name} is {what}; a source whose license is not a verified CC0-1.0 verdict, or a "
            "source pinned but not cached, reaches no dataset"
        )

    # What the file is decides before what it is called (review 0fcd9966 finding 1): a cached source by identity or
    # bytes, then a pinned-not-cached one by its bytes; only then, for a file that is neither, the names. A pinned file
    # has no copy in the cache, so no cache path is spelled out here (B-088).
    pinned = not_cached_sources()
    source = _by_identity(path)
    if source is None and path.is_file():
        digest = sha256_of(path)
        entry = next((e for e in pinned if e.get("sha256") == digest), None)
        if entry is not None:
            refuse(f"{entry['id']}, pinned but not cached")
    if source is None:
        source = next((s for s in cached_sources() if Path(s.file).name == path.name), None)
    if source is None:
        entry = next((e for e in pinned if Path(str(e.get("url", ""))).name == path.name), None)
        if entry is not None:
            refuse(f"{entry['id']}, pinned but not cached")
        return
    if not (source.license_verified and source.license == "CC0-1.0"):
        refuse(f"{source.id}: license {source.license!r}, verified {source.license_verified}")


def nonconforming_lines(source_path: str | Path) -> dict[int, str]:
    """The lines of a cached file that break IVTFF itself, as its record lists them (line number to reported id): the
    parser reports them, and the suite requires its rejections to be exactly these (S13). Empty for any other file.
    """
    source = _registered(source_path)
    if source is None:
        return {}
    entry = next(e for e in load_sources()["cached"] if e["id"] == source.id)
    return {int(item["line"]): str(item["id"]) for item in entry.get("nonconforming") or []}


def _by_identity(path: Path) -> CachedSource | None:
    """The cached source a file is by what it is: the same file on disk (a symbolic or hard link), else the same bytes (a
    copy). None for a missing file or any other."""
    if not path.is_file():
        return None
    sources = cached_sources()
    for source in sources:
        if source.path.exists() and os.path.samefile(path, source.path):
            return source
    digest = sha256_of(path)
    return next((source for source in sources if source.sha256 == digest), None)


def _registered(source_path: str | Path) -> CachedSource | None:
    """The cached source a path is: by what it is (`_by_identity`), and only for a file that is no cached source's, by its
    name. So what the registry says of a file cannot depend on how a caller names it (review 3eacd8a0 finding 2, reach
    8e09e8e7 gap 1), and a copy named after another source is still itself (review 0fcd9966 finding 1).
    """
    path = Path(source_path)
    found = _by_identity(path)
    if found is not None:
        return found
    return next(
        (source for source in cached_sources() if Path(source.file).name == path.name), None
    )


def registered_source(source_path: str | Path) -> CachedSource | None:
    """The cached source a file is (`_registered`: by identity, bytes, then name), or None."""
    return _registered(source_path)


def source_encoding(source_path: str | Path) -> str:
    """The encoding the registry records for a cached file (`_registered`); UTF-8 for any other file."""
    source = _registered(source_path)
    return source.encoding if source else "utf-8"


def source_file(source_id: str) -> Path:
    """The cached file `sources.yaml` records for a source id (ZL, IT, ...), relative to the repository: the one place a
    builder's default source comes from (AB2 F3, B-081)."""
    for source in cached_sources():
        if source.id == source_id:
            return Path(source.file)
    raise KeyError(f"no cached source {source_id!r} in {SOURCES_YAML}")


def pinned_sha256(source_path: str | Path) -> str | None:
    """The SHA-256 `sources.yaml` pins for this cached file (matched by file name), or None if it lists no such file."""
    name = Path(source_path).name
    for source in cached_sources():
        if Path(source.file).name == name:
            return source.sha256
    return None


def repo_relative(path: str | Path) -> str:
    """The path relative to the repository, POSIX style, when it lies inside it; otherwise the absolute path."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        # Outside the repository: the absolute path, so no reader depends on the caller's working
        # directory (review cc2c2127 finding 3)
        return str(resolved)
