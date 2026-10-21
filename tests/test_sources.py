"""
The sources and their paperwork (roadmap item 1.9, D8): `data_sources/sources.yaml` against the cache, the checksums, the
file headers, the verification receipts, and the license each dataset card states. Every expectation is read from the
files at test time; no count is hand-written (principle 2).
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

import pytest
import yaml

from data_sources.verify_sources import main as verify_main
from data_sources.verify_sources import read_checksums, render_report, verify_cache
from vcat.loss_accounting import CACHE_DIR
from vcat.sources import (
    ROOT,
    cached_sources,
    license_statement,
    load_sources,
    not_cached_sources,
    pinned_sha256,
    sha256_of,
)

SOURCES = load_sources()
RECORDS = cached_sources()


def card_front_matter(card: str) -> dict:
    text = (ROOT / card / "README.md").read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert match, card
    return yaml.safe_load(match.group(1))


def test_every_cached_file_has_one_record_and_every_record_a_file():
    # every file anywhere under the cache (S13: a file not in the format's ASCII sits in a directory named for its
    # encoding, LSI in latin-1/)
    files = sorted(p.relative_to(CACHE_DIR).as_posix() for p in CACHE_DIR.rglob("*") if p.is_file())
    recorded = [record.path.relative_to(CACHE_DIR).as_posix() for record in RECORDS]
    assert sorted(recorded) == files
    assert len({r.id for r in RECORDS}) == len(RECORDS)
    for record in RECORDS:
        expected = CACHE_DIR if record.encoding == "utf-8" else CACHE_DIR / record.encoding
        assert record.path.parent == expected, record.file


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_each_record_pins_its_file(record):
    """URL, SHA-256 and upstream version for every source (D8): the hash is the file's, the version is its header's."""
    assert record.url.startswith("https://"), record.url
    assert record.sha256 == sha256_of(record.path)
    assert pinned_sha256(record.path) == record.sha256
    lines = record.path.read_text(encoding="utf-8", errors="replace").splitlines()
    # the preamble: every line before the first page header (reach e85b7f33 gap 1)
    head = list(itertools.takewhile(lambda line: not line.startswith("<"), lines))
    assert head[0].startswith("#=IVTFF ")
    comments = [line[1:].strip() for line in head if line.startswith("#")]
    if record.version_from == "listing":
        # No version line in the header (only the IVTFF line), so the version is voynich.nu's table's, which the
        # file name carries (S12)
        assert comments == [head[0][1:].strip()], head
        assert re.fullmatch(r"v\. [0-9][a-z]", record.upstream_version), record.upstream_version
        assert record.upstream_version.removeprefix("v. ") in Path(record.file).name
    else:
        # the version line verbatim, after the comment mark (reach b09d5b4b gap 2: not a fragment of a line)
        assert record.version_from == "header"
        assert record.upstream_version in comments, head


def test_checksums_file_agrees_with_the_records():
    assert read_checksums() == {r.path.relative_to(CACHE_DIR).as_posix(): r.sha256 for r in RECORDS}


VOYNICH_NU = "https://www.voynich.nu/"


def test_every_source_comes_from_voynich_nu():
    """Every cached or pinned source is a voynich.nu file (the only upstream for transliterations the roadmap names)."""
    for url in [r.url for r in RECORDS] + [e["url"] for e in not_cached_sources()]:
        assert url.startswith(VOYNICH_NU + "data/"), url


def test_the_license_statement_is_quoted_from_its_source():
    """The upstream statement, read at voynich.nu on a recorded date, is quoted verbatim in the provenance document,
    with the tables of files it covers (S12)."""
    statement = license_statement()
    assert statement["url"] == VOYNICH_NU + "roadmap.html"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", statement["read"])
    assert "CC0" in statement["quote"] and "here, here and here" in statement["quote"]
    document = (ROOT / "docs/SOURCES_LICENSE.md").read_text(encoding="utf-8")
    assert f"> {statement['quote']}" in document.splitlines()
    assert statement["tables"] and all(t.startswith(VOYNICH_NU) for t in statement["tables"])
    for table in statement["tables"]:
        assert f"- {table}" in document.splitlines()


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_each_source_has_a_license_verdict(record):
    """Each cached source's license is a verdict: the file is linked from a table the statement covers, so it is CC0-1.0,
    and the basis says so (S12). A source the statement does not cover would be marked unverified instead.
    """
    assert record.license_basis.strip()
    assert record.redistributed is True  # the file is committed in data_sources/cache/
    if record.listed_at in license_statement()["tables"]:
        assert record.license == "CC0-1.0" and record.license_verified is True
        assert record.listed_at in record.license_basis and "CC0" in record.license_basis
    else:
        assert record.license_verified is False


def test_only_verified_cc0_sources_reach_a_dataset():
    """A source whose license is unclear is cached and pinned but kept out of every built output (S12)."""
    licensed = {r.id for r in RECORDS if r.license_verified and r.license == "CC0-1.0"}
    for dataset in SOURCES["datasets"]:
        assert set(dataset["sources"]) <= licensed, dataset["name"]


def test_pinned_sources_that_are_not_cached():
    """Each source pinned but not cached has its URL, SHA-256, version, table, license and reason, and is not in the
    cache under its name or another record's id (DECISIONS Q61)."""
    cached_ids = {r.id for r in RECORDS}
    cached_files = {p.name for p in CACHE_DIR.rglob("*") if p.is_file()}
    pinned = not_cached_sources()
    assert len({e["id"] for e in pinned}) == len(pinned)
    for entry in pinned:
        assert entry["id"] not in cached_ids
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), entry["id"]
        assert entry["sha256"] not in {r.sha256 for r in RECORDS}
        assert entry["url"].rsplit("/", 1)[1] not in cached_files
        assert entry["upstream_version"] and entry["reason"].strip()
        assert entry["listed_at"] in license_statement()["tables"]
        assert entry["license"] == "CC0-1.0"


