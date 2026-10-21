"""
The links from each page to Yale's images of it (roadmap item 2.4): the canvases of the Beinecke Library's IIIF manifest of
MS 408, as extracted and pinned in `data_sources/iiif/yale-2002046-canvases.json`, and the page-to-canvas links the
metadata dataset publishes (`page_canvases`), read from Yale's labels by the rule `vcat/iiif.py` documents. Links only:
no image is in the repository.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from vcat import iiif

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
EXTRACT = iiif.load_canvases()
CANVASES = EXTRACT["canvases"]
PAGES = [
    json.loads(line)["page_id"]
    for line in (OUTPUT / "metadata" / "pages.jsonl").read_text().splitlines()
]
LINKS = [
    json.loads(line)
    for line in (OUTPUT / "metadata" / "page_canvases.jsonl").read_text().splitlines()
]


def test_the_extract_is_pinned_to_the_manifest_the_roadmap_names():
    assert EXTRACT["manifest"] == "https://collections.library.yale.edu/manifests/2002046"
    # a SHA-256 in hexadecimal, its form checked (a digest's length, not a population count)
    assert re.fullmatch(r"[0-9a-f]{64}", EXTRACT["manifest_sha256"])
    # the roadmap's count of canvases, read from the extract
    assert [c["index"] for c in CANVASES] == list(range(1, len(CANVASES) + 1))
    assert len({c["canvas_id"] for c in CANVASES}) == len(CANVASES)
    for canvas in CANVASES:
        assert canvas["canvas_id"].startswith(
            "https://collections.library.yale.edu/manifests/oid/2002046/canvas/"
        )
        assert canvas["image_service"].startswith("https://collections.library.yale.edu/iiif/2/")


def test_the_extract_refuses_an_edited_canvas(tmp_path):
    data = json.loads(iiif.CANVASES_JSON.read_text(encoding="utf-8"))
    data["canvases"][2]["label"] = "2r"
    path = tmp_path / "canvases.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="canvases_sha256"):
        iiif.load_canvases(path)


def test_extract_canvases_reads_a_presentation_3_manifest(tmp_path):
    def canvas(n: int, label: str) -> dict:
        return {
            "id": f"https://example.org/canvas/{n}",
            "type": "Canvas",
            "label": {"none": [label]},
            "items": [
                {"items": [{"body": {"service": [{"@id": f"https://example.org/iiif/{n}"}]}}]}
            ],
        }

    manifest = {
        "id": iiif.MANIFEST_URL,
        "type": "Manifest",
        "items": [canvas(7, "1r"), canvas(9, "69v and 70r")],
    }
    assert iiif.extract_canvases(manifest) == [
        {
            "index": 1,
            "canvas_id": "https://example.org/canvas/7",
            "label": "1r",
            "image_service": "https://example.org/iiif/7",
        },
        {
            "index": 2,
            "canvas_id": "https://example.org/canvas/9",
            "label": "69v and 70r",
            "image_service": "https://example.org/iiif/9",
        },
    ]
    raw = json.dumps(manifest).encode()
    data = iiif.write_extract(raw, tmp_path / "extract.json")
    assert data["manifest_sha256"] == hashlib.sha256(raw).hexdigest()
    assert iiif.load_canvases(tmp_path / "extract.json")["canvases"] == iiif.extract_canvases(
        manifest
    )


@pytest.mark.parametrize(
    ("label", "sides"),
    [
        ("1r", [(1, "recto", False)]),
        ("69v and 70r", [(69, "verso", False), (70, "recto", False)]),
        ("70v (part)", [(70, "verso", True)]),
        (
            "85r (part) 86v (part) (part of 85-86 foldout)",
            [(85, "recto", True), (86, "verso", True)],
        ),
        ("85v and 86r (foldout)", [(85, "verso", False), (86, "recto", False)]),
        ("89v (part) and 90r", [(89, "verso", True), (90, "recto", False)]),
        ("[Front cover]", []),
    ],
)
def test_a_label_names_its_sides(label, sides):
    assert iiif.sides_of_label(label) == sides


def test_every_label_in_the_manifest_is_read():
    """Every canvas label names a side or is one of Yale's bracketed views of the binding."""
    for canvas in CANVASES:
        assert iiif.sides_of_label(canvas["label"]) or canvas["label"].startswith("["), canvas[
            "label"
        ]


