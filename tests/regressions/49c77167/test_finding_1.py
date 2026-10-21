# tests/regressions/49c77167/test_finding_1.py
import pytest

from vcat.loss_accounting import account, census_text


@pytest.mark.parametrize("reported", [[], ["f1r:2"]])
def test_account_rejects_missing_reading_despite_shared_id(reported):
    census = census_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0;H> daiin\n"
        "<f1r.1,@P0;C> otol\n"
        "<f1r.2,+P0;H> ol\n"
    )
    emitted = ["f1r:1", "f1r:2"]

    control = account(
        census, emitted, census.pages, reported_loci=["f1r:1"]
    )
    assert control.complete, control.problems()

    result = account(
        census, emitted, census.pages, reported_loci=reported
    )
    assert not result.complete
    assert result.unaccounted_loci == ["f1r:1"]
