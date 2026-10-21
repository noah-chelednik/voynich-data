"""Upstream tracking (roadmap item 2.1): the check against voynich.nu, the locus diff, and the scheduled workflow.

No test reaches the network: the fetcher is replaced by one serving the cached bytes, or edited copies of them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vcat import upstream
from vcat.sources import cached_sources, load_sources

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "upstream.yml"
SOURCES = {s.id: s for s in cached_sources()}
FETCHED = {e["id"] for e in load_sources()["cached"] if e.get("url_fetched")}


def zl_lines() -> list[str]:
    return SOURCES["ZL"].path.read_bytes().decode("utf-8").split("\n")


def edited_zl() -> tuple[bytes, dict[str, list[str]]]:
    """ZL with one locus's text changed, one locus removed, one added and one page header edited; and what the diff of
    those edits must be."""
    lines = zl_lines()
    seven = next(i for i, line in enumerate(lines) if line.startswith("<f1r.7,"))
    nineteen = next(i for i, line in enumerate(lines) if line.startswith("<f1r.19,"))
    lines[seven] = lines[seven] + ".daiin"
    removed = lines.pop(nineteen)
    assert removed.startswith("<f1r.19,")
    lines.insert(nineteen, "<f1r.99,+P0>      daiin.daiin")
    header = next(i for i, line in enumerate(lines) if line.startswith("<f1v>"))
    lines[header] = lines[header] + " "
    return "\n".join(lines).encode("utf-8"), {
        "added": ["f1r.99"],
        "removed": ["f1r.19"],
        "changed": ["f1r.7"],
    }


@pytest.mark.parametrize("source_id", sorted(SOURCES))
def test_a_file_against_itself_differs_in_nothing(source_id):
    """Every cached source, its loci and its other lines, read whole: the diff of a file with itself is empty."""
    source = SOURCES[source_id]
    data = source.path.read_bytes()
    assert (
        upstream.locus_diff(data, data, source.encoding).as_dict() == upstream.LocusDiff().as_dict()
    )


def test_the_diff_names_each_locus_added_removed_and_changed():
    """On real edits of ZL: the changed locus, the removed one and the added one are named exactly; the edited page
    header is an other line removed and one added."""
    new, expected = edited_zl()
    diff = upstream.locus_diff(SOURCES["ZL"].path.read_bytes(), new).as_dict()
    assert {k: diff[k] for k in ("added", "removed", "changed")} == expected
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 1)


def test_a_line_the_parser_does_not_read_as_a_locus_is_still_compared():
    """LSI holds lines the parser reports instead of reading as loci (the registry's nonconforming lines): a change to
    one is an other line changed, not lost between the two comparisons."""
    from vcat.sources import nonconforming_lines

    source = SOURCES["LSI"]
    data = source.path.read_bytes()
    text = data.decode(source.encoding)
    numbers = nonconforming_lines(source.path)
    assert numbers
    lines = text.split("\n")
    number = min(numbers)
    line = lines[number - 1]
    ending = "\r" if line.endswith("\r") else ""  # LSI's lines end with CR LF
    lines[number - 1] = line[: len(line) - len(ending)] + "x" + ending
    diff = upstream.locus_diff(
        data, "\n".join(lines).encode(source.encoding), source.encoding
    ).as_dict()
    assert (diff["added"], diff["removed"], diff["changed"]) == ([], [], [])
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 1)


def test_a_reordering_is_named_and_a_file_differs_whenever_its_bytes_do():
    """Two loci swapped are moved; a comment line moved to another locus is an other line removed and added; any
    difference of bytes is a difference (`identical`), whatever the lists name (review 5af7b31a finding 1).
    """
    lines = zl_lines()
    two = next(i for i, line in enumerate(lines) if line.startswith("<f1r.2,"))
    three = next(i for i, line in enumerate(lines) if line.startswith("<f1r.3,"))
    swapped = list(lines)
    swapped[two], swapped[three] = swapped[three], swapped[two]
    old = SOURCES["ZL"].path.read_bytes()
    diff = upstream.locus_diff(old, "\n".join(swapped).encode("utf-8")).as_dict()
    assert diff["moved"] and set(diff["moved"]) <= {"f1r.2", "f1r.3"}
    assert (diff["added"], diff["removed"], diff["changed"], diff["identical"]) == (
        [],
        [],
        [],
        False,
    )
    comment = next(i for i, line in enumerate(lines) if line.startswith("#") and i > three)
    moved = list(lines)
    moved.insert(two, moved.pop(comment))
    diff = upstream.locus_diff(old, "\n".join(moved).encode("utf-8")).as_dict()
    assert (diff["other_lines_added"], diff["other_lines_removed"]) == (1, 1)
    assert upstream.locus_diff(old, old).identical
    # two other lines swapped within one gap (review bfd4e0ad finding 1): counted, not lost
    header = next(i for i, line in enumerate(lines) if line.startswith("<f1v>"))
    first = next(i for i in range(header + 1, len(lines)) if lines[i].startswith("#"))
    second = first + 1
    assert lines[second].startswith("#") and lines[first] != lines[second]
    within = list(lines)
    within[first], within[second] = within[second], within[first]
    diff = upstream.locus_diff(old, "\n".join(within).encode("utf-8")).as_dict()
    assert diff["other_lines_added"] == diff["other_lines_removed"] >= 1
    assert (diff["added"], diff["removed"], diff["changed"], diff["identical"]) == (
        [],
        [],
        [],
        False,
    )


def test_a_repeated_locus_key_is_refused():
    """Two loci with one page, number and transcriber would make the diff lose one: refused."""
    lines = zl_lines()
    seven = next(i for i, line in enumerate(lines) if line.startswith("<f1r.7,"))
    lines.insert(seven + 1, lines[seven])
    with pytest.raises(ValueError, match="two loci"):
        upstream.locus_diff(SOURCES["ZL"].path.read_bytes(), "\n".join(lines).encode("utf-8"))


def served(changes: dict[str, bytes] | None = None, down: set[str] = frozenset()):
    """A fetcher serving each fetched source's cached bytes, or the given replacement, or failing."""
    by_url = {SOURCES[i].url: i for i in FETCHED}

    def fetch(url: str) -> bytes:
        source_id = by_url[url]
        if source_id in down:
            raise OSError("connection refused")
        if changes and source_id in changes:
            return changes[source_id]
        return SOURCES[source_id].path.read_bytes()

    return fetch


def test_every_fetched_source_is_checked_and_unchanged_when_served_as_pinned():
    results = upstream.check_upstream(served())
    assert sorted(r["id"] for r in results) == sorted(FETCHED)
    assert {r["status"] for r in results} == {"unchanged"}
    assert all(r["served_sha256"] == r["pinned_sha256"] for r in results)


def test_a_changed_source_is_reported_with_its_diff_and_an_unreachable_one_with_its_reason():
    new, expected = edited_zl()
    results = {r["id"]: r for r in upstream.check_upstream(served({"ZL": new}, down={"IT"}))}
    assert results["ZL"]["status"] == "changed"
    assert {k: results["ZL"]["diff"][k] for k in ("added", "removed", "changed")} == expected
    assert (
        results["IT"]["status"] == "unreachable" and "connection refused" in results["IT"]["error"]
    )
    assert {r["status"] for i, r in results.items() if i not in ("ZL", "IT")} == {"unchanged"}


def test_the_check_command_exits_by_what_it_found(tmp_path, monkeypatch):
    """Exit 0 when all are unchanged, 1 when any changed, 2 when any was unreachable, 3 when both; the reports hold every
    source."""
    from scripts import check_upstream as command

    new, _ = edited_zl()
    cases = (
        (served(), 0),
        (served({"ZL": new}), 1),
        (served(down={"IT"}), 2),
        (served({"ZL": new}, down={"IT"}), 3),
    )
    for fetcher, code in cases:
        monkeypatch.setattr(command, "check_upstream", lambda f=fetcher: upstream.check_upstream(f))
        report, markdown = tmp_path / "r.json", tmp_path / "r.md"
        assert command.main(["--report", str(report), "--markdown", str(markdown)]) == code
        assert sorted(s["id"] for s in json.loads(report.read_text())["sources"]) == sorted(FETCHED)
        text = markdown.read_text()
        assert all(f"| {i} |" in text for i in FETCHED)
        # a changed source's added locus is named in the issue body
        assert ("f1r.99" in text) == (code in (1, 3))


def test_the_diff_command_exits_by_whether_the_files_differ(tmp_path):
    from scripts import source_diff as command

    old = SOURCES["ZL"].path
    new, _ = edited_zl()
    edited = tmp_path / "zl.txt"
    edited.write_bytes(new)
    assert command.main([str(old), str(old)]) == 0
    assert command.main([str(old), str(edited)]) == 1


def test_the_workflow_runs_the_check_weekly_and_opens_an_issue_only_on_a_change():
    """Scheduled and dispatchable; least permissions (read the code, write issues); runs the check; for every exit code
    of the check, the issue is opened or commented exactly on a change (1, 3) and the run fails on every status but 0
    and 1: an unreachable source, a failed check, and a check that did not finish (killed: 137)."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["schedule"] and "cron" in triggers["schedule"][0]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read", "issues": "write"}
    steps = workflow["jobs"]["check"]["steps"]
    check = next(s for s in steps if "scripts/check_upstream.py" in s.get("run", ""))
    after = steps[steps.index(check) + 1 :]
    output = f"steps.{check['id']}.outputs.status"

    def runs(step: dict, status: str) -> bool:
        """Whether a step runs for a status: its condition (comparisons of the status, `&&`, `||`, parentheses only)
        evaluated."""
        condition = step.get("if")
        if condition is None or condition == "always()":
            return True
        assert set(condition.replace(output, "S")) <= set("S=!'0123456789 &|()"), condition
        expression = (
            condition.replace(output, repr(status)).replace("&&", " and ").replace("||", " or ")
        )
        return bool(eval(expression))  # noqa: S307 - the workflow's own conditions, checked above

    for status in ("0", "1", "2", "3", "4", "137"):  # 137: the check killed
        issue = [s for s in after if runs(s, status) and "upstream_issue.sh" in s.get("run", "")]
        fails = [s for s in after if runs(s, status) and "exit 1" in s.get("run", "")]
        assert bool(issue) == (status in ("1", "3")), status
        assert bool(fails) == (status not in ("0", "1")), status
    script = (ROOT / ".github" / "scripts" / "upstream_issue.sh").read_text(encoding="utf-8")
    assert (
        "gh issue comment" in script and "gh issue create" in script and "upstream-change" in script
    )
