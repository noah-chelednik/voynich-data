# tests/regressions/020f7450/test_finding_1.py
import re
from collections import defaultdict

import pytest

from builders.build_metadata import build_metadata_datasets
from vcat.sources import ROOT, source_file


@pytest.mark.parametrize("source_id", ["ZL", "GC"])
def test_an_order_attributed_to_zl_is_zls_order(source_id):
    zl_text = (ROOT / source_file("ZL")).read_text(encoding="utf-8")
    zl_pages = re.findall(r"^<([^<>.,\s]+)>", zl_text, re.M)
    assert zl_pages

    result = build_metadata_datasets(ROOT / source_file(source_id))
    assert not result.report.warnings
    assert result.page_orders

    orders = defaultdict(list)
    for row in result.page_orders:
        orders[row.order].append(row)

    if source_id == "ZL":
        assert "zl_file" in orders

    for name, rows in orders.items():
        claims_zl = name == "zl_file" or any(
            "ZL transliteration" in row.attribution
            or "Zandbergen-Landini" in row.attribution
            for row in rows
        )
        if claims_zl:
            actual = [
                row.page_id
                for row in sorted(rows, key=lambda row: row.position)
            ]
            assert actual == zl_pages, (
                source_id,
                name,
                "The order claims ZL provenance but is not ZL's order",
            )
