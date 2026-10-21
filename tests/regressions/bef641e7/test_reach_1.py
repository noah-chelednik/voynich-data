# tests/regressions/bef641e7/test_reach_1.py
import pytest
import yaml

from vcat import layers as vl


@pytest.mark.parametrize("field", ["source", "attribution"])
@pytest.mark.parametrize("value", [None, ""])
def test_registry_refuses_empty_required_provenance(tmp_path, field, value):
    data = yaml.safe_load(vl.LAYERS_YAML.read_text(encoding="utf-8"))
    entry = next(row for row in data["layers"] if row["kind"] == "vcat")
    entry[field] = value
    path = tmp_path / "layers.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError):
        vl.load_layers(path)
