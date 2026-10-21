"""Links from each page to Yale's images of it (roadmap item 2.4): the page-to-canvas mapping to the Beinecke Library's IIIF
manifest of MS 408. Links only: VCAT never copies or serves an image.

The manifest is not committed. `data_sources/iiif/yale-2002046-canvases.json` holds what the links need from it, each
canvas's id, label and image service, in manifest order, with the SHA-256 of the manifest they were read from
(`python -m vcat.iiif --fetch`, from the manifest URL the roadmap names, or `--from-file` for a saved copy).

A page lies on every canvas whose label names its folio and side: `1r` is `f1r`; `69v and 70r` shows `f69v`, `f70r1` and
`f70r2`; a panel lies on the canvas labelled with its side; `fRos`, drawn over f85 verso and f86 recto, on the canvas that
names both. A side the label says is shown `(part)` gives the page's link `coverage: part` (the page, or one of its panels,
may lie on that canvas only in part); otherwise `coverage: whole`. The rule reads Yale's labels and nothing else: whether a
particular panel is on a particular part is not decided here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_URL = "https://collections.library.yale.edu/manifests/2002046"
CANVASES_JSON = ROOT / "data_sources" / "iiif" / "yale-2002046-canvases.json"

#: The fields of a canvas in the extract, in order
CANVAS_FIELDS = ("index", "canvas_id", "label", "image_service")
#: The fields of a page's link, in the order the published table has them
LINK_FIELDS = ("page_id", "canvas_index", "canvas_id", "canvas_label", "coverage", "image_service")
#: What each field of a link holds, as the card's field table states it
LINK_FIELD_DESCRIPTIONS = {
    "page_id": ("str", "The page, as in `pages`"),
    "canvas_index": ("int", "The canvas's position in Yale's manifest, from 1"),
    "canvas_id": ("str", "The canvas's IIIF id in Yale's manifest"),
    "canvas_label": ("str", "Yale's label for the canvas, as written"),
    "coverage": (
        "str",
        "`whole` when the label names the page's side, `part` when it says that side is shown in part",
    ),
    "image_service": (
        "str",
        "The canvas image's IIIF Image API service (a link; VCAT copies no image)",
    ),
}
#: A side named in a label: folio number, `r` or `v`, and whether the label says it is shown in part
_SIDE = re.compile(r"(\d+)([rv])((?:\s*\(part\))?)")
#: Label notes that name no side
_NOTE = re.compile(r"\((?:part of [^)]*|foldout)\)")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _part(index: int, value: Any, kind: type, what: str) -> Any:
    """A part of canvas `index` of the kind it must be (a non-empty list for a list), else an error."""
    if not isinstance(value, kind) or (kind is list and not value):
        raise ValueError(f"canvas {index}: {what} is {value!r}")
    return value


def extract_canvases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Each canvas of a IIIF Presentation 3 manifest, in order: its position from 1, id, label (the first value of the
    first language) and the image service of its first painting annotation. A canvas whose id, label or image service is
    not a non-empty string is an error, so a malformed manifest never becomes an extract (review f6b7579c finding 1).
    """
    canvases = []
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError(f"the manifest's items are {type(items).__name__}, not a list")
    for index, canvas in enumerate(items, start=1):
        # each part read only after its shape is checked: a string where a list belongs would otherwise be indexed
        # (review d0d64b4c finding 1: `{"none": "1r"}` became the label `1`)
        _part(index, canvas, dict, "the canvas")
        labels = _part(index, canvas.get("label"), dict, "label")
        label = _part(index, next(iter(labels.values()), None), list, "label value")[0]
        annotations = _part(
            index,
            _part(index, canvas.get("items"), list, "annotation pages")[0],
            dict,
            "annotation page",
        )
        annotation = _part(
            index,
            _part(index, annotations.get("items"), list, "annotations")[0],
            dict,
            "annotation",
        )
        body = _part(index, annotation.get("body"), dict, "annotation body")
        service = _part(
            index,
            _part(index, body.get("service"), list, "image service")[0],
            dict,
            "image service",
        )
        entry = {
            "index": index,
            "canvas_id": canvas.get("id"),
            "label": label,
            "image_service": service.get("id") or service.get("@id"),
        }
        for name in ("canvas_id", "label", "image_service"):
            if not isinstance(entry[name], str) or not entry[name].strip():
                raise ValueError(f"canvas {index}: {name} is {entry[name]!r}")
        canvases.append(entry)
    return canvases


