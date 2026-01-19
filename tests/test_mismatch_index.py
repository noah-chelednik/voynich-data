"""Tests for the mismatch index builder."""

import json
from pathlib import Path

import pytest

from builders.build_mismatch_index import (
    MismatchIndexBuilder,
    MismatchRecord,
    TranscriptionLine,
)


class TestMismatchRecord:
    """Tests for MismatchRecord dataclass."""

    def test_create_record(self) -> None:
        """Test basic record creation."""
        record = MismatchRecord(
            page_id="f1r",
            line_number=1,
            line_id="f1r:1",
        )
        assert record.page_id == "f1r"
        assert record.line_number == 1
        assert record.line_id == "f1r:1"
        assert record.status == "unknown"

    def test_record_to_dict(self) -> None:
        """Test conversion to dictionary."""
        record = MismatchRecord(
            page_id="f1r",
            line_number=1,
            line_id="f1r:1",
            zl_text="test.text",
            it_text="test.text",
            status="exact_match",
            eva_agreement=True,
            similarity_score=1.0,
        )
        d = record.to_dict()
        assert d["page_id"] == "f1r"
        assert d["zl_text"] == "test.text"
        assert d["eva_agreement"] is True


class TestMismatchIndexBuilder:
    """Tests for MismatchIndexBuilder."""

    def test_normalize_eva_text_basic(self) -> None:
        """Test basic EVA text normalization."""
        text = "fachys.ykal.ar"
        normalized = MismatchIndexBuilder.normalize_eva_text(text)
        assert normalized == "fachys.ykal.ar"

    def test_normalize_eva_text_removes_uncertainty(self) -> None:
        """Test removal of uncertainty markers."""
        text = "fach?ys.yk!al"
        normalized = MismatchIndexBuilder.normalize_eva_text(text)
        assert "?" not in normalized
        assert "!" not in normalized

    def test_normalize_eva_text_removes_editorial(self) -> None:
        """Test removal of editorial markers."""
        text = "fachys<comment>.ykal"
        normalized = MismatchIndexBuilder.normalize_eva_text(text)
        assert "<" not in normalized
        assert ">" not in normalized

    def test_normalize_eva_text_normalizes_spaces(self) -> None:
        """Test space normalization."""
        text = "fachys   ykal   ar"
        normalized = MismatchIndexBuilder.normalize_eva_text(text)
        # Multiple spaces should be collapsed
        assert "   " not in normalized

    def test_compute_similarity_identical(self) -> None:
        """Test similarity computation for identical texts."""
        similarity = MismatchIndexBuilder.compute_similarity("abc", "abc")
        assert similarity == 1.0

    def test_compute_similarity_different(self) -> None:
        """Test similarity computation for different texts."""
        similarity = MismatchIndexBuilder.compute_similarity("abc", "xyz")
        assert similarity == 0.0

    def test_compute_similarity_partial(self) -> None:
        """Test similarity computation for partially similar texts."""
        similarity = MismatchIndexBuilder.compute_similarity("abcd", "abce")
        assert 0.0 < similarity < 1.0

    def test_compute_similarity_empty(self) -> None:
        """Test similarity computation with empty text."""
        similarity = MismatchIndexBuilder.compute_similarity("", "abc")
        assert similarity == 0.0
        similarity = MismatchIndexBuilder.compute_similarity("abc", "")
        assert similarity == 0.0

    def test_compare_eva_lines_exact_match(self) -> None:
        """Test comparison of identical lines."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines("fachys.ykal.ar", "fachys.ykal.ar")
        assert status == "exact_match"
        assert agreement is True
        assert score == 1.0

    def test_compare_eva_lines_normalized_match(self) -> None:
        """Test comparison with uncertainty markers."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines("fachys.ykal.ar", "fach?ys.ykal.ar")
        assert status == "normalized_match"
        assert agreement is True

    def test_compare_eva_lines_content_mismatch(self) -> None:
        """Test comparison of different lines."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines(
            "fachys.ykal.ar", "completely.different.text"
        )
        assert status == "content_mismatch"
        assert agreement is False
        assert score is not None and score < 0.5

    def test_compare_eva_lines_zl_missing(self) -> None:
        """Test comparison when ZL is missing."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines(None, "fachys.ykal.ar")
        assert status == "zl_missing"

    def test_compare_eva_lines_it_missing(self) -> None:
        """Test comparison when IT is missing."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines("fachys.ykal.ar", None)
        assert status == "it_missing"

    def test_compare_eva_lines_both_missing(self) -> None:
        """Test comparison when both are missing."""
        builder = MismatchIndexBuilder()
        status, agreement, score = builder.compare_eva_lines(None, None)
        assert status == "both_missing"


class TestTranscriptionLine:
    """Tests for TranscriptionLine dataclass."""

    def test_create_line(self) -> None:
        """Test basic line creation."""
        line = TranscriptionLine(
            page_id="f1r",
            line_number=1,
            line_id="f1r:1",
            text_raw="raw text",
            text_clean="clean text",
            source_id="zl",
        )
        assert line.page_id == "f1r"
        assert line.source_id == "zl"


class TestMismatchIndexIntegration:
    """Integration tests for mismatch index building."""

    @pytest.fixture
    def cache_dir(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory with test files."""
        cache = tmp_path / "cache"
        cache.mkdir()

        # Create minimal ZL test file
        zl_content = """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $P=A>
<f1r.1,@P0>       <%>fachys.ykal.ar.ataiin.shol.shory
<f1r.2,+P0>       sory.ckhar.or.y.kair.chtaiin
"""
        (cache / "ZL3b-n.txt").write_text(zl_content)

        # Create minimal IT test file with same content
        it_content = """#=IVTFF EvaT 1.7
<f1r>      <! $Q=A $P=A>
<f1r.1,@P0>       <%>fachys.ykal.ar.ataiin.shol.shory
<f1r.2,+P0>       sory.ckhar.or.y.kair.chtaiin
"""
        (cache / "IT_ivtff_1a.txt").write_text(it_content)

        return cache

    def test_load_transcription(self, cache_dir: Path) -> None:
        """Test loading a single transcription."""
        builder = MismatchIndexBuilder(cache_dir=cache_dir)
        loaded = builder.load_transcription("zl")
        assert loaded is True
        assert "zl" in builder.transcriptions
        assert len(builder.transcriptions["zl"]) == 2

    def test_load_all_available(self, cache_dir: Path) -> None:
        """Test loading all available transcriptions."""
        builder = MismatchIndexBuilder(cache_dir=cache_dir)
        loaded = builder.load_all_transcriptions()
        assert loaded >= 2  # At least ZL and IT

    def test_build_record(self, cache_dir: Path) -> None:
        """Test building a single mismatch record."""
        builder = MismatchIndexBuilder(cache_dir=cache_dir)
        builder.load_all_transcriptions()

        record = builder.build_record("f1r:1")
        assert record.page_id == "f1r"
        assert record.line_number == 1
        assert record.zl_text is not None
        assert record.status in [
            "exact_match",
            "normalized_match",
            "high_similarity",
            "content_mismatch",
        ]

    def test_build_complete_index(self, cache_dir: Path, tmp_path: Path) -> None:
        """Test building complete mismatch index."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        builder = MismatchIndexBuilder(cache_dir=cache_dir, output_dir=output_dir)
        records = builder.build()

        assert len(records) == 2  # Two lines in test files
        assert all(isinstance(r, MismatchRecord) for r in records)

    def test_export_jsonl(self, cache_dir: Path, tmp_path: Path) -> None:
        """Test JSONL export."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        builder = MismatchIndexBuilder(cache_dir=cache_dir, output_dir=output_dir)
        records = builder.build()

        output_path = builder.export_jsonl(records)
        assert output_path.exists()

        # Verify JSONL format
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 2
            for line in lines:
                record = json.loads(line)
                assert "page_id" in record
                assert "status" in record


