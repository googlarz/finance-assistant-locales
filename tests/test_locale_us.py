"""Tests for US locale: tax calculations, filing deadlines, FICA, and locale interface."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "us"))

from us.tax_rules import TAX_YEAR_RULES, get_tax_year_rules
from us.tax_calculator import calculate_liability
from us.tax_dates import get_filing_deadline, get_extension_deadline, get_estimated_tax_deadlines
from us.social_contributions import estimate_fica, estimate_self_employment_tax
import us as locale_us


# ── Tax calculation ───────────────────────────────────────────────────────────

def _calc(gross, filing_status="single", year=2024, extra=None):
    ctx = {
        "employment": {"annual_gross": gross},
        "tax_profile": {
            "filing_status": filing_status,
            "tax_year": year,
            "extra": extra or {},
        },
    }
    return calculate_liability(ctx)


def test_single_60k_standard_deduction_applies():
    r = _calc(60_000)
    # taxable = 60000 - 14600 = 45400, falls in 10%+12% brackets
    assert r["standard_deduction"] == 14_600
    assert r["taxable_income"] == 45_400.0
    assert r["federal_income_tax"] == pytest.approx(5_216.0, abs=1)
    assert r["effective_rate"] == pytest.approx(0.0869, abs=0.001)


def test_single_60k_only_10_and_12_brackets():
    r = _calc(60_000)
    # Must not reach 22% bracket (starts at $47,150 taxable; 45400 < 47150)
    assert r["taxable_income"] < 47_150
    assert r["federal_income_tax"] < 60_000 * 0.22


def test_single_150k_22_and_24_brackets_apply():
    r = _calc(150_000)
    # taxable = 150000 - 14600 = 135400
    # 22% bracket: 47150-100525; 24% bracket: 100525-135400
    assert r["taxable_income"] == 135_400.0
    # Tax must exceed what 10%+12%+22% alone would give
    tax_through_22 = 0.10 * 11_600 + 0.12 * (47_150 - 11_600) + 0.22 * (100_525 - 47_150)
    assert r["federal_income_tax"] > tax_through_22
    # And some income is taxed at 24%
    tax_expected = tax_through_22 + 0.24 * (135_400 - 100_525)
    assert r["federal_income_tax"] == pytest.approx(tax_expected, abs=1)


def test_mfj_225k_no_additional_medicare():
    """MFJ threshold is $250k — $225k gross must NOT trigger the extra 0.9%."""
    r = _calc(225_000, filing_status="married_filing_jointly")
    # Medicare = gross * 1.45% only (no surcharge)
    assert r["medicare_tax"] == pytest.approx(225_000 * 0.0145, abs=0.01)


def test_mfj_260k_additional_medicare_applies():
    """$260k MFJ: $10k over $250k threshold → extra 0.9% on $10k."""
    r = _calc(260_000, filing_status="married_filing_jointly")
    base_medicare = 260_000 * 0.0145
    extra_medicare = (260_000 - 250_000) * 0.009
    assert r["medicare_tax"] == pytest.approx(base_medicare + extra_medicare, abs=0.01)


def test_withheld_federal_key_used_for_refund():
    r = _calc(60_000, extra={"withheld_federal": 7_000})
    assert r["withheld"] == 7_000
    # refund = withheld_federal - federal_income_tax (not total tax)
    assert r["estimated_refund"] == pytest.approx(7_000 - r["federal_income_tax"], abs=0.01)


def test_legacy_withheld_key_also_works():
    r = _calc(60_000, extra={"withheld": 5_000})
    assert r["withheld"] == 5_000
    assert r["estimated_refund"] == pytest.approx(5_000 - r["federal_income_tax"], abs=0.01)


def test_filing_status_defaults_to_single():
    ctx_explicit = {
        "employment": {"annual_gross": 80_000},
        "tax_profile": {"filing_status": "single", "tax_year": 2024},
    }
    ctx_no_status = {
        "employment": {"annual_gross": 80_000},
        "tax_profile": {"tax_year": 2024},
    }
    r_explicit = calculate_liability(ctx_explicit)
    r_default = calculate_liability(ctx_no_status)
    assert r_explicit["federal_income_tax"] == r_default["federal_income_tax"]
    assert r_default["filing_status"] == "single"


# ── LocaleContext path (regression: used to crash via tax_engine) ─────────────

def test_calculate_liability_accepts_localecontext():
    """The main skill path passes a LocaleContext, not a dict. Must not crash
    and must match the equivalent dict input for a W-2 employee."""
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=60_000)
    r = calculate_liability(ctx)
    assert r["gross_income"] == 60_000
    assert r["filing_status"] == "single"
    # Matches the dict path
    assert r["federal_income_tax"] == pytest.approx(_calc(60_000)["federal_income_tax"], abs=1)


def test_localecontext_married_derives_mfj():
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=225_000, married=True)
    r = calculate_liability(ctx)
    assert r["filing_status"] == "married_filing_jointly"


def test_localecontext_filing_status_from_extra_wins():
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2024, annual_gross=80_000, married=True,
                        extra={"filing_status": "head_of_household"})
    r = calculate_liability(ctx)
    assert r["filing_status"] == "head_of_household"


# ── Self-employment: SE tax + QBI (regression: main path ignored them) ────────

def test_self_employed_gets_se_tax_and_qbi():
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2024, employment_type="self_employed", annual_gross=80_000)
    r = calculate_liability(ctx)
    assert r["self_employment_tax"] > 0
    assert r["qbi_deduction"] > 0
    # SE tax ≈ 80000 * 0.9235 * 15.3% (below SS wage base) ≈ 11,304
    assert r["self_employment_tax"] == pytest.approx(11_304, abs=50)
    # QBI = 20% of profit, capped by 20% taxable income — must be positive & ≤ 16k
    assert 0 < r["qbi_deduction"] <= 16_000
    # SE filer pays no W-2 FICA
    assert r["social_security_tax"] == 0
    assert r["medicare_tax"] == 0


def test_employed_no_se_fields():
    """A plain W-2 employee result must not carry SE/QBI keys."""
    r = _calc(60_000)
    assert "self_employment_tax" not in r
    assert "qbi_deduction" not in r


# ── SSTB phase-out wiring (regression: is_sstb never reached calculate_qbi_deduction) ──

def test_sstb_above_threshold_gets_zero_qbi_deduction():
    """A consultant/lawyer/advisor (SSTB) above the 2025 single threshold ($197,300 +
    $50k phase-out range) must get $0 QBI, not the full 20% deduction."""
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2025, employment_type="self_employed", annual_gross=400_000,
                        extra={"is_sstb": True})
    r = calculate_liability(ctx)
    assert r["qbi_deduction"] == 0.0, (
        f"SSTB above phase-out should get $0 QBI, got {r['qbi_deduction']}"
    )
    assert "fully phased out" in r["qbi_note"].lower()


def test_non_sstb_above_threshold_still_gets_qbi():
    """A non-SSTB business (e.g. a shop, agency) above the threshold keeps the QBI
    deduction — only SSTBs phase out. (W-2/UBIA cap is a separate, documented gap.)"""
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2025, employment_type="self_employed", annual_gross=400_000,
                        extra={"is_sstb": False})
    r = calculate_liability(ctx)
    assert r["qbi_deduction"] > 0, "Non-SSTB above threshold should still get a QBI deduction"


def test_sstb_unset_above_threshold_warns_in_qbi_note():
    """When is_sstb isn't provided and taxable income is above threshold, the engine
    must not silently assume non-SSTB — qbi_note has to say so."""
    from context import LocaleContext
    ctx = LocaleContext(tax_year=2025, employment_type="self_employed", annual_gross=400_000)
    r = calculate_liability(ctx)
    assert r["qbi_deduction"] > 0  # same number as before this fix — assumption is non-SSTB
    assert "is_sstb" in r["qbi_note"] or "SSTB status not provided" in r["qbi_note"], (
        f"Missing SSTB ambiguity warning in qbi_note: {r['qbi_note']!r}"
    )


def test_sstb_below_threshold_gets_full_qbi_regardless():
    """Below the phase-out threshold, SSTB status doesn't matter — full deduction either way."""
    from context import LocaleContext
    ctx_sstb = LocaleContext(tax_year=2025, employment_type="self_employed", annual_gross=80_000,
                             extra={"is_sstb": True})
    ctx_non = LocaleContext(tax_year=2025, employment_type="self_employed", annual_gross=80_000,
                            extra={"is_sstb": False})
    r_sstb = calculate_liability(ctx_sstb)
    r_non = calculate_liability(ctx_non)
    assert r_sstb["qbi_deduction"] == r_non["qbi_deduction"] > 0