def test_the_published_links_are_the_rule_over_the_pages():
    assert LINKS == iiif.page_links(PAGES, CANVASES)
    assert all(tuple(link) == iiif.LINK_FIELDS for link in LINKS)


def test_every_page_has_a_link_and_every_link_names_its_side():
    assert {link["page_id"] for link in LINKS} == set(PAGES)
    for link in LINKS:
        on_page = set(iiif.sides_of_page(link["page_id"]))
        named = [
            (f, s, part)
            for f, s, part in iiif.sides_of_label(link["canvas_label"])
            if (f, s) in on_page
        ]
        assert named, link
        assert link["coverage"] == ("part" if any(part for *_, part in named) else "whole"), link


def test_a_page_links_to_the_canvases_its_folio_sides_are_on():
    by_page: dict[str, list[str]] = {}
    for link in LINKS:
        by_page.setdefault(link["page_id"], []).append(link["canvas_label"])
    assert by_page["f1r"] == ["1r"]
    assert by_page["f67r2"] == ["67r"]
    assert by_page["f70r1"] == ["69v and 70r"]
    assert by_page["fRos"] == ["85v and 86r (foldout)"]
    assert by_page["f90r1"] == ["89v (part) and 90r", "90r"]


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".jp2", ".webp"}


#: The directories of a checkout that are not the repository's content: git's own store, a local environment and the tools'
#: caches. Every other directory is read, hidden ones too (`.github`, `.githooks`; review 2e53e1c4 finding 1)
NOT_CONTENT = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}


def repository_files(root: Path) -> list[Path]:
    """Every file of the repository's tree: all of it, not one directory (reach b7c1ae53 gap 1), hidden directories
    included, but not git's store, a local environment or a cache (`NOT_CONTENT`)."""
    import os

    found = []
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = [d for d in subdirectories if d not in NOT_CONTENT]
        found += [Path(directory) / name for name in files]
    return found


def test_links_are_links_never_images():
    images = [p for p in repository_files(ROOT) if p.suffix.lower() in IMAGE_SUFFIXES]
    assert not images, images
    for link in LINKS:
        assert link["image_service"].startswith("https://collections.library.yale.edu/iiif/2/")


def candidate(tmp_path: Path) -> Path:
    out = tmp_path / "candidate"
    out.mkdir()
    for name in ("eva_lines.jsonl", "eva_lines_build_report.json"):
        shutil.copy2(OUTPUT / name, out / name)
    shutil.copytree(OUTPUT / "metadata", out / "metadata")
    return out


def write_links(out: Path, rows: list[dict]) -> None:
    meta = out / "metadata"
    (meta / "page_canvases.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    pq.write_table(pa.Table.from_pylist(rows), meta / "page_canvases.parquet")


def drop_first(rows):
    return rows[1:]


def change_coverage(rows):
    rows[0]["coverage"] = "part"
    return rows


def change_canvas(rows):
    rows[0]["canvas_id"] = rows[1]["canvas_id"]
    return rows


def drop_page(rows):
    return [r for r in rows if r["page_id"] != "fRos"]


@pytest.mark.parametrize(
    "tamper", [drop_first, change_coverage, change_canvas, drop_page], ids=lambda f: f.__name__
)
@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_both_validators_refuse_changed_links(tmp_path, tamper, validator):
    from validators import validate_phase1_outputs as phase
    from validators import verify_invariants as invariants

    out = candidate(tmp_path)

    def problems():
        if validator == "phase":
            return phase.validate_outputs(out)[1]
        return invariants.verify_all_invariants(out).failures

    assert not problems()
    write_links(out, tamper(copy.deepcopy(LINKS)))
    assert problems()


def test_both_validators_refuse_a_report_naming_another_manifest(tmp_path):
    from validators.validate_phase1_outputs import check_metadata

    out = candidate(tmp_path)
    path = out / "metadata" / "metadata_report.json"
    report = json.loads(path.read_text())
    report["iiif_manifest_sha256"] = "0" * 64
    path.write_text(json.dumps(report), encoding="utf-8")
    assert any("iiif_manifest_sha256" in p for p in check_metadata(out))


def test_the_validators_read_the_extract_vcat_iiif_names():
    """The validators read the canvas extract at the path `vcat.iiif` names, the one object, not a path spelled again
    (B-120): moving the extract in `vcat.iiif` moves what the validators read."""
    from validators import validate_phase1_outputs as phase1

    assert phase1.IIIF_CANVASES is iiif.CANVASES_JSON
