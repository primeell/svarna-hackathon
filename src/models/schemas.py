"""
Project SVARNA — Pydantic Data Contracts
=========================================
Strict type-hinted schemas for every data handoff in the pipeline.
Enforces JSON-Schema validation at runtime.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    SURPLUS = "surplus"
    DEFICIT = "deficit"
    PRICE_SPIKE = "price_spike"
    INFLATION_RISK = "inflation_risk"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CLARIFICATION_NEEDED = "clarification_needed"


# ---------------------------------------------------------------------------
# Agent 1 Output: Transcription
# ---------------------------------------------------------------------------

class TranscriptionSegment(BaseModel):
    """A single timestamped segment from Whisper."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    confidence: float = Field(..., ge=0.0, le=1.0)


class TranscriptionResult(BaseModel):
    """Output schema for AcousticSignalIngestor."""
    id: str = Field(..., description="Unique transcription ID")
    audio_file: str = Field(..., description="Source audio file path")
    full_text: str = Field(..., description="Complete transcription text")
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    language: str = Field(default="id", description="Detected language code")
    noise_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence that audio is clean (1.0 = no noise)"
    )
    duration_seconds: float = Field(..., ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    status: PipelineStatus = Field(default=PipelineStatus.COMPLETED)


# ---------------------------------------------------------------------------
# Agent 2 Output: Parsed Farmer Report
# ---------------------------------------------------------------------------

class GeoLocation(BaseModel):
    """Geographic coordinates of the farmer's location."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    village_name: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None


class FarmerReport(BaseModel):
    """Structured entity extraction from farmer voice note."""
    id: str = Field(..., description="Unique report ID")
    transcription_id: str = Field(..., description="Link to source transcription")
    commodity: str = Field(..., description="Crop/commodity name (e.g., 'beras', 'cabai')")
    volume: float = Field(..., gt=0.0, description="Quantity in original unit")
    local_unit: str = Field(..., description="Original unit (e.g., 'kuintal', 'karung')")
    volume_kg: float = Field(..., gt=0.0, description="Normalized volume in KG")
    asking_price: float = Field(..., ge=0.0, description="Price per unit in IDR")
    price_per_kg: float = Field(..., ge=0.0, description="Normalized price per KG in IDR")
    geo_location: GeoLocation
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    status: PipelineStatus = Field(default=PipelineStatus.COMPLETED)
    raw_text: Optional[str] = Field(None, description="Original transcription text")

    @field_validator("commodity")
    @classmethod
    def commodity_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Commodity name cannot be empty")
        return v.strip().lower()


# ---------------------------------------------------------------------------
# Agent 3 Output: Economic Analysis
# ---------------------------------------------------------------------------

class PriceDeviation(BaseModel):
    """Price comparison between local and national reference."""
    commodity: str
    p_local: float = Field(..., description="Local farm-gate price per KG (IDR)")
    p_national: float = Field(..., description="National PIHPS reference price per KG (IDR)")
    deviation: float = Field(..., description="(P_local - P_national) / P_national")
    deviation_pct: float = Field(..., description="Deviation as percentage")


class InflationRiskAssessment(BaseModel):
    """IRI calculation result for a single commodity + region."""
    id: str
    report_id: str = Field(..., description="Link to source FarmerReport")
    commodity: str
    region: str
    price_deviation: PriceDeviation
    regional_scarcity_factor: float = Field(default=1.0, ge=0.0)
    iri_score: float = Field(..., description="Inflation Risk Index")
    risk_level: RiskLevel
    timestamp: datetime = Field(default_factory=datetime.now)


class LogisticsMatch(BaseModel):
    """Surplus-to-deficit matchmaking recommendation."""
    id: str
    commodity: str
    surplus_location: GeoLocation
    surplus_volume_kg: float
    deficit_location: GeoLocation
    deficit_severity: RiskLevel
    price_differential_pct: float
    recommended_action: str
    timestamp: datetime = Field(default_factory=datetime.now)


class EconomicAlert(BaseModel):
    """Top-level alert dispatched by the MacroEconomicStrategist."""
    id: str
    alert_type: AlertType
    risk_level: RiskLevel
    title: str
    description: str
    commodity: str
    iri_assessment: Optional[InflationRiskAssessment] = None
    logistics_match: Optional[LogisticsMatch] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Blackboard State
# ---------------------------------------------------------------------------

class BlackboardEntry(BaseModel):
    """Generic wrapper for any data on the blackboard."""
    entry_id: str
    agent_source: str
    entry_type: str  # "transcription" | "farmer_report" | "economic_alert"
    payload: dict
    timestamp: datetime = Field(default_factory=datetime.now)
