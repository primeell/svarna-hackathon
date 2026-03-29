"""
Project SVARNA — Agent 3: MacroEconomicStrategist
====================================================
Calculates Inflation Risk Index (IRI) and generates surplus/deficit alerts.
Pure analytical agent — no LLM needed.
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.blackboard import Blackboard
from src.models.schemas import (
    AlertType,
    EconomicAlert,
    GeoLocation,
    InflationRiskAssessment,
    LogisticsMatch,
    PipelineStatus,
    PriceDeviation,
    RiskLevel,
)


class MacroEconomicStrategist(BaseAgent):
    """
    Agent 3: National economic intelligence and inflation risk analysis.
    
    Hardware: CPU (NumPy/Pandas analytics)
    Compares local prices against PIHPS national reference data.
    """

    def __init__(self, config: dict, blackboard: Blackboard):
        super().__init__(
            name="MacroEconomicStrategist",
            config=config,
            blackboard=blackboard,
        )
        self._national_prices: dict[str, float] = {}
        self._alert_threshold = 0.15

    def initialize(self) -> None:
        """Load national PIHPS reference prices."""
        analytics_config = self.config.get("analytics", {})
        self._alert_threshold = (
            analytics_config.get("price_deviation", {}).get("alert_threshold", 0.15)
        )

        ref_data = self.config.get("reference_data", {})
        csv_path = ref_data.get("pihps_csv", "data/pihps_reference/sample_prices.csv")

        self._national_prices = self._load_pihps(csv_path)
        logger.info(
            f"[{self.name}] Loaded {len(self._national_prices)} national prices. "
            f"Alert threshold: {self._alert_threshold:.0%}"
        )

    def _load_pihps(self, csv_path: str) -> dict[str, float]:
        """Load national reference prices from CSV."""
        prices = {}
        path = Path(csv_path)

        if not path.exists():
            logger.warning(f"[{self.name}] PIHPS CSV not found: {path}. Using defaults.")
            return self._default_prices()

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    commodity = row.get("commodity", "").strip().lower()
                    price_str = row.get("price_per_kg", "0")
                    if commodity and price_str:
                        prices[commodity] = float(price_str)
        except Exception as e:
            logger.error(f"[{self.name}] Error reading PIHPS CSV: {e}")
            return self._default_prices()

        return prices

    @staticmethod
    def _default_prices() -> dict[str, float]:
        """Fallback national average prices (IDR per KG, Q1 2026)."""
        return {
            "beras": 13500.0,
            "cabai": 45000.0,
            "cabai rawit": 50000.0,
            "cabai merah": 42000.0,
            "tomat": 12000.0,
            "bawang merah": 35000.0,
            "bawang putih": 32000.0,
            "jagung": 6500.0,
            "kedelai": 11000.0,
            "gula pasir": 17500.0,
            "minyak goreng": 18000.0,
            "telur": 28000.0,
            "daging sapi": 135000.0,
            "daging ayam": 38000.0,
        }

    def process(self, input_data: Any) -> dict:
        """
        Analyze a farmer report against national prices.
        
        Args:
            input_data: FarmerReport dict or None (reads from blackboard).
        """
        if input_data and isinstance(input_data, dict) and "commodity" in input_data:
            report = input_data
        else:
            latest = self.blackboard.read_latest("parsed_reports")
            if not latest:
                return {"status": PipelineStatus.FAILED.value, "error": "No report found"}
            report = latest["payload"]

        commodity = report.get("commodity", "unknown")
        price_per_kg = report.get("price_per_kg", 0.0)
        report_id = report.get("id", "unknown")
        geo = report.get("geo_location", {})
        region = geo.get("district", "Unknown") or "Unknown"

        # Get national reference price
        p_national = self._national_prices.get(commodity)
        if p_national is None or p_national <= 0:
            logger.warning(
                f"[{self.name}] No national price for '{commodity}'. Skipping."
            )
            return {
                "status": PipelineStatus.COMPLETED.value,
                "message": f"No national reference for {commodity}",
                "commodity": commodity,
                "alerts": [],
            }

        # Calculate IRI
        deviation = self._calculate_deviation(price_per_kg, p_national)
        scarcity_factor = self._estimate_scarcity_factor(commodity, region)
        iri_score = deviation * scarcity_factor
        risk_level = self._classify_risk(abs(iri_score))

        price_dev = PriceDeviation(
            commodity=commodity,
            p_local=price_per_kg,
            p_national=p_national,
            deviation=deviation,
            deviation_pct=deviation * 100,
        )

        assessment_id = f"IRI-{uuid.uuid4().hex[:8].upper()}"
        assessment = InflationRiskAssessment(
            id=assessment_id,
            report_id=report_id,
            commodity=commodity,
            region=region,
            price_deviation=price_dev,
            regional_scarcity_factor=scarcity_factor,
            iri_score=iri_score,
            risk_level=risk_level,
            timestamp=datetime.now(),
        )

        # Generate alerts if threshold exceeded
        alerts = []
        if abs(deviation) >= self._alert_threshold:
            alert = self._generate_alert(assessment, report)
            alerts.append(alert.model_dump(mode="json"))

        result = {
            "id": assessment_id,
            "report_id": report_id,
            "commodity": commodity,
            "iri_assessment": assessment.model_dump(mode="json"),
            "alerts": alerts,
            "status": PipelineStatus.COMPLETED.value,
        }

        return result

    @staticmethod
    def _calculate_deviation(p_local: float, p_national: float) -> float:
        """Calculate price deviation: (P_local - P_national) / P_national."""
        if p_national <= 0:
            return 0.0
        return (p_local - p_national) / p_national

    @staticmethod
    def _estimate_scarcity_factor(commodity: str, region: str) -> float:
        """
        Estimate regional scarcity factor.
        In production, this would use historical supply data.
        For now, returns 1.0 (neutral).
        """
        # TODO: integrate real supply/demand data per region
        return 1.0

    @staticmethod
    def _classify_risk(abs_iri: float) -> RiskLevel:
        """Classify IRI score into risk levels."""
        if abs_iri < 0.10:
            return RiskLevel.LOW
        elif abs_iri < 0.25:
            return RiskLevel.MODERATE
        elif abs_iri < 0.50:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_alert(
        self, assessment: InflationRiskAssessment, report: dict
    ) -> EconomicAlert:
        """Generate an economic alert from an IRI assessment."""
        deviation_pct = assessment.price_deviation.deviation_pct
        commodity = assessment.commodity
        region = assessment.region

        if deviation_pct > 0:
            alert_type = AlertType.PRICE_SPIKE
            title = f"⚠️ {commodity.title()} Price Spike in {region}"
            description = (
                f"{commodity.title()} is priced {deviation_pct:+.1f}% above "
                f"the national average in {region}. "
                f"Local: Rp {assessment.price_deviation.p_local:,.0f}/kg vs "
                f"National: Rp {assessment.price_deviation.p_national:,.0f}/kg. "
                f"Risk Level: {assessment.risk_level.value.upper()}"
            )
        else:
            alert_type = AlertType.SURPLUS
            title = f"📉 {commodity.title()} Surplus Detected in {region}"
            description = (
                f"{commodity.title()} is priced {deviation_pct:+.1f}% below "
                f"the national average in {region}, indicating a potential surplus. "
                f"Consider logistics matchmaking to deficit areas."
            )

        return EconomicAlert(
            id=f"ALR-{uuid.uuid4().hex[:8].upper()}",
            alert_type=alert_type,
            risk_level=assessment.risk_level,
            title=title,
            description=description,
            commodity=commodity,
            iri_assessment=assessment,
            timestamp=datetime.now(),
        )

    def validate(self, result: dict) -> tuple[bool, list[str]]:
        """Validate analysis output."""
        issues = []

        if result.get("status") == PipelineStatus.FAILED.value:
            issues.append(f"Analysis failed: {result.get('error', 'unknown')}")
            return False, issues

        assessment = result.get("iri_assessment")
        if assessment:
            iri = assessment.get("iri_score", 0)
            if abs(iri) > 5.0:
                issues.append(f"IRI score seems unrealistic ({iri:.2f})")

        return len(issues) == 0, issues

    def write_output(self, result: dict) -> None:
        """Write economic analysis to the blackboard."""
        entry_id = result.get("id", f"ECO-{uuid.uuid4().hex[:8]}")

        self.blackboard.write(
            entry_id=entry_id,
            agent_source=self.name,
            entry_type="economic_alerts",
            payload=result,
        )

        # Also write individual alerts
        for alert in result.get("alerts", []):
            self.blackboard.write(
                entry_id=alert.get("id", f"ALR-{uuid.uuid4().hex[:8]}"),
                agent_source=self.name,
                entry_type="economic_alerts",
                payload=alert,
            )
