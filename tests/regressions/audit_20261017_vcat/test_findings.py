import configparser
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_f1_high_ascii_only_source_words_are_counted():
    from vcat.eva_charset import validate_eva_text

    source = ROOT / "data_sources/cache/ZL3b-n.txt"
    pattern = re.compile(
        r"^<([^>.]+)\.(\d+),[^>]+>[ \t]*((?:@\d{3};)+)[ \t]*$"
    )
    matches = [
        match for line in source.read_text().splitlines()
        if (match := pattern.fullmatch(line))
    ]
    assert matches, "Positive control: source must exercise encoded-glyph words"

    rows = {
        row["line_id"]: row
        for line in (ROOT / "output/eva_lines.jsonl").read_text().splitlines()
        if (row := json.loads(line))
    }
    for match in matches:
        text = match.group(3)
        expected = len([word for word in re.split(r"[.,\s]+", text) if word])
        line_id = f"{match.group(1)}:{int(match.group(2))}"
        assert validate_eva_text(text).word_count == expected, line_id
        assert rows[line_id]["word_count"] == expected, line_id


def test_f4_diplomatic_removes_whitespace_inside_alternates():
    from parsers import IVTFFParser
    from vcat.profiles import apply_profile

    text = "d[a : b]y"
    parser = IVTFFParser(strict=True)
    locus = list(parser.parse_string(
        "#=IVTFF Eva- 2.0\n<f1r>\n<f1r.1,@P0> " + text + "\n"
    ))[0].loci[0]
    assert not parser.warnings
    assert apply_profile("raw-v1", locus.markup) == text
    assert apply_profile("diplomatic-v1", locus.markup) == "d[a:b]y"


def test_f5_raw_validation_handles_supported_readings_and_wraps():
    from parsers import IVTFFParser
    from vcat.eva_charset import validate_eva_text

    for raw, reading in [("[:a]", ""), ("a /\n/ b", "ab")]:
        parser = IVTFFParser(strict=True)
        list(parser.parse_string(
            "#=IVTFF Eva- 2.0\n<f1r>\n<f1r.1,@P0> " + raw + "\n"
        ))
        assert not parser.warnings
        result = validate_eva_text(raw, strict=True)
        assert result.is_valid, result.errors
        assert result.char_count == len(reading)
        assert result.word_count == len(
            [word for word in re.split(r"[.,\s]+", reading) if word]
        )


def test_f2_ci_does_not_override_configured_proof_trees():
    config = configparser.ConfigParser()
    config.read(ROOT / "pytest.ini")
    proof_trees = set(config["pytest"]["testpaths"].split())
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    commands = [
        shlex.split(match.group(1))
        for match in re.finditer(r"(?m)^\s*run:\s*(.*pytest.*)$", workflow)
    ]
    assert commands, "Positive control: find the CI pytest invocation"
    for command in commands:
        positional_trees = {
            arg.rstrip("/") for arg in command
            if arg.rstrip("/") in proof_trees
        }
        assert not positional_trees, command


def test_f6_named_logger_uses_configured_stream():
    code = """
import io
from vcat.logging import configure_logging, get_logger
sink = io.StringIO()
configure_logging(level="INFO", format="json", stream=sink)
get_logger("vcat.audit_stream_proof").info("child")
get_logger().info("root")
print(sink.getvalue(), end="")
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    messages = [json.loads(line)["message"] for line in result.stdout.splitlines()]
    assert "root" in messages, "Positive control: configured stream receives root"
    assert "child" in messages
