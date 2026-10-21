# tests/regressions/69aa93cc/test_finding_1.py
from builders.build_metadata import build_metadata_datasets
from vcat.sources import cached_sources


def test_lsi_hand_layer_names_the_classification_its_source_states():
    source = next(s for s in cached_sources() if s.id == "LSI")
    text = source.path.read_text(encoding=source.encoding)
    assert "$H = Currier's hand" in text

    result = build_metadata_datasets(source.path)
    assert any(page.hand for page in result.pages)

    field = "voynich-manuscript-metadata:pages.hand"
    attributions = [
        layer["attribution"]
        for layer in result.tables()["layers"]
        if field in layer["fields"]
    ]
    assert attributions
    assert all("Currier" in attribution for attribution in attributions), attributions
