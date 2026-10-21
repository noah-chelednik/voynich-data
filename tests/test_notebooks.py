"""
The notebooks run in the suite (roadmap item 1.9, D8: "notebooks never run"). Each is executed from `notebooks/`, as a
reader runs it, on the committed output and the cached sources; a cell that raises fails the test. No network access.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


def test_there_are_notebooks():
    assert NOTEBOOKS


#: NBClient's tags that let a cell not run or fail without failing the run; no notebook may carry them (AT2 F2, B-078).
SUPPRESSING_TAGS = {"skip-execution", "raises-exception"}


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_runs(path: Path):
    """Every code cell runs and none raises: no cell is tagged to be skipped or allowed to fail, and NBClient raises on
    any error, whatever a cell's tags say."""
    notebook = nbformat.read(path, as_version=4)
    for index, cell in enumerate(notebook.cells):
        tags = set(cell.get("metadata", {}).get("tags", []))
        assert not tags & SUPPRESSING_TAGS, (path.name, index, sorted(tags & SUPPRESSING_TAGS))
    NotebookClient(
        notebook,
        timeout=600,
        kernel_name="python3",
        allow_errors=False,
        force_raise_errors=True,
        skip_cells_with_tag="",
        resources={"metadata": {"path": str(path.parent)}},
    ).execute()
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is not None, (path.name, cell.source[:60])
            assert not [o for o in cell.outputs if o.get("output_type") == "error"], (
                path.name,
                cell.source[:60],
            )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_is_committed_without_outputs(path: Path):
    """A committed output would be a number no build produced; the outputs come from running the notebook."""
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert not cell.outputs and cell.execution_count is None, path.name
