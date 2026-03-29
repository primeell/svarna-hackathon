"""
Tests for UnitConverter — Indonesian agricultural unit conversion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.core.unit_converter import UnitConverter


@pytest.fixture
def converter():
    return UnitConverter()


class TestBasicConversions:
    def test_kg_identity(self, converter):
        assert converter.to_kg(10, "kg") == 10.0

    def test_kuintal(self, converter):
        assert converter.to_kg(5, "kuintal") == 500.0

    def test_ton(self, converter):
        assert converter.to_kg(2, "ton") == 2000.0

    def test_karung_default(self, converter):
        assert converter.to_kg(1, "karung") == 50.0

    def test_gram(self, converter):
        assert converter.to_kg(1000, "gram") == 1.0


class TestCommodityOverrides:
    def test_beras_karung(self, converter):
        """Beras (rice) karung should still be 50 kg."""
        assert converter.to_kg(1, "karung", "beras") == 50.0

    def test_cabai_karung(self, converter):
        """Cabai (chili) karung is only 20 kg."""
        assert converter.to_kg(1, "karung", "cabai") == 20.0

    def test_jagung_karung(self, converter):
        """Jagung (corn) karung is 40 kg."""
        assert converter.to_kg(1, "karung", "jagung") == 40.0


class TestPricePerKg:
    def test_simple_price(self, converter):
        # 5 kuintal at 6,000,000 IDR total → 12,000 IDR/kg
        price = converter.price_per_kg(6_000_000, 5, "kuintal", "beras")
        assert price == 12_000.0

    def test_zero_volume(self, converter):
        price = converter.price_per_kg(100_000, 0, "kg")
        assert price == 0.0


class TestUnknownUnit:
    def test_raises_on_unknown(self, converter):
        with pytest.raises(ValueError, match="Unknown unit"):
            converter.to_kg(10, "bushel")


class TestCaseInsensitive:
    def test_upper_case(self, converter):
        assert converter.to_kg(1, "KUINTAL") == 100.0

    def test_mixed_case(self, converter):
        assert converter.to_kg(1, "Karung") == 50.0


class TestListMethods:
    def test_list_units(self, converter):
        units = converter.list_units()
        assert "kg" in units
        assert "kuintal" in units

    def test_list_commodities(self, converter):
        commodities = converter.list_commodities()
        assert "beras" in commodities
        assert "cabai" in commodities
