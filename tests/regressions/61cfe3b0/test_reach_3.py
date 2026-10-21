# tests/regressions/61cfe3b0/test_reach_3.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "path, expression",
    [
        ("builders/build_eva_lines.py", "len(line_types) >= 2"),
        ("tests/test_mismatch_index.py", "len(statuses) >= 2"),
    ],
)
def test_population_thresholds_are_not_hidden_by_their_small_value(
    path, expression
):
    snippet = f"assert {expression}\n"
    assert _literal_count_hits(path, snippet), (
        f"The literal-count gate did not detect the population threshold: "
        f"{expression}"
    )
