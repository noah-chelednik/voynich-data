def test_f1_ci_includes_configured_proof_roots():
    import configparser
    import shlex
    from pathlib import Path

    import yaml

    cfg = configparser.ConfigParser()
    cfg.read("pytest.ini")
    steps = yaml.safe_load(
        Path(".github/workflows/ci.yml").read_text()
    )["jobs"]["test"]["steps"]
    command = next(s["run"] for s in steps if s.get("name") == "Run tests")
    args = shlex.split(command)
    selected = [Path(a) for a in args[1:] if not a.startswith("-")]
    roots = [Path(p) for p in cfg["pytest"]["testpaths"].split()]
    uncovered = [
        str(p) for p in roots
        if selected and not any(p.is_relative_to(s) for s in selected)
    ]
    assert not uncovered, uncovered
