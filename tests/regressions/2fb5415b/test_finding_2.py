# tests/regressions/2fb5415b/test_finding_2.py
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_the_data_model_s_layer_table_puts_section_in_its_registry_layer():
    """Clause 21: the EVA `section` is described one way wherever it is described, the data model included: a renaming of
    what the source states, its layer `section_name`, which the registry records as the source's (`kind: source`). The
    data model's own table of layers (section 2) still files `section` under the layer `interpretation`."""
    layers = yaml.safe_load((ROOT / "data_sources" / "layers.yaml").read_text(encoding="utf-8"))["layers"]
    section_name = next(layer for layer in layers if layer["layer"] == "section_name")
    assert "voynich-eva:section" in section_name["fields"] and section_name["kind"] == "source"
    model = (ROOT / "docs" / "data_model.md").read_text(encoding="utf-8")
    layer_table = model.split("## 2. Layers", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in layer_table.splitlines() if re.search(r"\|\s*[^|]*`section`", line)]
    assert rows, "the layer table names no layer for `section`"
    stale = [row for row in rows if row.split("|")[1].strip() == "interpretation"]
    assert stale == [], stale
