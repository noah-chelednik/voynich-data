# tests/regressions/9fa0ae04/test_finding_1.py
import pytest

from tests import test_stability as checks


@pytest.mark.parametrize(
    ("attribute", "heading", "predicate_name"),
    (
        (
            "STABILITY",
            "Versions",
            "test_the_version_parts_are_defined",
        ),
        (
            "ERRATA",
            None,
            "test_every_roadmap_defect_has_an_erratum",
        ),
    ),
)
def test_required_table_columns_cannot_be_deleted(
    monkeypatch, attribute, heading, predicate_name
):
    predicate = getattr(checks, predicate_name)
    predicate()

    original = getattr(checks, attribute)
    region = checks.section(original, heading) if heading else original
    identifiers_only = "".join(
        "|" + line.split("|")[1] + "|\n"
        if line.startswith("|")
        else line
        for line in region.splitlines(keepends=True)
    )
    assert identifiers_only != region
    changed = original.replace(region, identifiers_only, 1)
    monkeypatch.setattr(checks, attribute, changed)

    with pytest.raises(AssertionError):
        predicate()
