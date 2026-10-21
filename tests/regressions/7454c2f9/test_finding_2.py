# tests/regressions/7454c2f9/test_finding_2.py
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_ships_the_layer_registry(tmp_path):
    root = Path(__file__).resolve().parents[3]
    source = tmp_path / "source"
    source.mkdir()

    for name in (
        "pyproject.toml", "README.md", "LICENSE",
        "MANIFEST.in", "setup.cfg", "setup.py",
    ):
        path = root / name
        if path.is_file():
            shutil.copy2(path, source / name)

    for name in (
        "vcat", "parsers", "builders", "validators",
        "hf", "data_sources", "schemas",
    ):
        shutil.copytree(
            root / name,
            source / name,
            ignore=shutil.ignore_patterns("cache", "__pycache__", "*.pyc"),
        )

    wheels = tmp_path / "wheels"
    built = subprocess.run(
        [
            sys.executable, "-B", "-m", "pip", "wheel",
            "--no-index", "--no-deps", "--no-build-isolation",
            "--no-cache-dir", "--wheel-dir", str(wheels), str(source),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr

    wheel, = wheels.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        name = "data_sources/layers.yaml"
        assert name in archive.namelist()
        assert archive.read(name) == (root / name).read_bytes()