class TestMismatchIndexOutput:
    """Tests that verify the actual output file if it exists."""

    @pytest.fixture
    def output_path(self) -> Path:
        """Path to the output mismatch index."""
        return Path(__file__).parent.parent / "output" / "mismatch_index.jsonl"

    def test_output_exists(self, output_path: Path) -> None:
        """Test that output file exists."""
        if not output_path.exists():
            pytest.skip("Mismatch index not built yet")
        assert output_path.exists()

    def test_output_is_valid_jsonl(self, output_path: Path) -> None:
        """Test that output is valid JSONL."""
        if not output_path.exists():
            pytest.skip("Mismatch index not built yet")

        count = 0
        with open(output_path) as f:
            for line in f:
                record = json.loads(line)
                assert isinstance(record, dict)
                count += 1

        assert count > 0

    def test_output_has_required_fields(self, output_path: Path) -> None:
        """Test that output records have required fields."""
        if not output_path.exists():
            pytest.skip("Mismatch index not built yet")

        required_fields = {"page_id", "line_number", "line_id", "status"}

        with open(output_path) as f:
            for line in f:
                record = json.loads(line)
                missing = required_fields - set(record.keys())
                assert not missing, f"Missing fields: {missing}"

    def test_output_statistics_reasonable(self, output_path: Path) -> None:
        """Test that output statistics are reasonable."""
        if not output_path.exists():
            pytest.skip("Mismatch index not built yet")

        count = 0
        statuses: dict[str, int] = {}

        with open(output_path) as f:
            for line in f:
                record = json.loads(line)
                count += 1
                status = record["status"]
                statuses[status] = statuses.get(status, 0) + 1

        # Should have thousands of records
        assert count > 3000

        # Should have multiple status types
        assert len(statuses) >= 2

        # exact_match or high_similarity should be the most common
        assert "exact_match" in statuses or "high_similarity" in statuses
