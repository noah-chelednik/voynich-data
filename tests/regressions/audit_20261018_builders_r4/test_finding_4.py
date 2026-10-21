def test_card_schema_uses_the_validator_schema_location(monkeypatch, tmp_path):
    import json
    from builders.cards import eva_schema
    from validators import schema

    name = "transcription_lines.schema.json"
    selected = schema.load_schema(name)
    selected["description"] = "Schema selected by the shared schema directory"
    (tmp_path / name).write_text(json.dumps(selected), encoding="utf-8")
    monkeypatch.setattr(schema, "SCHEMA_DIR", tmp_path)

    assert eva_schema() == schema.load_schema(name)
