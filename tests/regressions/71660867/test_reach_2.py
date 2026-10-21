# tests/regressions/71660867/test_reach_2.py
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tests import test_words as checks


def test_fresh_build_predicate_reads_the_generated_parquet(tmp_path, monkeypatch):
    original_write = pq.write_table

    def omit_first_row(table, where, *args, **kwargs):
        if Path(where).name == "eva_words.parquet":
            table = table.slice(1)
        return original_write(table, where, *args, **kwargs)

    monkeypatch.setattr(pq, "write_table", omit_first_row)

    with pytest.raises(AssertionError):
        checks.test_the_committed_words_are_the_build_of_the_committed_lines(tmp_path)
