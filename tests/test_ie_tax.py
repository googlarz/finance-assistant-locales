"""
Tests for the Irish (ie) tax locale.

Validates income tax + USC + PRSI calculations against known scenarios.
Uses the same LocaleContext pattern as test_uk_tax.py.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from context import LocaleContext
from ie import calculate_tax
from ie.tax_rules import calculate_income_tax, calculate_usc, get_tax_year_rules
from ie.social_contributions import get_social_contributions


SUPPORTED_YEARS = [2024, 2025, 2026]


def _make_ctx(gross: float, year: int, employment_type: str = "employed",
              married: bool = False) -> LocaleContext:
    return LocaleContext(
        tax_year=year,
        employment_type=employment_type,
        annual_gross=gross,
        married=married,
    )


class TestTaxRulesSanity:
    """Basic sanity checks on the rules data."""

    @pytest.mark.parametrize("year", SUPPORTED_YEARS)
    def test_standard_rate_band_positive(self, year):
        rules = get_tax_year_rules(year)
        assert rules["standard_rate_band_single"] > 0

    @pytest.mark.parametrize("year", SUPPORTED_YEARS)
    def test_rates_are_valid(self, year):
        rules = get_tax_year_rules(year)
        assert rules["standard_rate"] == 0.20
        assert rules["higher_rate"] == 0.40

    @pytest.mark.parametrize("year", SUPPORTED_YEARS)
    def test_usc_bands_progressive(self, year):
        rules = get_tax_year_rules(year)
        bands = rules["usc_bands"]
        for i in range(len(bands) - 1):
            if bands[i][0] is not None and bands[i + 1][0] is not None:
                assert bands[i][0] < bands[i + 1][0]

    @pytest.mark.parametrize("year", SUPPORTED_YEARS)
    def test_credits_positive(self, year):
        rules = get_tax_year_rules(year)
        assert rules["personal_credit_single"] > 0
        assert rules["employee_credit"] > 0


class TestIncomeTax:
    """Test income tax calculation (before credits)."""

    def test_zero_income(self):
        rules = get_tax_year_rules(2025)
        assert calculate_income_tax(0, rules) == 0.0

    def test_standard_band_only_2025(self):
        rules = get_tax_year_rules(2025)
        # €40,000 is within the €44,000 standard band
        tax = calculate_income_tax(40_000, rules)
        assert tax == 40_000 * 0.20  # €8,000

    def test_higher_rate_2025(self):
        rules = get_tax_year_rules(2025)
        # €60,000: first €44,000 at 20%, remaining €16,000 at 40%
        tax = calculate_income_tax(60_000, rules)
        expected = 44_000 * 0.20 + 16_000 * 0.40  # 8,800 + 6,400 = 15,200
        assert tax == expected


class TestUSC:
    """Test Universal Social Charge calculation."""

    def test_exempt_below_threshold(self):
        rules = get_tax_year_rules(2025)
        # Income ≤ €13,000 is exempt
        assert calculate_usc(13_000, rules) == 0.0
        assert calculate_usc(12_000, rules) == 0.0

    def test_not_exempt_above_threshold(self):
        rules = get_tax_year_rules(2025)
        assert calculate_usc(14_000, rules) > 0.0

    def test_usc_40k_2025(self):
        rules = get_tax_year_rules(2025)
        # €40,000:
        # Band 1: €12,012 × 0.5% = €60.06
        # Band 2: €15,370 (€27,382 - €12,012) × 2% = €307.40
        # Band 3: €12,618 (€40,000 - €27,382) × 3% = €378.54
        # Total = €745.99 → rounded €746.00
        usc = calculate_usc(40_000, rules)
        assert 740 < usc < 755  # Allow small rounding variance


class TestPRSI:
    """Test PRSI calculations."""

    def test_below_threshold_no_prsi(self):
        # Weekly income ≤ €352 → no employee PRSI
        # €352 × 52 = €18,304
        result = get_social_contributions(18_000, 2025)
        assert result["prsi_employee"] == 0.0

    def test_class_a_above_threshold(self):
        result = get_social_contributions(50_000, 2025)
        # 4% of €50,000 = €2,000
        assert result["prsi_employee"] == 2_000.0
        assert result["class"] == "A"

    def test_class_s_self_employed(self):
        result = get_social_contributions(80_000, 2025, self_employed=True)
        # 4% of €80,000 = €3,200
        assert result["prsi_employee"] == 3_200.0
        assert result["class"] == "S"

    def test_class_s_minimum(self):
        # Self-employed with low income: minimum €500
        result = get_social_contributions(10_000, 2025, self_employed=True)
        assert result["prsi_employee"] == 500.0


class TestCalculateTax:
    """Integration tests for the full calculate_tax function."""

    def test_basic_employee_50k_2025(self):
        """Single employee on €50,000 in 2025."""
        ctx = _make_ctx(50_000, 2025)
        result = calculate_tax(ctx)

        assert result["gross"] == 50_000
        assert result["currency"] == "EUR"
        assert result["tax_year"] == 2025

        # Income tax: €50,000 at 20%/40% = (44,000×0.20 + 6,000×0.40) = 11,200
        # Credits: personal 2,000 + PAYE 2,000 = 4,000
        # Income tax after credits: 11,200 - 4,000 = 7,200
        assert result["income_tax"] == 7_200.0

        # USC: should be positive
        assert result["usc"] > 0

        # PRSI: 4% of 50,000 = 2,000
        assert result["prsi_employee"] == 2_000.0

        # Net should be gross minus all deductions
        expected_net = 50_000 - result["income_tax"] - result["usc"] - result["prsi_employee"]
        assert abs(result["net"] - expected_net) < 1.0

        # Effective rate should be between 20% and 50%
        assert 0.20 < result["effective_rate"] < 0.50

    def test_basic_employee_30k_2025(self):
        """Single employee on €30,000 — fully within standard rate band."""
        ctx = _make_ctx(30_000, 2025)
        result = calculate_tax(ctx)

        # Income tax: 30,000 × 20% = 6,000 - credits (4,000) = 2,000
        assert result["income_tax"] == 2_000.0

    def test_high_earner_100k_2025(self):
        """Single employee on €100,000."""
        ctx = _make_ctx(100_000, 2025)
        result = calculate_tax(ctx)

        # Income tax: (44,000×0.20 + 56,000×0.40) = 8,800 + 22,400 = 31,200
        # Credits: 4,000
        # After credits: 27,200
        assert result["income_tax"] == 27_200.0

        # Total tax burden should be significant
        assert result["effective_rate"] > 0.35

    def test_self_employed_60k_2025(self):
        """Self-employed person on €60,000."""
        ctx = _make_ctx(60_000, 2025, employment_type="self_employed")
        result = calculate_tax(ctx)

        # Gets earned income credit instead of PAYE credit (same value in 2025)
        # Income tax: (44,000×0.20 + 16,000×0.40) = 8,800 + 6,400 = 15,200
        # Credits: personal 2,000 + earned income 2,000 = 4,000
        # After credits: 11,200
        assert result["income_tax"] == 11_200.0
        assert result["is_self_employed"] is True

    def test_zero_income(self):
        ctx = _make_ctx(0, 2025)
        result = calculate_tax(ctx)
        assert result["net"] == 0.0
        assert result["total_tax"] == 0.0

    def test_very_low_income_no_tax(self):
        """Income low enough that credits exceed gross tax and USC exempt."""
        ctx = _make_ctx(12_000, 2025)
        result = calculate_tax(ctx)
        # 12,000 × 20% = 2,400. Credits = 4,000. Tax = 0.
        assert result["income_tax"] == 0.0
        # USC exempt (≤ €13,000)
        assert result["usc"] == 0.0

    @pytest.mark.parametrize("year", SUPPORTED_YEARS)
    def test_net_less_than_gross(self, year):
        ctx = _make_ctx(50_000, year)
        result = calculate_tax(ctx)
        assert result["net"] < result["gross"]
        assert result["net"] > 0

    def test_marginal_rate_standard_band(self):
        """Marginal rate for someone in the standard band (2025)."""
        ctx = _make_ctx(35_000, 2025)
        result = calculate_tax(ctx)
        # 20% IT + 2% USC (in band 2) + 4% PRSI = 26%
        assert 0.24 <= result["marginal_rate"] <= 0.28

    def test_marginal_rate_higher_band(self):
        """Marginal rate for someone in the higher band (2025)."""
        ctx = _make_ctx(80_000, 2025)
        result = calculate_tax(ctx)
        # 40% IT + 3% USC (band 3) + 4% PRSI = 47%
        # (or 8% USC if above €70,044)
        assert 0.45 <= result["marginal_rate"] <= 0.52

    def test_confidence_definitive_for_known_year(self):
        ctx = _make_ctx(50_000, 2025)
        result = calculate_tax(ctx)
        assert result["confidence"] == "Definitive"

    def test_confidence_likely_for_future_year(self):
        ctx = _make_ctx(50_000, 2030)
        result = calculate_tax(ctx)
        assert result["confidence"] == "Likely"
