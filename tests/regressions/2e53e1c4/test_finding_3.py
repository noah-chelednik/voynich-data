# tests/regressions/2e53e1c4/test_finding_3.py
import json

import pytest

from vcat import iiif


@pytest.mark.parametrize("kind", ["not-a-manifest", "foreign-manifest"])
def test_invalid_manifest_does_not_replace_the_pinned_extract(tmp_path, kind):
    destination = tmp_path / "extract.json"
    original = iiif.CANVASES_JSON.read_bytes()
    destination.write_bytes(original)
    assert iiif.load_canvases(destination) == iiif.load_canvases()

    candidate = {}
    if kind == "foreign-manifest":
        candidate = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "id": "https://example.org/manifests/another-manuscript",
            "type": "Manifest",
            "items": [
                {
                    "id": "https://example.org/canvas/1",
                    "type": "Canvas",
                    "label": {"none": ["1r"]},
                    "items": [
                        {
                            "items": [
                                {
                                    "body": {
                                        "service": [
                                            {"id": "https://example.org/iiif/1"}
                                        ]
                                    }
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    with pytest.raises(ValueError):
        iiif.write_extract(json.dumps(candidate).encode(), destination)
    assert destination.read_bytes() == original
