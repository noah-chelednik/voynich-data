"""S21 hardening, gate 8: the audits of 2026-10-21, the findings fixed beside their HIGHs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from parsers import IVTFFParser
from vcat import sources as registry
from vcat import upstream

ROOT = Path(__file__).resolve().parent.parent

HEADERLESS = (
    "# a comment first\n#=IVTFF Eva- 2.0 M 5\n<f1r>      <! $I=H>\n<f1r.1,@P0>       fachys.ykal\n"
)


def test_a_file_header_not_on_line_1_is_reported(tmp_path):
    """Audit 20261021-parsers F3: read as a comment (B-050), and reported, an error when strict."""
    path = tmp_path / "late.txt"
    path.write_text(HEADERLESS, encoding="utf-8")
    parser = IVTFFParser()
    list(parser.parse_file(path))
    assert parser.alphabet is None
    assert any("not on line 1" in w.reason and w.line_number == 2 for w in parser.warnings)
    with pytest.raises(ValueError, match="not on line 1"):
        list(IVTFFParser(strict=True).parse_file(path))


def test_a_file_whose_header_is_on_line_1_is_not_reported(tmp_path):
    path = tmp_path / "ok.txt"
    path.write_text(HEADERLESS.split("\n", 1)[1], encoding="utf-8")
    parser = IVTFFParser()
    list(parser.parse_file(path))
    assert parser.alphabet == "Eva-" and not parser.warnings


def test_both_validators_read_a_relative_output_dir_from_the_working_directory(tmp_path):
    """Audit 20261021-validators F3: an empty ./output fails both, never the repository's output in its place."""
    (tmp_path / "output").mkdir()
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}
    for module in ("validators.verify_invariants", "validators.validate_phase1_outputs"):
        done = subprocess.run(
            [sys.executable, "-m", module, "--output-dir", "output"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        assert done.returncode != 0, (module, done.stdout[-500:])


@pytest.mark.parametrize("value", [None, "yes", 1])
def test_the_upstream_check_refuses_a_source_without_a_boolean_url_fetched(monkeypatch, value):
    """Audit 20261021-vcat F1: a flag missing or of another type is refused, not read as `not fetched`."""
    data = registry.load_sources()
    entry = data["cached"][0]
    if value is None:
        entry.pop("url_fetched")
    else:
        entry["url_fetched"] = value
    monkeypatch.setattr(upstream, "load_sources", lambda: data)
    with pytest.raises(ValueError, match="url_fetched"):
        upstream.check_upstream(lambda url: b"")


def test_the_upstream_check_refuses_a_registry_that_fetches_nothing(monkeypatch):
    data = registry.load_sources()
    for entry in data["cached"]:
        entry["url_fetched"] = False
    monkeypatch.setattr(upstream, "load_sources", lambda: data)
    with pytest.raises(ValueError, match="nothing to check"):
        upstream.check_upstream(lambda url: b"")
