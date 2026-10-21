# tests/regressions/audit_20261018_tests/test_finding_3.py
import copy
import inspect
import json
from pathlib import Path

import pytest

from tests import test_validators as checks
from validators import schema as schema_module


def test_line_number_test_detects_a_removed_minimum(monkeypatch):
    method = checks.TestValidateAgainstSchema().test_validate_invalid_line_number
    root = Path(checks.__file__).resolve().parent.parent
    valid = json.loads((root / "output/eva_lines.jsonl").read_text().splitlines()[0])
    kwargs = {}
    if "valid_transcription_record" in inspect.signature(method).parameters:
        kwargs["valid_transcription_record"] = copy.deepcopy(valid)

    method(**kwargs)
    weakened = copy.deepcopy(
        schema_module.load_schema("transcription_lines.schema.json")
    )
    del weakened["properties"]["line_number"]["minimum"]
    monkeypatch.setattr(schema_module, "load_schema", lambda name: weakened)

    with pytest.raises(AssertionError):
        method(**kwargs)
