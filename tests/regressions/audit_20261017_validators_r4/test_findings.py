import contextlib
import hashlib
import io
import json
import runpy
import shutil
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from parsers import IVTFFParser
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from vcat import sources
from vcat.loss_accounting import census_source

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def copied_output(tmp_path):
    target = tmp_path / "output"
    shutil.copytree(ROOT / "output", target)
    return target


def accepted(out, checker):
    with contextlib.redirect_stdout(io.StringIO()):
        if checker == "phase":
            return phase.validate_outputs(out)[0]
        return inv.verify_all_invariants(out).passed


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_pair(out, stem, rows):
    blob = "".join(
        json.dumps(
            row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ) + "\n"
        for row in rows
    ).encode()
    (out / (stem + ".jsonl")).write_bytes(blob)
    pq.write_table(pa.Table.from_pylist(rows), out / (stem + ".parquet"))
    return blob


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("page_id", "f999r"),
        ("line_number", 999),
        ("zl_reading", "forged"),
        ("it_reading", "forged"),
        ("zl_locus_type", "&Lz"),
        ("it_locus_type", "&Lz"),
        ("zl_source_line", 1),
        ("it_source_line", 1),
        ("sources_present", []),
    ],
)
def test_f1_rejects_each_false_mismatch_field(
    copied_output, checker, field, value
):
    assert accepted(copied_output, checker)
    rows = read_rows(copied_output / "mismatch_index.jsonl")
    row = next(
        row for row in rows
        if row["zl_text_raw"] is not None
        and row["it_text_raw"] is not None
    )
    assert row[field] != value
    row[field] = value
    write_pair(copied_output, "mismatch_index", rows)
    assert not accepted(copied_output, checker)


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_f2_rejects_orphan_mismatch_artifacts(copied_output, checker):
    assert accepted(copied_output, checker)
    (copied_output / "mismatch_index.jsonl").unlink()
    assert (copied_output / "mismatch_index.parquet").is_file()
    assert (copied_output / "mismatch_report.json").is_file()
    assert not accepted(copied_output, checker)


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_f3_rejects_unreported_source_locus(
    copied_output, checker, tmp_path, monkeypatch
):
    assert accepted(copied_output, checker)
    entries = sources.cached_sources()
    original = next(entry for entry in entries if entry.id == "IT")
    census = census_source(original.path)
    page = census.pages[-1]
    number = max(int(locus.rsplit(":", 1)[1]) for locus in census.loci) + 1
    added_id = f"{page}:{number}"
    assert added_id not in census.loci

    scratch_source = tmp_path / original.path.name
    scratch_source.write_bytes(
        original.path.read_bytes()
        + f"\n<{page}.{number},@X9>    rejected\n".encode()
    )
    digest = hashlib.sha256(scratch_source.read_bytes()).hexdigest()
    changed_entries = [
        replace(entry, file=str(scratch_source), sha256=digest)
        if entry.id == "IT" else entry
        for entry in entries
    ]
    monkeypatch.setattr(
        sources, "cached_sources", lambda: changed_entries
    )

    parser = IVTFFParser()
    list(parser.parse_file(scratch_source))
    assert any(warning.locus_id == added_id for warning in parser.warnings)

    report_path = copied_output / "mismatch_report.json"
    report = json.loads(report_path.read_text())
    report["sources"]["it"]["sha256"] = digest
    assert added_id not in report["sources"]["it"]["reported_loci"]
    report_path.write_text(json.dumps(report))

    phase._source_loci.cache_clear()
    try:
        assert not accepted(copied_output, checker)
    finally:
        phase._source_loci.cache_clear()


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_f4_rejects_false_row_source(copied_output, checker):
    assert accepted(copied_output, checker)
    rows = read_rows(copied_output / "eva_lines.jsonl")
    assert rows[0]["source"] == "zandbergen_landini"
    rows[0]["source"] = "takeshi_takahashi"
    blob = write_pair(copied_output, "eva_lines", rows)
    digest = hashlib.sha256(blob).hexdigest()

    path = copied_output / "release_manifest.json"
    manifest = json.loads(path.read_text())
    for entry in manifest["files"]:
        if entry["name"] == "eva_lines.jsonl":
            entry["sha256"] = digest
    path.write_text(json.dumps(manifest))
    (copied_output / "SHA256SUMS").write_text(
        f"{digest}  eva_lines.jsonl\n"
    )
    assert not accepted(copied_output, checker)


def test_f5_default_source_follows_registry(monkeypatch):
    monkeypatch.setattr(
        sources,
        "cached_sources",
        lambda: [
            SimpleNamespace(
                id="ZL", file="data_sources/cache/ZL-next.txt"
            )
        ],
    )
    namespace = runpy.run_path(
        str(ROOT / "validators" / "verify_invariants.py"),
        run_name="audit_validator_import",
    )
    assert namespace["DEFAULT_SOURCE"] == ROOT / sources.source_file("ZL")


def test_f6_installed_schema_api_has_its_resources(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in (
        "pyproject.toml", "README.md", "LICENSE",
        "MANIFEST.in", "setup.cfg", "setup.py",
    ):
        path = ROOT / name
        if path.is_file():
            shutil.copy2(path, source / name)
    for name in (
        "vcat", "parsers", "builders", "validators",
        "hf", "data_sources", "schemas",
    ):
        shutil.copytree(
            ROOT / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    wheels = tmp_path / "wheels"
    built = subprocess.run(
        [
            sys.executable, "-B", "-m", "pip", "wheel",
            "--no-index", "--no-deps", "--no-build-isolation",
            "--no-cache-dir", "--wheel-dir", str(wheels), str(source),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    wheel, = wheels.glob("*.whl")
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    schema_names = sorted(path.name for path in (ROOT / "schemas").glob("*.json"))
    assert schema_names
    code = (
        "import json, sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "from validators import load_schema; "
        "[load_schema(name) for name in json.loads(sys.argv[2])]"
    )
    checked = subprocess.run(
        [
            sys.executable, "-I", "-B", "-c", code,
            str(installed), json.dumps(schema_names),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