def _fetch_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fetch_sources", ROOT / "scripts/fetch_sources.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_cached_source_is_fetchable():
    """`scripts/fetch_sources.py` fetches every cached source from its record (S12): none is cached by hand only."""
    assert set(_fetch_module().SOURCES) == {Path(r.file).name for r in RECORDS}


@pytest.mark.parametrize("good", [True, False], ids=["pinned bytes", "other bytes"])
def test_a_fetch_writes_the_cache_only_with_the_pinned_bytes(
    tmp_path: Path, monkeypatch, good: bool
):
    """A missing file is downloaded beside the cache and moved in only when it has the pinned SHA-256; other bytes leave
    the cache as it was and fail the run."""
    fetch = _fetch_module()
    record = RECORDS[0]
    name = Path(record.file).name
    monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(fetch, "SOURCES", {name: fetch.SOURCES[name]})
    payload = record.path.read_bytes() if good else b"#=IVTFF Eva- 2.0\n"

    def download(url, dest):
        assert url == record.url and dest.parent == tmp_path and dest.name != name
        dest.write_bytes(payload)
        return True

    monkeypatch.setattr(fetch, "fetch_file", download)
    assert fetch.main() == (0 if good else 1)
    assert sorted(p.name for p in tmp_path.iterdir()) == ([name] if good else [])
    if good:
        assert sha256_of(tmp_path / name) == record.sha256


def test_the_receipts_are_a_fresh_verification(tmp_path: Path):
    """`vcat-verify` writes the machine receipt and renders the human one from it; the committed pair is what it writes
    now, apart from the date (B-064)."""
    assert verify_main(["--reports-dir", str(tmp_path)]) == 0
    fresh = json.loads((tmp_path / "source_verification.json").read_text())
    committed = json.loads((ROOT / "reports/source_verification.json").read_text())
    for receipt in (fresh, committed):
        receipt["_metadata"].pop("verification_date")
    assert committed == fresh
    assert committed["_metadata"]["all_pass"] is True
    on_disk = json.loads((ROOT / "reports/source_verification.json").read_text())
    assert (ROOT / "reports/source_verification_report.md").read_text(
        encoding="utf-8"
    ) == render_report(on_disk)


def test_the_verifier_fails_on_a_changed_file(tmp_path: Path, monkeypatch):
    """A cached file whose bytes are not the pinned ones fails verification (the negative control of the receipt)."""
    record = RECORDS[0]
    changed = tmp_path / Path(record.file).name
    changed.write_bytes(record.path.read_bytes() + b"# edited\n")
    monkeypatch.setattr(
        type(record),
        "path",
        property(lambda self: changed if self.id == record.id else ROOT / self.file),
    )
    results = verify_cache()
    assert results[record.id]["is_success"] is False
    assert results["_metadata"]["all_pass"] is False


