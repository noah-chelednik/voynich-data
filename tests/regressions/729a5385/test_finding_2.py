# tests/regressions/729a5385/test_finding_2.py
import json
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


def test_metadata_card_documents_configured_serializations():
    root = Path(__file__).resolve().parents[3]
    card = (
        root / "huggingface/voynich-manuscript-metadata/README.md"
    ).read_text()
    front = yaml.safe_load(card.split("---", 2)[1])
    declared = set(
        re.findall(r"^\| `([^`]+)` \|", card, re.MULTILINE)
    )
    assert declared

    for config in front["configs"]:
        for entry in config["data_files"]:
            path = root / "output/metadata" / entry["path"]
            if path.suffix == ".parquet":
                schema = pq.read_schema(path)
                fields = set(schema.names)
                if "verso_page_ids" in fields:
                    kind = schema.field("verso_page_ids").type
                    if pa.types.is_string(kind) or pa.types.is_large_string(kind):
                        documented_types = re.findall(
                            r"^\| `verso_page_ids` \| ([^|]+) \|",
                            card,
                            re.MULTILINE,
                        )
                        assert any(
                            "str" in text
                            and "list" not in text
                            and "array" not in text
                            for text in documented_types
                        ), documented_types
            else:
                fields = set(
                    json.loads(path.read_text().splitlines()[0])
                )
            assert fields
            assert fields <= declared, (
                config["config_name"], sorted(fields - declared)
            )
