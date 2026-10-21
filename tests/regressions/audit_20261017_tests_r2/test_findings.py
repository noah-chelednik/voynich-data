# tests/regressions/audit_20261017_tests_r2/test_findings.py
import configparser
import subprocess
from pathlib import Path
from types import SimpleNamespace

import nbformat
import pytest
from _pytest.mark.structures import get_empty_parameterset_mark
from _pytest.nodes import Collector
from nbclient.exceptions import CellExecutionError

from tests import test_notebooks as notebook_checks
from tests.test_ci_checks import _literal_count_hits, _skip_and_xfail_uses


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)


def test_f1_empty_parameter_sets_are_rejected():
    source = (
        "import pytest\n"
        "cases = []\n"
        "@pytest.mark.parametrize('value', cases)\n"
        "def test_probe(value):\n"
        "    assert value\n"
    )
    assert any(
        _skip_and_xfail_uses(
            "tests/probe.py",
            "import pytest\npytest.skip('control')\n",
        )
    )
    detected = any(_skip_and_xfail_uses("tests/probe.py", source))
    config = configparser.ConfigParser()
    config.read(ROOT / "pytest.ini")
    requested = config["pytest"].get("empty_parameter_set_mark", "")

    def probe(value):
        pass

    refused_at_collection = False
    try:
        get_empty_parameterset_mark(
            SimpleNamespace(getini=lambda name: requested),
            ("value",),
            probe,
        )
    except Collector.CollectError:
        refused_at_collection = True

    assert detected or refused_at_collection, (
        "An empty parameter set is neither caught by the guard "
        "nor rejected by the configured collector."
    )


@pytest.mark.parametrize("tag", ["raises-exception", "skip-execution"])
def test_f2_notebook_error_cells_cannot_pass(tmp_path, tag):
    path = tmp_path / "probe.ipynb"
    nbformat.write(
        nbformat.v4.new_notebook(
            cells=[nbformat.v4.new_code_cell("value = 1")]
        ),
        path,
    )
    notebook_checks.test_notebook_runs(path)

    nbformat.write(
        nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell(
                    "raise RuntimeError('audit probe')",
                    metadata={"tags": [tag]},
                )
            ]
        ),
        path,
    )
    with pytest.raises((AssertionError, ValueError, CellExecutionError)):
        notebook_checks.test_notebook_runs(path)


@pytest.mark.parametrize(
    ("source", "expected_hit"),
    [
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
def test_f3_population_provenance_respects_scope(source, expected_hit):
    assert _literal_count_hits(
        "tests/probe.py",
        "rows = load(ZL)\nassert len(rows) == 9\n",
    )
    assert bool(_literal_count_hits("tests/probe.py", source)) == expected_hit
