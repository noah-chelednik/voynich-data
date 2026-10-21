# tests/regressions/5427a363/test_finding_1.py
import configparser
import re
import shlex
from pathlib import Path

ROOT = next(
    p for p in Path(__file__).resolve().parents
    if (p / "pyproject.toml").is_file()
)


def test_ci_selects_every_configured_test_tree():
    configuration = configparser.ConfigParser()
    configuration.read(ROOT / "pytest.ini")
    configured = configuration["pytest"]["testpaths"].split()
    assert list((ROOT / "tests/regressions").rglob("test_*.py"))

    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    match = re.search(r"- name: Run tests\s+run: ([^\n]+)", workflow)
    assert match is not None
    arguments = shlex.split(match.group(1))
    pytest_index = next(
        i for i, argument in enumerate(arguments)
        if Path(argument).name == "pytest"
    )
    explicit = [
        argument.split("::", 1)[0]
        for argument in arguments[pytest_index + 1:]
        if not argument.startswith("-")
    ]
    selected = explicit or configured

    for tree in configured:
        assert any(
            (ROOT / tree).resolve().is_relative_to(
                (ROOT / selector).resolve()
            )
            for selector in selected
        ), f"CI excludes configured test tree {tree}"
