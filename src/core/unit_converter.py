"""
Project SVARNA — Unit Conversion Engine
=========================================
Converts traditional Indonesian agricultural units to metric KG.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Default conversion table (Traditional → KG)
# These are common Indonesian agricultural units.
# ---------------------------------------------------------------------------
DEFAULT_CONVERSIONS: dict[str, float] = {
    # Standard metric
    "kg": 1.0,
    "kilogram": 1.0,
    "gram": 0.001,
    "g": 0.001,

    # Indonesian traditional
    "kuintal": 100.0,        # 1 kuintal = 100 kg
    "quintal": 100.0,
    "ton": 1000.0,           # 1 ton = 1000 kg
    "karung": 50.0,          # 1 karung (sack) ≈ 50 kg (rice)
    "peti": 25.0,            # 1 peti (crate) ≈ 25 kg (varies by commodity)
    "ikat": 0.5,             # 1 ikat (bundle) ≈ 0.5 kg (leafy vegetables)
    "sisir": 1.5,            # 1 sisir (comb of bananas) ≈ 1.5 kg
    "tandan": 15.0,          # 1 tandan (palm fruit bunch) ≈ 15 kg
    "butir": 0.06,           # 1 butir (egg) ≈ 60 grams
    "ekor": 2.0,             # 1 ekor (chicken) ≈ 2 kg (live weight)
    "liter": 1.0,            # 1 liter ≈ 1 kg (approximate for liquids/grains)
}

# Commodity-specific overrides (some units vary by commodity)
COMMODITY_OVERRIDES: dict[str, dict[str, float]] = {
    "beras": {"karung": 50.0, "liter": 0.85},
    "jagung": {"karung": 40.0, "liter": 0.72},
    "cabai": {"karung": 20.0, "peti": 15.0},
    "tomat": {"peti": 20.0, "karung": 30.0},
    "bawang merah": {"karung": 25.0, "peti": 20.0},
    "bawang putih": {"karung": 25.0},
    "gula pasir": {"karung": 50.0},
    "minyak goreng": {"liter": 0.92},
    "telur": {"butir": 0.06, "peti": 18.0},  # 1 peti telur ≈ 300 butir
    "pisang": {"sisir": 1.5, "tandan": 15.0},
}


class UnitConverter:
    """
    Converts agricultural quantities from local units to metric KG.
    Supports commodity-specific overrides for accuracy.
    """

    def __init__(self, conversions_file: Optional[str] = None):
        self.conversions = DEFAULT_CONVERSIONS.copy()
        self.commodity_overrides = COMMODITY_OVERRIDES.copy()

        if conversions_file and Path(conversions_file).exists():
            self._load_custom(conversions_file)
            logger.info(f"Loaded custom conversions from {conversions_file}")

    def _load_custom(self, filepath: str) -> None:
        """Load additional conversions from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "units" in data:
            self.conversions.update(data["units"])
        if "commodity_overrides" in data:
            for commodity, overrides in data["commodity_overrides"].items():
                if commodity not in self.commodity_overrides:
                    self.commodity_overrides[commodity] = {}
                self.commodity_overrides[commodity].update(overrides)

    def to_kg(
        self,
        value: float,
        unit: str,
        commodity: Optional[str] = None,
    ) -> float:
        """
        Convert a value from a local unit to KG.

        Args:
            value: Quantity in the original unit.
            unit: The unit name (e.g., "kuintal", "karung").
            commodity: Optional commodity for context-specific conversion.

        Returns:
            Equivalent quantity in KG.

        Raises:
            ValueError: If the unit is not recognized.
        """
        unit_lower = unit.strip().lower()
        commodity_lower = commodity.strip().lower() if commodity else None

        # Check commodity-specific override first
        if commodity_lower and commodity_lower in self.commodity_overrides:
            overrides = self.commodity_overrides[commodity_lower]
            if unit_lower in overrides:
                factor = overrides[unit_lower]
                logger.debug(
                    f"Converting {value} {unit} → KG "
                    f"(commodity override: {commodity}, factor={factor})"
                )
                return value * factor

        # Fall back to default conversion
        if unit_lower in self.conversions:
            factor = self.conversions[unit_lower]
            logger.debug(f"Converting {value} {unit} → KG (factor={factor})")
            return value * factor

        raise ValueError(
            f"Unknown unit '{unit}'. "
            f"Known units: {', '.join(sorted(self.conversions.keys()))}"
        )

    def price_per_kg(
        self,
        total_price: float,
        value: float,
        unit: str,
        commodity: Optional[str] = None,
    ) -> float:
        """
        Calculate price per KG.

        Args:
            total_price: Total price for the given quantity.
            value: Quantity in the original unit.
            unit: Original unit.
            commodity: Optional commodity for context-specific conversion.

        Returns:
            Price per KG in IDR.
        """
        kg = self.to_kg(value, unit, commodity)
        if kg <= 0:
            return 0.0
        return total_price / kg

    def list_units(self) -> list[str]:
        """Return all known unit names."""
        return sorted(self.conversions.keys())

    def list_commodities(self) -> list[str]:
        """Return all commodities with specific overrides."""
        return sorted(self.commodity_overrides.keys())
