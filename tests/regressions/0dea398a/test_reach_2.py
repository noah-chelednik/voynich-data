# tests/regressions/0dea398a/test_reach_2.py
import pytest

from builders import build_transliterations as bt


def test_build_rejects_one_reading_replaced_by_another(monkeypatch):
    record = next(r for r in bt.dataset_sources() if r.id == "LSI")
    original_parser = bt.IVTFFParser

    class DuplicatingParser(original_parser):
        def parse_file(self, *args, **kwargs):
            pages = list(super().parse_file(*args, **kwargs))
            seen = {}
            substituted = False
            for page in pages:
                for index, locus in enumerate(page.loci):
                    previous = seen.get(locus.locus_id)
                    if previous is not None:
                        assert previous.source_line != locus.source_line
                        page.loci[index] = previous
                        substituted = True
                        break
                    seen[locus.locus_id] = locus
                if substituted:
                    break
            assert substituted, "The registered interlinear source supplied no repeated locus"
            yield from pages

    monkeypatch.setattr(bt, "IVTFFParser", DuplicatingParser)
    with pytest.raises(ValueError):
        bt.build_source(record)
