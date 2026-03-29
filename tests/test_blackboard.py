"""
Tests for Blackboard — shared state manager.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.core.blackboard import Blackboard


@pytest.fixture
def bb(tmp_path):
    """Create a Blackboard with a temp DB."""
    db_path = str(tmp_path / "test_blackboard.db")
    return Blackboard(db_path=db_path)


class TestWrite:
    def test_write_and_read(self, bb):
        bb.write("T-001", "TestAgent", "transcriptions", {"text": "hello"})
        entries = bb.read("transcriptions")
        assert len(entries) == 1
        assert entries[0]["payload"]["text"] == "hello"

    def test_write_multiple(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "first"})
        bb.write("T-002", "Agent1", "transcriptions", {"text": "second"})
        entries = bb.read("transcriptions")
        assert len(entries) == 2


class TestRead:
    def test_read_by_id(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "test"})
        entry = bb.read_by_id("T-001")
        assert entry is not None
        assert entry["payload"]["text"] == "test"

    def test_read_by_id_not_found(self, bb):
        entry = bb.read_by_id("NONEXISTENT")
        assert entry is None

    def test_read_latest(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "first"})
        bb.write("T-002", "Agent1", "transcriptions", {"text": "second"})
        latest = bb.read_latest("transcriptions")
        assert latest["payload"]["text"] == "second"

    def test_read_empty_type(self, bb):
        entries = bb.read("nonexistent_type")
        assert entries == []


class TestStats:
    def test_stats(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "a"})
        bb.write("R-001", "Agent2", "parsed_reports", {"commodity": "beras"})
        stats = bb.get_stats()
        assert stats["transcriptions"] == 1
        assert stats["parsed_reports"] == 1


class TestHistory:
    def test_query_history(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "a"})
        history = bb.query_history("transcriptions")
        assert len(history) >= 1


class TestClearMemory:
    def test_clear(self, bb):
        bb.write("T-001", "Agent1", "transcriptions", {"text": "a"})
        bb.clear_memory()
        entries = bb.read("transcriptions")
        assert entries == []
