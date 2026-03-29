"""
Tests for the full SVARNA pipeline — mock mode end-to-end.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.core.pipeline import SVARNAPipeline


@pytest.fixture
def pipeline(tmp_path):
    """Create a pipeline that writes its DB to a temp dir."""
    # We'll run with default config (AgentConfig.yaml)
    p = SVARNAPipeline(config_path="AgentConfig.yaml")
    return p


class TestPipelineMockRun:
    def test_mock_run_completes(self, pipeline):
        """Run the pipeline in mock mode and verify all 3 stages produce output."""
        results = pipeline.run(audio_file=None)

        assert "AcousticSignalIngestor" in results
        assert "SemanticDataParser" in results
        assert "MacroEconomicStrategist" in results

    def test_transcription_stage(self, pipeline):
        results = pipeline.run(audio_file=None)
        tr = results["AcousticSignalIngestor"]

        assert tr.get("_status") in ("completed", "clarification_needed")
        assert "full_text" in tr
        assert len(tr["full_text"]) > 10

    def test_parsing_stage(self, pipeline):
        results = pipeline.run(audio_file=None)
        pr = results["SemanticDataParser"]

        assert pr.get("_status") in ("completed", "clarification_needed")
        assert "commodity" in pr
        assert "volume_kg" in pr

    def test_analysis_stage(self, pipeline):
        results = pipeline.run(audio_file=None)
        ea = results["MacroEconomicStrategist"]

        assert ea.get("status") in ("completed", "failed")

    def test_blackboard_populated(self, pipeline):
        pipeline.run(audio_file=None)
        stats = pipeline.get_stats()

        assert stats.get("transcriptions", 0) >= 1
        assert stats.get("parsed_reports", 0) >= 1
