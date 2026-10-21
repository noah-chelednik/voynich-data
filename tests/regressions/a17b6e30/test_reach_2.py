# tests/regressions/a17b6e30/test_reach_2.py
import importlib.util
import json
from pathlib import Path

from parsers import ivtff_markup as mk
from vcat import profiles as vp

ROOT = Path(__file__).resolve().parents[3]


def test_all_markup_validator_predicate_supplies_every_defined_kind(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "reach_validator_predicates", ROOT / "tests" / "test_profiles.py"
    )
    assert spec is not None and spec.loader is not None
    predicates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predicates)

    predicates.test_validators_accept_a_build_and_its_profile(tmp_path)
    rows = [
        json.loads(line)
        for line in (tmp_path / "out" / "eva_lines.jsonl").read_text().splitlines()
    ]
    seen = {
        token.kind
        for row in rows
        for token in mk.parse_markup(row["text_raw"]).tokens
    }
    required = set(vp.TOKEN_KINDS) - {mk.UNKNOWN}

    assert required <= seen, f"Unexercised defined token kinds: {sorted(required - seen)}"
