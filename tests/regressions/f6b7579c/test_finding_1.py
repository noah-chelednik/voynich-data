# tests/regressions/f6b7579c/test_finding_1.py
import copy
import json

import pytest

from vcat import iiif


@pytest.mark.parametrize(
    "defect",
    ["missing-label", "null-label", "empty-label", "null-service"],
)
def test_invalid_canvas_does_not_replace_the_extract(tmp_path, defect):
    canvas = next(
        c
        for c in iiif.load_canvases()["canvases"]
        if iiif.sides_of_label(c["label"])
    )
    manifest = {
        "id": iiif.MANIFEST_URL,
        "type": "Manifest",
        "items": [
            {
                "id": canvas["canvas_id"],
                "type": "Canvas",
                "label": {"none": [canvas["label"]]},
                "items": [
                    {
                        "items": [
                            {
                                "body": {
                                    "service": [{"id": canvas["image_service"]}]
                                }
                            }
                        ]
                    }
                ],
            }
        ],
    }

    good = iiif.write_extract(
        json.dumps(manifest).encode(), tmp_path / "valid.json"
    )
    assert good["canvases"][0]["label"] == canvas["label"]
    assert good["canvases"][0]["image_service"] == canvas["image_service"]

    candidate = copy.deepcopy(manifest)
    entry = candidate["items"][0]
    if defect == "missing-label":
        del entry["label"]
    elif defect == "null-label":
        entry["label"] = None
    elif defect == "empty-label":
        entry["label"] = {"none": [""]}
    else:
        entry["items"][0]["items"][0]["body"]["service"] = [{"@id": None}]

    destination = tmp_path / "extract.json"
    original = iiif.CANVASES_JSON.read_bytes()
    destination.write_bytes(original)

    with pytest.raises(ValueError):
        iiif.write_extract(json.dumps(candidate).encode(), destination)

    assert destination.read_bytes() == original
