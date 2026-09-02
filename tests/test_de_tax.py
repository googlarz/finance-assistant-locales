"""Tests for German tax calculations using LocaleContext directly."""
import pytest
from context import LocaleContext, ReceiptItem, ChildInfo
from de import calculate_tax
from de.tax_rules import TAX_YEAR_RULES, calculate_income_tax, calculate_soli

SUPPORTED_YEARS = [2024, 2025, 2026]


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_zero_tax_below_grundfreibetrag(year):
    grundfreibetrag = TAX_YEAR_RULES[year]["grundfreibetrag"]
    assert calculate_income_tax(grundfreibetrag, year) == 0.0
    assert calculate_income_tax(grundfreibetrag - 1, year) == 0.0


def test_tax_increases_with_income():
    tax_low = calculate_income_tax(30000, 2025)
    tax_mid = calculate_income_tax(60000, 2025)
    tax_high = calculate_income_tax(100000, 2025)
    assert tax_low < tax_mid < tax_high


def test_soli_zero_below_threshold():
    for year in SUPPORTED_YEARS:
        threshold = TAX_YEAR_RULES[year]["soli_freigrenze_single"]
        assert calculate_soli(threshold, year) == 0.0


def test_soli_positive_above_threshold():
    for year in SUPPORTED_YEARS:
        threshold = TAX_YEAR_RULES[year]["soli_freigrenze_single"]
        assert calculate_soli(threshold + 5000, year) > 0.0


def test_calculate_tax_salaried_employee():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="I",
        region="Berlin",
        homeoffice_days_per_week=3.0,
    )
    result = calculate_tax(ctx)
    assert "estimated_refund" in result
    assert "confidence_pct" in result
    assert "breakdown" in result
    assert result["confidence_pct"] > 0
    # A salaried employee with homeoffice should have a reasonable refund range
    assert -10000 < result["estimated_refund"] < 10000


def test_calculate_tax_married_splitting():
    ctx_single = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="I",
        married=False,
    )
    ctx_married = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="III",
        married=True,
    )
    result_single = calculate_tax(ctx_single)
    result_married = calculate_tax(ctx_married)
    # Married splitting (Steuerklasse III) should result in lower tax due
    assert result_married["breakdown"]["estimated_tax"] < result_single["breakdown"]["estimated_tax"]


def test_calculate_tax_freelancer():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="freelancer",
        annual_gross=80000.0,
        tax_class="I",
    )
    result = calculate_tax(ctx)
    assert "estimated_refund" in result
    assert result["confidence_pct"] < 100  # freelance reduces confidence


def test_calculate_tax_with_ruerup():
    ctx_without = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="I",
    )
    ctx_with = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="I",
        ruerup=True,
        ruerup_contribution=5000.0,
    )
    result_without = calculate_tax(ctx_without)
    result_with = calculate_tax(ctx_with)
    # Rürup contribution should reduce tax due and increase refund
    assert result_with["breakdown"]["estimated_tax"] < result_without["breakdown"]["estimated_tax"]


def test_soli_married_freigrenze_doubled():
    """Married filers get double the Soli Freigrenze (§3 SolzG joint assessment).

    income_tax of €18,200 is above the single threshold (~€18,130–€20,350)
    but below the doubled married threshold — so single pays Soli, married pays none.
    We use 2024 rules (single Freigrenze = €18,130).
    """
    # Single filer: income_tax €19,000 > single Freigrenze €18,130 → Soli charged
    soli_single = calculate_soli(19_000, year=2024, married=False)
    assert soli_single > 0.0, "Single filer above Freigrenze should pay Soli"

    # Married filer: same income_tax €19,000 < doubled Freigrenze €36,260 → no Soli
    soli_married = calculate_soli(19_000, year=2024, married=True)
    assert soli_married == 0.0, "Married filer below doubled Freigrenze should pay no Soli"

    # Both pay Soli when income_tax is above the doubled threshold
    soli_both = calculate_soli(40_000, year=2024, married=True)
    assert soli_both > 0.0, "Married filer above doubled Freigrenze should pay Soli"


def test_all_2026_params_filled():
    ctx = LocaleContext(
        tax_year=2026,
        employment_type="employed",
        annual_gross=65000.0,
        tax_class="I",
        homeoffice_days_per_week=3.0,
    )
    result = calculate_tax(ctx)
    bd = result["breakdown"]
    critical_keys = [
        "gross_income", "total_werbungskosten", "total_sonderausgaben",
        "zu_versteuerndes_einkommen", "estimated_tax", "total_tax_due",
    ]
    for key in critical_keys:
        assert bd[key] is not None, f"breakdown.{key} is None"


def test_kinderfreibetrag_guenstigerpruefung_adds_back_kindergeld():
    """Regression: § 31 EStG requires Kindergeld already received to be
    added back when the Kinderfreibetrag proves more favorable — it isn't
    free once the Freibetrag is used instead. Was dropped entirely,
    overstating the refund by exactly the annual Kindergeld amount."""
    from de.tax_rules import calculate_income_tax as _cit, TAX_YEAR_RULES

    p = TAX_YEAR_RULES[2025]
    kindergeld_annual = 1 * p["kindergeld_per_child"] * 12
    kinderfreibetrag_total = 1 * (p["kinderfreibetrag_child"] + p["kinderfreibetrag_bea"]) * 2  # married: both parents

    ctx = LocaleContext(
        tax_year=2025, employment_type="employed", annual_gross=600_000.0,
        married=True, tax_class="III",
        children=[ChildInfo(birth_year=2015)],
    )
    result = calculate_tax(ctx)
    tax = result["breakdown"]["estimated_tax"]
    zve = result["breakdown"]["zu_versteuerndes_einkommen"]

    zve_kfb = max(0, zve - kinderfreibetrag_total)
    tax_kfb = _cit(zve_kfb / 2, 2025) * 2
    tax_no_kfb = _cit(zve / 2, 2025) * 2

    # The Kinderfreibetrag branch must have fired for this income level
    assert (tax_no_kfb - tax_kfb - kindergeld_annual) > 0
    # And the resulting tax must include the clawed-back Kindergeld, not
    # just the Kinderfreibetrag-reduced figure on its own.
    assert tax == pytest.approx(tax_kfb + kindergeld_annual, abs=0.02)
