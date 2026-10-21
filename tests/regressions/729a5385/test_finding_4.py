# tests/regressions/729a5385/test_finding_4.py
import json
import sys
import types
from collections import Counter
from pathlib import Path


def test_statistics_notebook_does_not_save_checkout_figures(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[3]
    notebook = json.loads(
        (root / "notebooks/02_sanity_statistics.ipynb").read_text()
    )
    saved = []
    pyplot = types.ModuleType("matplotlib.pyplot")
    for name in (
        "figure", "bar", "barh", "xlabel", "ylabel",
        "title", "tight_layout", "show",
    ):
        setattr(pyplot, name, lambda *args, **kwargs: None)
    pyplot.savefig = lambda path, **kwargs: saved.append(Path(path))
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.pyplot = pyplot
    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", pyplot)

    # Positive control for the write-attempt recorder.
    control = tmp_path / "control.png"
    pyplot.savefig(control)
    assert saved == [control]
    saved.clear()

    namespace = {
        "project_root": tmp_path,
        "char_counter": Counter({"a": 1}),
        "section_stats": {"sample": {"pages": {"f1r"}}},
    }
    for cell in notebook["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and "import matplotlib.pyplot" in source:
            exec(compile(source, "<notebook-plot-cell>", "exec"), namespace)

    assert not [
        path for path in saved
        if path.resolve().is_relative_to(tmp_path.resolve())
    ], saved
