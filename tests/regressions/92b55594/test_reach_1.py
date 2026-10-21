# tests/regressions/92b55594/test_reach_1.py
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tests import test_transliterations as checks


def test_fresh_build_predicate_rejects_changed_parquet_bytes(tmp_path, monkeypatch):
    original_write = pq.write_table

    def change_metadata(table, where, *args, **kwargs):
        if Path(where).name in {
            "locus_variants.parquet",
            "word_alignments.parquet",
        }:
            metadata = dict(table.schema.metadata or {})
            metadata[b"reach_probe"] = b"different file bytes"
            table = table.replace_schema_metadata(metadata)
        return original_write(table, where, *args, **kwargs)

    monkeypatch.setattr(pq, "write_table", change_metadata)

    with pytest.raises(AssertionError):
        checks.test_the_committed_output_is_a_fresh_build(tmp_path)
