# tests/regressions/494bb9ab/test_finding_3.py
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def test_built_wheel_can_import_builders(tmp_path):
    root = Path(__file__).resolve().parents[3]
    source = tmp_path / "source"
    source.mkdir()

    for name in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "MANIFEST.in",
        "setup.cfg",
        "setup.py",
    ):
        path = root / name
        if path.is_file():
            shutil.copy2(path, source / name)

    for name in (
        "vcat",
        "parsers",
        "builders",
        "validators",
        "hf",
        "data_sources",
        "schemas",
    ):
        shutil.copytree(
            root / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    wheels = tmp_path / "wheels"
    built = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pip",
            "wheel",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            "--no-cache-dir",
            "--wheel-dir",
            str(wheels),
            str(source),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr

    wheel_files = list(wheels.glob("*.whl"))
    assert len(wheel_files) == 1
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel_files[0]) as archive:
        archive.extractall(installed)

    imported = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "from builders import build_metadata_datasets, LineRecord",
            str(installed),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
