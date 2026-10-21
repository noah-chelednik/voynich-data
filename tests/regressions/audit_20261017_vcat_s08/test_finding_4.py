def test_f4_named_logging_obeys_package_configuration():
    import subprocess
    import sys

    code = """
import json
import logging
from io import StringIO
from vcat.logging import configure_logging, get_logger

sink = StringIO()
configure_logging(level="DEBUG", format="json", stream=sink)
get_logger("vcat").info("root-control")
get_logger("vcat.audit_stream_proof").info("named-probe")
messages = [json.loads(line)["message"] for line in sink.getvalue().splitlines()]
assert messages == ["root-control", "named-probe"], messages

configure_logging(level="ERROR", format="json", stream=sink)
child = get_logger("vcat.audit_stream_proof")
assert child.logger.getEffectiveLevel() == logging.ERROR
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