def test_us_tax_via_tax_engine_does_not_error():
    """Integration: the real product path through tax_engine must work end-to-end."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
    from tax_engine import calculate_tax_estimate
    profile = {
        "meta": {"locale": "us", "tax_year": 2024},
        "tax_profile": {"locale": "us", "filing_status": "single"},
        "employment": {"type": "employed", "annual_gross": 80_000},
    }
    r = calculate_tax_estimate(profile, 2024)
    assert "error" not in r, f"US tax via tax_engine errored: {r.get('error')}"
    assert r["federal_income_tax"] > 0


# ── Filing deadlines ──────────────────────────────────────────────────────────

def test_filing_deadline_2024_is_april_15_2025():
    d = get_filing_deadline(2024)
    assert d.year == 2025
    assert d.month == 4
    assert d.day == 15


def test_extension_deadline_2024_is_october_15_2025():
    d = get_extension_deadline(2024)
    assert d.year == 2025
    assert d.month == 10
    assert d.day == 15


def test_quarterly_estimated_deadlines_returns_4_entries():
    deadlines = get_estimated_tax_deadlines(2024)
    assert len(deadlines) == 4
    quarters = [d["quarter"] for d in deadlines]
    assert quarters == ["Q1", "Q2", "Q3", "Q4"]


# ── Social contributions (FICA) ───────────────────────────────────────────────

def test_fica_100k_2024_ss_and_medicare():
    r = estimate_fica(100_000, 2024)
    assert r["social_security"] == pytest.approx(6_200.0, abs=0.01)   # 100k × 6.2%
    assert r["medicare"] == pytest.approx(1_450.0, abs=0.01)          # 100k × 1.45%


def test_fica_200k_2024_ss_capped_at_wage_base():
    r = estimate_fica(200_000, 2024)
    # SS capped at $168,600 wage base: 168600 × 6.2% = 10453.20
    assert r["social_security"] == pytest.approx(10_453.20, abs=0.01)
    assert r["wage_base"] == 168_600


def test_self_employment_tax_80k_2024():
    r = estimate_self_employment_tax(80_000, 2024)
    expected_se_base = 80_000 * 0.9235   # = 73880.0
    assert r["se_base"] == pytest.approx(expected_se_base, abs=0.01)
    # SE tax ≈ 15.3% on se_base (both shares)
    expected_total = expected_se_base * (0.062 * 2 + 0.0145 * 2)
    assert r["total_se_tax"] == pytest.approx(expected_total, abs=1)


# ── Tax rules ─────────────────────────────────────────────────────────────────

def test_2024_standard_deduction_single():
    rules = get_tax_year_rules(2024)
    assert rules["standard_deduction"]["single"] == 14_600


def test_2025_standard_deduction_single():
    rules = get_tax_year_rules(2025)
    assert rules["standard_deduction"]["single"] == 15_000


def test_2025_ss_wage_base():
    rules = get_tax_year_rules(2025)
    assert rules["fica"]["social_security_wage_base"] == 176_100


def test_future_year_falls_back_to_most_recent():
    from locales.us.tax_rules import TAX_YEAR_RULES
    rules_2099 = get_tax_year_rules(2099)
    latest_year = max(TAX_YEAR_RULES)
    assert rules_2099["year"] == latest_year


# ── Locale interface ──────────────────────────────────────────────────────────

def test_locale_code():
    assert locale_us.LOCALE_CODE == "us"


def test_currency():
    assert locale_us.CURRENCY == "USD"


def test_get_deduction_categories_min_5_items():
    cats = locale_us.get_deduction_categories()
    assert isinstance(cats, list)
    assert len(cats) >= 5
    for item in cats:
        assert "id" in item
        assert "name" in item


def test_generate_tax_claims_empty_profile_returns_list():
    result = locale_us.generate_tax_claims({}, 2024)
    assert isinstance(result, list)


# ── Additional Medicare Tax (SE) ──────────────────────────────────────────────

def test_se_tax_additional_medicare_applies():
    """High-income SE filer should pay 0.9% Additional Medicare on amount over threshold."""
    result = estimate_self_employment_tax(250_000, 2024, filing_status="single")
    # se_base = 250_000 * 0.9235 = 230_875
    # Additional Medicare applies on: 230_875 - 200_000 = 30_875
    # Extra: 30_875 * 0.009 = 277.88
    assert result["medicare_tax"] > 230_875 * 0.0145 * 2  # more than base Medicare


def test_se_tax_mfj_higher_threshold():
    """MFJ filer at $240k should NOT pay Additional Medicare (threshold $250k)."""
    single_result = estimate_self_employment_tax(240_000, 2024, filing_status="single")
    mfj_result = estimate_self_employment_tax(240_000, 2024, filing_status="married_filing_jointly")
    # MFJ threshold is $250k — no additional Medicare
    # Single threshold is $200k — additional Medicare applies
    assert mfj_result["medicare_tax"] < single_result["medicare_tax"]


def test_estimate_fica_mfj_threshold():
    """MFJ employee at $240k should NOT pay Additional Medicare (threshold $250k)."""
    single = estimate_fica(240_000, 2024, filing_status="single")
    mfj = estimate_fica(240_000, 2024, filing_status="married_filing_jointly")
    assert mfj["medicare"] < single["medicare"]
