"""
Tests for Canadian (ca) locale: tax calculations, filing deadlines, CPP/EI, and claims.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ca"))

from context import LocaleContext, ChildInfo
import ca as locale_ca
from ca.tax_rules import get_tax_year_rules, normalize_province, SUPPORTED_YEARS
from ca.tax_calculator import calculate_tax
from ca.social_contributions import calculate_social_contributions
from ca.tax_dates import get_filing_deadlines
from ca.claim_rules import generate_ca_claims


# ── Tax calculation tests ───────────────────────────────────────────────────

def test_single_employed_ontario_60k_2024():
    """Verify $60,000 gross in Ontario for 2024."""
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=60000.0, region="ON")
    res = calculate_tax(ctx)

    assert res["gross"] == 60000.0
    assert res["federal_tax"] == pytest.approx(6088.0, abs=10)
    assert res["provincial_tax"] == pytest.approx(3163.0, abs=10)
    assert res["tax"] == pytest.approx(9251.0, abs=15)
    assert res["cpp_employee"] == pytest.approx(3362.0, abs=5)
    assert res["ei_employee"] == pytest.approx(996.0, abs=5)
    assert res["net"] < res["gross"]
    assert res["effective_rate"] == pytest.approx(res["tax"] / res["gross"], abs=0.001)


def test_province_awareness_all_13_jurisdictions():
    """Every Canadian province and territory must calculate tax without errors."""
    provinces = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]
    for prov in provinces:
        ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=75000.0, region=prov)
        res = calculate_tax(ctx)
        assert res["province"] == prov
        assert res["tax"] > 0
        assert res["net"] < res["gross"]
        assert 0 < res["effective_rate"] < 0.50
        assert 0 < res["marginal_rate"] < 0.60


def test_quebec_abatement_applies_to_qc_only():
    """Quebec residents receive the 16.5% federal tax abatement."""
    ctx_qc = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=70000.0, region="QC")
    res_qc = calculate_tax(ctx_qc)

    ctx_on = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=70000.0, region="ON")
    res_on = calculate_tax(ctx_on)

    assert res_qc["breakdown"]["federal_abatement"] > 0
    assert res_on["breakdown"]["federal_abatement"] == 0.0
    # Net federal tax for QC should be lower than ON due to abatement
    assert res_qc["federal_tax"] < res_on["federal_tax"]


def test_ontario_surtax_and_health_premium():
    """High earners in Ontario pay provincial surtax and Ontario Health Premium."""
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=120000.0, region="ON")
    res = calculate_tax(ctx)

    assert res["breakdown"]["ontario_surtax"] > 0
    assert res["breakdown"]["ontario_health_premium"] == 750.0  # $750 for $72k-$200k bracket


def test_bc_tax_reduction():
    """Modest income earners in BC receive the BC Tax Reduction."""
    ctx_modest = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=24000.0, region="BC")
    res_modest = calculate_tax(ctx_modest)

    assert res_modest["breakdown"]["provincial_tax_reduction"] > 0


def test_year_2025_federal_rate_reduction():
    """2025 lowest federal rate is 14.5% compared to 15.0% in 2024."""
    ctx_2024 = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=50000.0, region="AB")
    res_2024 = calculate_tax(ctx_2024)

    ctx_2025 = LocaleContext(tax_year=2025, employment_type="employed", annual_gross=50000.0, region="AB")
    res_2025 = calculate_tax(ctx_2025)

    # Federal tax should be lower in 2025 for identical gross income
    assert res_2025["federal_tax"] < res_2024["federal_tax"]


def test_year_2026_lowest_rate_14_percent():
    """2026 lowest federal rate is 14.0%."""
    ctx_2026 = LocaleContext(tax_year=2026, employment_type="employed", annual_gross=50000.0, region="AB")
    res_2026 = calculate_tax(ctx_2026)

    ctx_2025 = LocaleContext(tax_year=2025, employment_type="employed", annual_gross=50000.0, region="AB")
    res_2025 = calculate_tax(ctx_2025)

    assert res_2026["federal_tax"] < res_2025["federal_tax"]


# ── Social contributions tests ──────────────────────────────────────────────

def test_social_contributions_cpp_and_ei():
    """Check standard CPP and EI contribution caps."""
    soc_2024 = calculate_social_contributions(80000.0, 2024, province="ON")
    assert soc_2024["cpp_employee"] == 3867.50
    assert soc_2024["cpp2_employee"] == 188.00
    assert soc_2024["ei_employee"] == 1049.12
    assert soc_2024["total_employee"] == pytest.approx(3867.50 + 188.00 + 1049.12, abs=0.01)


def test_social_contributions_self_employed_double_cpp():
    """Self-employed individuals pay both employee and employer portions of CPP."""
    soc_se = calculate_social_contributions(50000.0, 2024, province="ON", self_employed=True)
    soc_ee = calculate_social_contributions(50000.0, 2024, province="ON", self_employed=False)

    assert soc_se["cpp_employee"] == pytest.approx(soc_ee["cpp_employee"] * 2, abs=0.05)
    assert soc_se["ei_employee"] == 0.0  # Optional for SE filers


# ── Filing deadlines tests ──────────────────────────────────────────────────

def test_filing_deadlines_present():
    """Ensure standard deadlines for individuals, self-employed, and RRSP are returned."""
    deadlines = get_filing_deadlines(2024)
    assert len(deadlines) >= 3

    types = {d["type"] for d in deadlines}
    assert "standard_individual" in types
    assert "self_employed_filing" in types
    assert "rrsp_contribution" in types

    for d in deadlines:
        assert "label" in d and d["label"]
        assert "deadline" in d and len(d["deadline"]) == 10
        assert "notes" in d and d["notes"]


# ── Claims tests ────────────────────────────────────────────────────────────

def test_claims_discovery_employed_profile():
    """Generate tax claims for an employed individual."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=65000.0,
        region="ON",
        children=[ChildInfo(birth_year=2018, childcare=True, childcare_annual_cost=6000.0)],
        union_dues=1200.0,
    )
    claims = generate_ca_claims(ctx)
    claim_ids = {c["id"] for c in claims}

    assert "federal_basic_personal_amount" in claim_ids
    assert "on_basic_personal_amount" in claim_ids
    assert "canada_employment_amount" in claim_ids
    assert "child_care_expenses" in claim_ids
    assert "union_professional_dues" in claim_ids

    # Check status of discovered claims
    for c in claims:
        assert c["status"] in ("ready", "needs_input", "needs_evidence", "detected")
        assert c["confidence"] in ("Definitive", "Likely", "Debatable")


# ── Locale interface tests ──────────────────────────────────────────────────

def test_ca_metadata():
    assert locale_ca.LOCALE_CODE == "ca"
    assert locale_ca.LOCALE_NAME == "Canada"
    assert locale_ca.SUPPORTED_YEARS == [2024, 2025, 2026]
    assert locale_ca.CURRENCY == "CAD"
