"""
Tests for Pydantic schemas — data contract validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pydantic import ValidationError
from src.models.schemas import (
    FarmerReport,
    GeoLocation,
    TranscriptionResult,
    TranscriptionSegment,
    InflationRiskAssessment,
    PriceDeviation,
    RiskLevel,
    PipelineStatus,
)


class TestTranscriptionResult:
    def test_valid_transcription(self):
        tr = TranscriptionResult(
            id="TR-001",
            audio_file="test.wav",
            full_text="sample text",
            segments=[],
            noise_confidence=0.9,
            duration_seconds=5.0,
        )
        assert tr.id == "TR-001"
        assert tr.status == PipelineStatus.COMPLETED

    def test_noise_confidence_bounds(self):
        with pytest.raises(ValidationError):
            TranscriptionResult(
                id="TR-002",
                audio_file="test.wav",
                full_text="text",
                noise_confidence=1.5,  # Out of range
                duration_seconds=5.0,
            )


class TestGeoLocation:
    def test_valid_location(self):
        geo = GeoLocation(latitude=-6.75, longitude=107.0, village_name="Sukamaju")
        assert geo.village_name == "Sukamaju"

    def test_invalid_latitude(self):
        with pytest.raises(ValidationError):
            GeoLocation(latitude=100.0, longitude=0.0)  # lat > 90


class TestFarmerReport:
    def test_valid_report(self):
        report = FarmerReport(
            id="FR-001",
            transcription_id="TR-001",
            commodity="beras",
            volume=5.0,
            local_unit="kuintal",
            volume_kg=500.0,
            asking_price=6_000_000,
            price_per_kg=12_000.0,
            geo_location=GeoLocation(latitude=-6.75, longitude=107.0),
            extraction_confidence=0.9,
        )
        assert report.commodity == "beras"  # Lowercased by validator
        assert report.volume_kg == 500.0

    def test_empty_commodity_rejected(self):
        with pytest.raises(ValidationError):
            FarmerReport(
                id="FR-002",
                transcription_id="TR-001",
                commodity="   ",  # Empty after strip
                volume=5.0,
                local_unit="kg",
                volume_kg=5.0,
                asking_price=0,
                price_per_kg=0,
                geo_location=GeoLocation(latitude=0, longitude=0),
                extraction_confidence=0.5,
            )

    def test_zero_volume_rejected(self):
        with pytest.raises(ValidationError):
            FarmerReport(
                id="FR-003",
                transcription_id="TR-001",
                commodity="cabai",
                volume=0.0,  # gt=0 constraint
                local_unit="kg",
                volume_kg=1.0,
                asking_price=0,
                price_per_kg=0,
                geo_location=GeoLocation(latitude=0, longitude=0),
                extraction_confidence=0.5,
            )


class TestInflationRiskAssessment:
    def test_valid_assessment(self):
        iri = InflationRiskAssessment(
            id="IRI-001",
            report_id="FR-001",
            commodity="beras",
            region="Cianjur",
            price_deviation=PriceDeviation(
                commodity="beras",
                p_local=14000,
                p_national=13500,
                deviation=0.037,
                deviation_pct=3.7,
            ),
            iri_score=0.037,
            risk_level=RiskLevel.LOW,
        )
        assert iri.risk_level == RiskLevel.LOW
