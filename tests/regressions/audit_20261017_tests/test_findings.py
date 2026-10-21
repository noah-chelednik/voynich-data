# tests/regressions/audit_20261017_tests/test_findings.py
import re
import shlex
import subprocess
from pathlib import Path

import pytest

from tests import test_data_model_doc as document_checks
from tests.test_ci_checks import _literal_count_hits, _skip_and_xfail_uses


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)


def test_f1_ci_includes_the_reviewer_proofs():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    commands = re.findall(r"(?m)^\s*run:\s*(.*\bpytest\b.*)$", workflow)
    assert commands
    for command in commands:
        words = shlex.split(command)
        arguments = words[words.index("pytest") + 1:]
        primary = any(word.rstrip("/") == "tests" for word in arguments)
        proofs = any(word.rstrip("/") == "tests/regressions" for word in arguments)
        assert not primary or proofs, command


@pytest.mark.parametrize("name", ["pages", "folios", "quires"])
def test_f4_metadata_table_rejects_false_duplicate(monkeypatch, name):
    document_checks.test_metadata_field_lists_are_the_outputs(name)
    body = document_checks.section("Metadata datasets (`output/metadata/`)")
    prefix = f"| `{name}.jsonl` |"
    assert body.count(prefix) == 1
    changed = body.replace(
        prefix,
        f"| `{name}.jsonl` | `phantom_field` |\n" + prefix,
        1,
    )
    monkeypatch.setattr(
        document_checks,
        "DOC",
        document_checks.DOC.replace(body, changed, 1),
    )
    with pytest.raises(AssertionError):
        document_checks.test_metadata_field_lists_are_the_outputs(name)


@pytest.mark.parametrize(
    "source",
    [
        "from pytest import skip as skip_test\nskip_test('reason')\n",
        "from pytest import xfail\nxfail('reason')\n",
    ],
)
def test_f2_imported_skip_and_xfail_calls_are_detected(source):
    assert any(
        _skip_and_xfail_uses(
            "tests/probe.py", "import pytest\npytest.skip('reason')\n"
        )
    )
    assert any(
        _skip_and_xfail_uses(
            "tests/probe.py", "import pytest\npytest.xfail('reason')\n"
        )
    )
    assert any(_skip_and_xfail_uses("tests/probe.py", source)), source


@pytest.mark.parametrize(
    ("source", "expected_hit"),
    [
        (
            "def test_count(zl_source_path):\n"
            "    pages = load(zl_source_path)\n"
            "    assert len(pages) == 9\n",
            True,
        ),
        (
            "def outer():\n"
            "    rows = load(ZL)\n"
            "    def inner():\n"
            "        assert len(rows) == 9\n",
            True,
        ),
        (
            "rows = load(ZL)\n"
            "def check(rows):\n"
            "    assert len(rows) == 3\n"
            "check([1, 2, 3])\n",
            False,
        ),
    ],
)
def test_f3_population_provenance_respects_fixtures_and_scope(
    source, expected_hit
):
    assert _literal_count_hits(
        "tests/probe.py", "rows = load(ZL)\nassert len(rows) == 9\n"
    )
    assert bool(_literal_count_hits("tests/probe.py", source)) == expected_hit
