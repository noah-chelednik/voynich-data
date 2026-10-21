# tests/regressions/bef641e7/test_reach_5.py
import pytest

from tests import test_data_model_doc as checks


def test_metadata_field_lists_reject_an_unpublished_file(monkeypatch):
    metadata = checks.OUTPUT / "metadata"
    stems = sorted(path.stem for path in metadata.glob("*.jsonl"))
    assert stems

    for stem in stems:
        checks.test_metadata_field_lists_are_the_outputs(stem)

    unknown = "unpublished_reach_probe.jsonl"
    assert not (metadata / unknown).exists()
    body = checks.section("Metadata datasets (`output/metadata/`)")
    extra = (
        "\n| file | fields |\n"
        "|---|---|\n"
        f"| `{unknown}` | `invented_field` |\n\n"
    )
    monkeypatch.setattr(
        checks,
        "DOC",
        checks.DOC.replace(body, body + extra, 1),
    )

    with pytest.raises(AssertionError):
        for stem in stems:
            checks.test_metadata_field_lists_are_the_outputs(stem)