def expected_card_license(dataset: dict) -> str:
    licenses = {r.id: r.license for r in RECORDS}
    used = [licenses[s] for s in dataset["sources"]]
    if any(lic != "CC0-1.0" for lic in used):
        return "other"
    return "cc-by-4.0" if dataset["vcat_annotations"] else "cc0-1.0"


@pytest.mark.parametrize("dataset", SOURCES["datasets"], ids=lambda d: d["name"])
def test_each_card_states_the_license_its_sources_allow(dataset: dict):
    """Data CC0 where upstream permits, VCAT annotations CC-BY-4.0, otherwise per source (roadmap item 1.9)."""
    meta = card_front_matter(dataset["card"])
    assert meta["license"] == expected_card_license(dataset)
    if meta["license"] == "other":
        assert meta.get("license_name") == "per-source"
    for source in dataset["sources"]:
        record = next(r for r in RECORDS if r.id == source)
        # The used_by lists and the datasets section agree
        assert dataset["name"] in SOURCES_USED_BY[record.id], (source, dataset["name"])


SOURCES_USED_BY = {entry["id"]: entry["used_by"] for entry in SOURCES["cached"]}


def test_used_by_lists_name_only_datasets():
    """Each source's used_by names exactly the datasets whose sources list it, both ways (reach b09d5b4b gap 4)."""
    names = {d["name"] for d in SOURCES["datasets"]}
    for source, used in SOURCES_USED_BY.items():
        assert set(used) <= names, source
        for name in used:
            assert source in next(d for d in SOURCES["datasets"] if d["name"] == name)["sources"]
    for dataset in SOURCES["datasets"]:
        for source in dataset["sources"]:
            assert dataset["name"] in SOURCES_USED_BY[source], (source, dataset["name"])


@pytest.mark.parametrize("dataset", SOURCES["datasets"], ids=lambda d: d["name"])
def test_each_card_has_known_limitations_and_no_complete_claim(dataset: dict):
    """Honest cards (D8): a "Known Limitations" section, and no claim of a complete transcription."""
    text = (ROOT / dataset["card"] / "README.md").read_text(encoding="utf-8")
    assert re.search(r"^## Known Limitations$", text, re.M)
    assert not re.search(r"\bcomplete (EVA )?transcription", text, re.I)


@pytest.mark.parametrize("dataset", SOURCES["datasets"], ids=lambda d: d["name"])
def test_card_directories_hold_no_copy_of_the_data(dataset: dict):
    """The data a card describes is the build's output; a copy beside the card would go stale (it did: 0.2.3)."""
    for path in (ROOT / dataset["card"]).rglob("*"):  # nested too (reach b09d5b4b gap 5)
        assert path.suffix not in {".jsonl", ".parquet", ".json"}, path.name


@pytest.mark.parametrize("relative", ["tests/conftest.py", "tests/test_parsers.py"])
def test_fixture_paths_are_the_shared_cache(relative: str):
    """Two fixtures spell the cache path out (a reviewer proof, AP F02, evaluates the expression with only `Path` in
    scope); each must still name the file under the shared `CACHE_DIR`, so moving the cache cannot leave them behind
    (AT1 F6, B-067)."""
    import ast

    source = ROOT / relative
    tree = ast.parse(source.read_text())
    fixture = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "zl_file"
    )
    assignment = next(
        n
        for n in ast.walk(fixture)
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "path" for t in n.targets)
    )
    resolved = eval(  # noqa: S307 - the expression is this repository's own fixture
        compile(ast.Expression(body=assignment.value), str(source), "eval"),
        {"Path": Path, "__file__": str(source)},
    )
    assert resolved.resolve() == (CACHE_DIR / "ZL3b-n.txt").resolve()


def test_tests_name_the_cache_through_the_shared_constant():
    """Apart from those two fixtures, no test module builds the cache path itself (AT1 F6, B-067)."""
    allowed = {"conftest.py", "test_parsers.py", "test_sources.py"}
    tests = ROOT / "tests"
    # nested modules too (reach b09d5b4b gap 6); reviewer proofs (tests/regressions, tests/test_audit_*) are copied unchanged
    for path in sorted(tests.rglob("*.py")):
        relative = path.relative_to(tests)
        if (
            relative.as_posix() in allowed
            or relative.parts[0] == "regressions"
            or path.name.startswith("test_audit_")
        ):
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"""["']data_sources["']\s*\)?\s*/\s*["']cache["']|["']data_sources/cache""", text
        ), path.name


