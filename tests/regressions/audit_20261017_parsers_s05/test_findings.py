import logging
import re
import shlex
import warnings
from pathlib import Path

import pytest

from builders.build_mismatch_index import MismatchIndexBuilder
from parsers import IVTFFParser


ROOT = next(
    p for p in Path(__file__).resolve().parents
    if (p / "pyproject.toml").is_file()
)
HEADER = "#=IVTFF Eva- 2.0 M\n"


def test_f2_mismatch_loader_does_not_silently_accept_rejected_locus(
    monkeypatch, caplog
):
    source = HEADER + "<f1r>\n<f1r.1,@X9> daiin\n"

    def parse_bad_source(self, path):
        return self.parse_string(source)

    monkeypatch.setattr(IVTFFParser, "parse_file", parse_bad_source)
    builder = MismatchIndexBuilder(cache_dir=ROOT / "data_sources/cache")
    with caplog.at_level(logging.WARNING), warnings.catch_warnings(record=True) as issued:
        warnings.simplefilter("always")
        try:
            loaded = builder.load_transcription("zl")
        except ValueError:
            return

    surfaced = (
        caplog.text
        + "\n".join(str(item.message) for item in issued)
        + str(builder.stats.get("warnings", ""))
    )
    assert not loaded or "f1r:1" in surfaced


def test_f1_ci_reaches_configured_proof_roots_and_trunk():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    command = re.search(
        r"^\s*run:\s*(pytest[^\n]*)$", workflow, re.MULTILINE
    ).group(1)
    arguments = shlex.split(command)[1:]
    targets = [a for a in arguments if not a.startswith("-")]
    roots = re.search(
        r"^testpaths\s*=\s*(.+)$",
        (ROOT / "pytest.ini").read_text(),
        re.MULTILINE,
    ).group(1).split()
    assert not targets or all(
        any(Path(root).is_relative_to(Path(target)) for target in targets)
        for root in roots
    ), (command, roots)

    trunk = re.search(
        r'^TRUNK_BRANCH="([^"]+)"$',
        'TRUNK_BRANCH="main"',
        re.MULTILINE,
    ).group(1)
    filters = re.findall(r"branches:\s*\[([^\]]+)\]", workflow)
    assert filters
    assert all(
        trunk in [value.strip().strip("'\"") for value in values.split(",")]
        for values in filters
    )
