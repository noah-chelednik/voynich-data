# tests/regressions/d0d64b4c/test_finding_1.py
import copy
import json

import pytest

from vcat import iiif


def test_scalar_language_value_does_not_replace_the_extract(tmp_path):
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
                                    "service": [
                                        {"id": canvas["image_service"]}
                                    ]
                                }
                            }
                        ]
                    }
                ],
            }
        ],
    }

    good = iiif.write_extract(
        json.dumps(manifest).encode(),
        tmp_path / "valid.json",
    )
    assert good["canvases"][0]["label"] == canvas["label"]

    destination = tmp_path / "extract.json"
    original = iiif.CANVASES_JSON.read_bytes()
    destination.write_bytes(original)
    assert iiif.load_canvases(destination) == iiif.load_canvases()

    malformed = copy.deepcopy(manifest)
    malformed["items"][0]["label"] = {"none": canvas["label"]}

    with pytest.raises(ValueError):
        iiif.write_extract(
            json.dumps(malformed).encode(),
            destination,
        )

    assert destination.read_bytes() == original