LICENSE_NAMES = {
    "cc0-1.0": "CC0 1.0 Universal (CC0-1.0)",
    "cc-by-4.0": "Creative Commons Attribution 4.0 International (CC-BY-4.0)",
    "other": "license per source",
}


@pytest.mark.parametrize("dataset", SOURCES["datasets"], ids=lambda d: d["name"])
def test_each_card_license_file_names_the_card_license(dataset: dict):
    meta = card_front_matter(dataset["card"])
    # and the card's license is the registry's (reach d4385eb4 gap 6)
    assert meta["license"] == expected_card_license(dataset)
    assert meta.get("license_link") == "LICENSE"
    text = (ROOT / dataset["card"] / "LICENSE").read_text(encoding="utf-8")
    assert LICENSE_NAMES[meta["license"]] in text
    assert "research use" not in text.lower() and "research resource" not in text.lower()


def test_license_document_is_the_record():
    """docs/SOURCES_LICENSE.md holds the matrix and the dataset table rendered from sources.yaml and the cards (D8: the
    document said the raw files are not redistributed; they are)."""
    from builders.cards import dataset_license_table, license_matrix
    from tests.test_paperwork import rendered_region

    text = (ROOT / "docs/SOURCES_LICENSE.md").read_text(encoding="utf-8")
    # each table is the whole of its marked region, so an added row fails (reach e85b7f33 gap 4)
    assert rendered_region(text, "license:matrix") == license_matrix()
    assert rendered_region(text, "license:datasets") == dataset_license_table()
    assert "not the original source files" not in text


@pytest.mark.parametrize("dataset", SOURCES["datasets"], ids=lambda d: d["name"])
def test_each_card_config_names_a_built_file(dataset: dict):
    """The data files a card's configs name are files the builders write to output/ (docs/PUBLISHING.md)."""
    built = {p.name for p in (ROOT / "output").rglob("*") if p.is_file()}
    configs = card_front_matter(dataset["card"])["configs"]
    paths = [f["path"] for c in configs for f in c["data_files"]]
    assert paths and set(paths) <= built, paths


def test_builder_defaults_come_from_the_registry():
    """The builders' default sources are the files `sources.yaml` records, not spelled-out paths (AB2 F3, B-081)."""
    import importlib
    import inspect

    from vcat.sources import source_file

    # by module name: the package re-exports functions of the same names
    build_eva_lines = importlib.import_module("builders.build_eva_lines")
    build_metadata = importlib.import_module("builders.build_metadata")
    build_mismatch_index = importlib.import_module("builders.build_mismatch_index")

    assert build_metadata.DEFAULT_SOURCE == source_file("ZL")
    dataset = next(d for d in SOURCES["datasets"] if d["name"] == "voynich-transcription-mismatch")
    assert build_mismatch_index.SOURCES == {
        s.lower(): source_file(s).name for s in dataset["sources"]
    }
    assert build_mismatch_index.CACHE_DIR == CACHE_DIR
    assert 'default=source_file("ZL")' in inspect.getsource(build_eva_lines.main)


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_each_source_is_read_in_its_recorded_encoding(record):
    """Every line of a cached file decodes in the encoding its record states; a record says Latin-1 only when some line is
    not UTF-8 (IVTFF files are ASCII, section 5.1; LSI's bytes above 127 are Latin-1, S13)."""
    lines = record.path.read_bytes().splitlines()
    for line in lines:
        line.decode(record.encoding)  # raises when a line is not in the recorded encoding
    not_utf8 = []
    for line in lines:
        try:
            line.decode("utf-8")
        except UnicodeDecodeError:
            not_utf8.append(line)
    assert (record.encoding == "latin-1") == bool(not_utf8), (record.id, len(not_utf8))


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_each_listed_nonconforming_line_is_in_the_source(record):
    """Each line a record lists as breaking IVTFF is that line of the file, a locus line, counted by the census under the
    id given; the parser's rejections are exactly these (tests/test_ivtff_coverage.py)."""
    from vcat.loss_accounting import census_source
    from vcat.sources import nonconforming_lines

    listed = nonconforming_lines(record.path)
    lines = record.path.read_text(encoding=record.encoding).splitlines()
    census = census_source(record.path)
    for number, locus in listed.items():
        assert lines[number - 1].startswith("<"), (record.id, number)
        # the census counts the line under that id, once per listed line (several transcribers' readings share it)
        assert census.loci.count(locus) == list(listed.values()).count(locus), (record.id, locus)