def load_canvases(path: Path = CANVASES_JSON) -> dict[str, Any]:
    """The extract: the manifest's URL and SHA-256, when it was read, and its canvases. A canvas missing a field, a
    position out of order, or canvases that are not the ones the extract's own hash names is an error.
    """
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("manifest", "manifest_sha256", "read_at", "canvases_sha256", "canvases"):
        if key not in data:
            raise ValueError(f"{path}: lacks {key!r}")
    for position, canvas in enumerate(data["canvases"], start=1):
        if tuple(canvas) != CANVAS_FIELDS or canvas["index"] != position:
            raise ValueError(f"{path}: canvas {position} is {canvas!r}")
    if hashlib.sha256(canonical(data["canvases"]).encode()).hexdigest() != data["canvases_sha256"]:
        raise ValueError(f"{path}: the canvases are not the ones its canvases_sha256 names")
    return data


def sides_of_label(label: str) -> list[tuple[int, str, bool]]:
    """The sides a canvas label names, in order: (folio number, `recto` or `verso`, shown in part)."""
    text = _NOTE.sub("", label)
    return [
        (int(folio), "recto" if side == "r" else "verso", bool(part))
        for folio, side, part in _SIDE.findall(text)
    ]


def sides_of_page(page_id: str) -> list[tuple[int, str]]:
    """The folio sides a page lies on: its own (`f67r2` is f67 recto), or both of a page drawn across two folios."""
    from parsers.metadata_parser import SPANNING_PAGES

    if page_id in SPANNING_PAGES:
        return [(int(folio[1:]), side) for folio, side in SPANNING_PAGES[page_id]]
    match = re.fullmatch(r"f(\d+)([rv])\d*", page_id)
    if match is None:
        return []
    return [(int(match.group(1)), "recto" if match.group(2) == "r" else "verso")]


def page_links(page_ids: list[str], canvases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every page's link to every canvas its folio sides are on, pages in the order given, canvases in manifest order."""
    named = [(canvas, sides_of_label(canvas["label"])) for canvas in canvases]
    links = []
    for page_id in page_ids:
        sides = sides_of_page(page_id)
        for canvas, on_canvas in named:
            parts = [part for folio, side, part in on_canvas if (folio, side) in sides]
            if not parts:
                continue
            links.append(
                {
                    "page_id": page_id,
                    "canvas_index": canvas["index"],
                    "canvas_id": canvas["canvas_id"],
                    "canvas_label": canvas["label"],
                    "coverage": "part" if any(parts) else "whole",
                    "image_service": canvas["image_service"],
                }
            )
    return links


def write_extract(manifest_bytes: bytes, path: Path = CANVASES_JSON) -> dict[str, Any]:
    """Write the extract of a manifest's bytes, pinned by their SHA-256. Only Yale's manifest of MS 408 is read: bytes that
    are not a IIIF Presentation 3 manifest with that id, or that hold no canvas, are refused before anything is written
    (review 2e53e1c4 finding 3)."""
    try:
        manifest = json.loads(manifest_bytes)
    except ValueError as error:
        raise ValueError(f"not JSON: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("type") != "Manifest":
        raise ValueError("not a IIIF Presentation 3 manifest")
    if manifest.get("id") != MANIFEST_URL:
        raise ValueError(f"the manifest is {manifest.get('id')!r}, not {MANIFEST_URL}")
    try:
        canvases = extract_canvases(manifest)
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f"a canvas without an id, label or image service: {error!r}") from error
    if not canvases:
        raise ValueError("the manifest holds no canvas")
    data = {
        "manifest": MANIFEST_URL,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "read_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "canvases_sha256": hashlib.sha256(canonical(canvases).encode()).hexdigest(),
        "canvases": canvases,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--fetch", action="store_true", help=f"read the manifest from {MANIFEST_URL}"
    )
    group.add_argument("--from-file", type=Path, help="read a saved copy of the manifest")
    args = parser.parse_args(argv)
    if args.fetch:
        with urllib.request.urlopen(
            MANIFEST_URL, timeout=120
        ) as response:  # noqa: S310 (the roadmap's URL)
            manifest_bytes = response.read()
    else:
        manifest_bytes = args.from_file.read_bytes()
    data = write_extract(manifest_bytes)
    print(f"{len(data['canvases'])} canvases, manifest sha256 {data['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
