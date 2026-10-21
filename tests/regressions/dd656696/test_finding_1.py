# tests/regressions/dd656696/test_finding_1.py
from tests.test_ci_checks import _literal_count_hits


def test_straight_line_source_provenance_is_not_truncated():
    control = "rows = load(ZL)\nassert len(rows) == 9\n"
    assert _literal_count_hits("tests/probe.py", control)

    for origin, expected_hit in (("[]", False), ("load(ZL)", True)):
        names = [f"value_{index}" for index in range(53)]
        lines = [f"{names[0]} = {origin}"]
        lines.extend(
            f"{current} = {previous}"
            for previous, current in zip(names, names[1:])
        )
        lines.append(f"assert len({names[-1]}) == 9")
        source = "\n".join(lines) + "\n"

        assert bool(_literal_count_hits("tests/probe.py", source)) == expected_hit
