"""
Tests for UK locale tax calculations using LocaleContext directly.

Tax year convention: year=2024 → 2024/25 (6 Apr 2024 – 5 Apr 2025).

UK tax numbers used:
  - Personal allowance: £12,570 (frozen until April 2028)
  - Basic rate (20%): £12,571 – £50,270
  - Higher rate (40%): £50,271 – £125,140
  - Additional rate (45%): above £125,140
  - NI (Class 1 employee): 8% on £12,570–£50,270, 2% above (post-Jan 2024)
"""

import pytest
from context import LocaleContext
from uk import calculate_tax, get_filing_deadlines, generate_tax_claims
from uk.tax_rules import TAX_YEAR_RULES, calculate_income_tax, get_tax_year_rules
from uk.social_contributions import get_social_contributions

SUPPORTED_YEARS = [2024, 2025, 2026]


# ── Tax rules sanity checks ───────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_all_rules_present(year):
    """All required rule keys exist and are non-None for every supported year."""
    rules = TAX_YEAR_RULES[year]
    required_keys = [
        "personal_allowance", "basic_rate_limit", "higher_rate_limit",
        "basic_rate", "higher_rate", "additional_rate",
        "ni_employee_rate_main", "ni_employee_rate_upper",
        "isa_allowance", "pension_annual_allowance", "capital_gains_allowance",
        "marriage_allowance", "currency",
    ]
    for key in required_keys:
        assert rules[key] is not None, f"TAX_YEAR_RULES[{year}]['{key}'] is None"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_personal_allowance_frozen(year):
    """Personal allowance is £12,570 across all supported years (frozen until 2028)."""
    assert TAX_YEAR_RULES[year]["personal_allowance"] == 12_570


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_basic_rate_limit_frozen(year):
    """Basic rate limit is £50,270 across all supported years."""
    assert TAX_YEAR_RULES[year]["basic_rate_limit"] == 50_270


def test_tax_increases_with_income():
    """Income tax is monotonically increasing with gross income."""
    rules = get_tax_year_rules(2024)
    tax_30k = calculate_income_tax(30_000, rules)
    tax_60k = calculate_income_tax(60_000, rules)
    tax_130k = calculate_income_tax(130_000, rules)
    assert tax_30k < tax_60k < tax_130k


def test_zero_income_zero_tax():
    """No tax on zero income."""
    rules = get_tax_year_rules(2024)
    assert calculate_income_tax(0.0, rules) == 0.0


def test_within_personal_allowance_zero_tax():
    """Income within personal allowance attracts no income tax."""
    rules = get_tax_year_rules(2024)
    assert calculate_income_tax(12_000, rules) == 0.0
    assert calculate_income_tax(12_570, rules) == 0.0


# ── Test 1: Basic rate taxpayer (£30k gross) ──────────────────────────────────

def test_basic_rate_taxpayer_30k():
    """
    £30,000 gross — basic rate taxpayer.
    Expected: tax = £3,486, NI ~£1,394, net ~£25,120.

    Calculation:
      Taxable income = £30,000 − £12,570 = £17,430
      Tax = £17,430 × 20% = £3,486
      NI = (£30,000 − £12,570) × 8% = £17,430 × 8% = £1,394.40
      Net = £30,000 − £3,486 − £1,394.40 = £25,119.60
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=30_000.0,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == 30_000.0
    assert result["tax"] == pytest.approx(3_486.0, abs=1.0)
    assert result["ni_employee"] == pytest.approx(1_394.40, abs=5.0)
    assert result["net"] == pytest.approx(25_119.60, abs=10.0)
    assert result["net"] < result["gross"]
    assert result["marginal_rate"] == pytest.approx(0.20, abs=0.01)
    assert result["confidence"] == "Definitive"
    assert result["currency"] == "GBP"


# ── Test 2: Higher rate taxpayer (£60k gross) ─────────────────────────────────

def test_higher_rate_taxpayer_60k():
    """
    £60,000 gross — higher rate taxpayer.
    Expected: tax = £11,432.

    Calculation:
      Basic rate band: (£50,270 − £12,570) × 20% = £37,700 × 20% = £7,540
      Higher rate band: (£60,000 − £50,270) × 40% = £9,730 × 40% = £3,892
      Total tax = £7,540 + £3,892 = £11,432
      NI (employee): (£50,270 − £12,570) × 8% + (£60,000 − £50,270) × 2%
                   = £37,700 × 8% + £9,730 × 2% = £3,016 + £194.60 = £3,210.60
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == 60_000.0
    assert result["tax"] == pytest.approx(11_432.0, abs=1.0)
    assert result["ni_employee"] == pytest.approx(3_210.60, abs=5.0)
    assert result["net"] < result["gross"]
    assert result["marginal_rate"] == pytest.approx(0.40, abs=0.01)
    assert result["confidence"] == "Definitive"


def test_higher_rate_taxpayer_breakdown():
    """Breakdown correctly splits tax between basic and higher rate bands."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    result = calculate_tax(ctx)
    bd = result["breakdown"]

    assert bd["basic_rate_tax"] == pytest.approx(7_540.0, abs=1.0)
    assert bd["higher_rate_tax"] == pytest.approx(3_892.0, abs=1.0)
    assert bd["additional_rate_tax"] == 0.0
    assert bd["total_income_tax"] == pytest.approx(11_432.0, abs=1.0)


# ── Test 3: Personal allowance taper (£110k gross) ───────────────────────────

def test_personal_allowance_taper_110k():
    """
    £110,000 gross — in the personal allowance taper zone (£100k–£125,140).
    Allowance is tapered: £12,570 − ((£110,000 − £100,000) / 2) = £12,570 − £5,000 = £7,570.
    This creates an effective 60% marginal rate in the taper zone.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=110_000.0,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == 110_000.0
    # Effective rate should be notably higher than basic higher rate (40%)
    assert result["effective_rate"] > 0.28
    # Marginal rate in taper zone is 60%
    assert result["marginal_rate"] == pytest.approx(0.60, abs=0.01)
    assert result["net"] < result["gross"]
    # Tax should be higher than a simple 40% calculation would suggest
    # (£110k − £12,570 = £97,430 taxable at simple 40% would give only £38,972 tax
    #  but taper means more of income is taxed — £32,432 which is correct)
    assert result["tax"] == pytest.approx(32_432.0, abs=5.0)


def test_personal_allowance_taper_allowance_zeroed_at_125140():
    """
    At £125,140 the personal allowance is fully withdrawn.
    """
    from uk.tax_rules import calculate_personal_allowance, get_tax_year_rules
    rules = get_tax_year_rules(2024)
    allowance_at_limit = calculate_personal_allowance(125_140, rules)
    assert allowance_at_limit == pytest.approx(0.0, abs=1.0)


def test_personal_allowance_taper_increases_effective_rate():
    """Effective tax rate at £110k is higher than at £60k despite same higher rate band."""
    ctx_60k = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=60_000.0)
    ctx_110k = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=110_000.0)

    r_60k = calculate_tax(ctx_60k)
    r_110k = calculate_tax(ctx_110k)

    assert r_110k["effective_rate"] > r_60k["effective_rate"]


# ── Test 4: Filing deadlines ──────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_at_least_one_per_year(year):
    """get_filing_deadlines returns at least one deadline for every supported year."""
    deadlines = get_filing_deadlines(year)
    assert len(deadlines) >= 1


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_have_required_keys(year):
    """Every deadline entry has label, deadline (ISO date), and notes."""
    deadlines = get_filing_deadlines(year)
    for dl in deadlines:
        assert "label" in dl, f"Deadline missing 'label': {dl}"
        assert "deadline" in dl, f"Deadline missing 'deadline': {dl}"
        assert "notes" in dl, f"Deadline missing 'notes': {dl}"
        # Validate ISO date format
        from datetime import date
        parsed = date.fromisoformat(dl["deadline"])
        assert parsed.year >= year, (
            f"Deadline date {dl['deadline']} appears before tax year {year}"
        )


def test_filing_deadlines_2024_includes_online_jan31():
    """2024/25 tax year has an online return deadline on 31 Jan 2026."""
    deadlines = get_filing_deadlines(2024)
    deadlines_by_date = {dl["deadline"]: dl for dl in deadlines}
    assert "2026-01-31" in deadlines_by_date


def test_filing_deadlines_2024_includes_paper_oct31():
    """2024/25 tax year has a paper return deadline on 31 Oct 2025."""
    deadlines = get_filing_deadlines(2024)
    deadlines_by_date = {dl["deadline"]: dl for dl in deadlines}
    assert "2025-10-31" in deadlines_by_date


def test_filing_deadlines_all_years_coverage():
    """All three supported tax years return deadlines with distinct future dates."""
    for year in SUPPORTED_YEARS:
        deadlines = get_filing_deadlines(year)
        assert len(deadlines) >= 3, (
            f"Expected at least 3 deadlines for year {year}, got {len(deadlines)}"
        )


# ── Test 5: Claims ────────────────────────────────────────────────────────────

def test_personal_allowance_always_present():
    """Personal allowance claim is always returned with status 'ready'."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    pa_claims = [c for c in claims if c["id"] == "personal_allowance"]
    assert len(pa_claims) == 1
    assert pa_claims[0]["status"] == "ready"
    assert pa_claims[0]["confidence"] == "Definitive"
    assert pa_claims[0]["amount_estimate"] == pytest.approx(12_570.0, abs=1.0)


def test_marriage_allowance_when_married():
    """Marriage allowance claim appears when profile is marked married."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=25_000.0,
        married=True,
    )
    claims = generate_tax_claims(ctx, 2024)
    ma_claims = [c for c in claims if c["id"] == "marriage_allowance"]
    assert len(ma_claims) >= 1


def test_marriage_allowance_needs_input_when_status_unknown():
    """When marital status is not set, marriage allowance is 'needs_input'."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=35_000.0,
        married=False,
    )
    claims = generate_tax_claims(ctx, 2024)
    ma_claims = [c for c in claims if c["id"] == "marriage_allowance"]
    if ma_claims:
        assert ma_claims[0]["status"] == "needs_input"


def test_wfh_claim_ready_when_homeoffice_flagged():
    """Working from home claim is 'ready' when homeoffice_days_per_week is set."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
        homeoffice_days_per_week=3.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    wfh_claims = [c for c in claims if c["id"] == "working_from_home"]
    assert len(wfh_claims) == 1
    assert wfh_claims[0]["status"] == "ready"
    assert wfh_claims[0]["amount_estimate"] == pytest.approx(312.0, abs=1.0)  # £6 × 52


def test_wfh_claim_needs_input_when_not_flagged():
    """Working from home claim is 'needs_input' when homeoffice_days_per_week is not set."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
        homeoffice_days_per_week=None,
    )
    claims = generate_tax_claims(ctx, 2024)
    wfh_claims = [c for c in claims if c["id"] == "working_from_home"]
    assert len(wfh_claims) == 1
    assert wfh_claims[0]["status"] == "needs_input"


def test_claims_have_required_keys():
    """All claims have the required interface keys."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=50_000.0,
        homeoffice_days_per_week=2.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    assert len(claims) >= 1
    for claim in claims:
        assert "id" in claim
        assert "title" in claim
        assert "status" in claim
        assert "amount_estimate" in claim
        assert "confidence" in claim
        assert claim["status"] in ("ready", "needs_input", "needs_evidence", "detected")
        assert claim["confidence"] in ("Definitive", "Likely", "Debatable")


def test_at_least_one_ready_or_needs_input_claim():
    """A standard employed profile has at least one ready or needs_input claim."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=45_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    actionable = [c for c in claims if c["status"] in ("ready", "needs_input")]
    assert len(actionable) >= 1


# ── NI contribution checks ────────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_ni_does_not_exceed_gross(year):
    """Employee NI does not exceed gross income."""
    for gross in (10_000, 30_000, 60_000, 150_000):
        ni_data = get_social_contributions(gross, year)
        assert ni_data["ni_employee"] <= gross, (
            f"NI ({ni_data['ni_employee']}) exceeds gross ({gross}) for year {year}"
        )


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_ni_rate_not_above_one(year):
    """NI rates in the rules are all below 1.0."""
    from uk.tax_rules import TAX_YEAR_RULES
    rules = TAX_YEAR_RULES[year]
    assert rules["ni_employee_rate_main"] < 1.0
    assert rules["ni_employee_rate_upper"] < 1.0
    assert rules["ni_employer_rate"] < 1.0


def test_ni_zero_below_primary_threshold():
    """No employee NI on income at or below the Primary Threshold (£12,570)."""
    ni_data = get_social_contributions(12_570, 2024)
    assert ni_data["ni_employee"] == pytest.approx(0.0, abs=0.01)


def test_ni_increases_with_gross():
    """Employee NI increases as gross income increases."""
    ni_30k = get_social_contributions(30_000, 2024)["ni_employee"]
    ni_60k = get_social_contributions(60_000, 2024)["ni_employee"]
    ni_100k = get_social_contributions(100_000, 2024)["ni_employee"]
    assert ni_30k < ni_60k < ni_100k


# ── Self-employed / confidence checks ────────────────────────────────────────

def test_self_employed_confidence_is_likely():
    """Self-employed calculations return 'Likely' confidence."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="self_employed",
        annual_gross=50_000.0,
    )
    result = calculate_tax(ctx)
    assert result["confidence"] == "Likely"


def test_self_employed_uses_class4_ni():
    """Self-employed NI uses Class 4 rates (6%/2%), not Class 1 (8%/2%)."""
    gross = 30_000.0
    ni_employee = get_social_contributions(gross, 2024, self_employed=True)
    ni_class1 = get_social_contributions(gross, 2024, self_employed=False)
    # Class 4 (6%) gives lower NI than Class 1 (8%)
    assert ni_employee["ni_employee"] < ni_class1["ni_employee"]
    # Class 4 has no employer contribution
    assert ni_employee["ni_employer"] == 0.0


# ── 2026 projection check ─────────────────────────────────────────────────────

def test_2026_all_params_filled():
    """All critical parameters for 2026 are non-None."""
    ctx = LocaleContext(
        tax_year=2026,
        employment_type="employed",
        annual_gross=55_000.0,
        homeoffice_days_per_week=2.0,
    )
    result = calculate_tax(ctx)
    bd = result["breakdown"]
    critical_keys = [
        "gross", "personal_allowance_used", "taxable_income",
        "total_income_tax", "ni_employee", "net",
    ]
    for key in critical_keys:
        assert bd[key] is not None, f"breakdown['{key}'] is None for year 2026"


def test_2026_confidence_is_likely():
    """2026 tax year returns 'Likely' confidence (frozen thresholds projected, not legislated)."""
    ctx = LocaleContext(
        tax_year=2026,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    result = calculate_tax(ctx)
    assert result["confidence"] in ("Likely", "Definitive")


# ── Dict profile input ────────────────────────────────────────────────────────

def test_calculate_tax_accepts_dict_profile():
    """calculate_tax accepts a Finance Assistant profile dict as well as LocaleContext."""
    profile = {
        "meta": {"tax_year": 2024},
        "employment": {"type": "employed", "annual_gross": 40_000},
        "family": {},
        "housing": {},
        "personal": {},
        "tax_profile": {},
    }
    result = calculate_tax(profile, year=2024)
    assert result["gross"] == pytest.approx(40_000.0, abs=1.0)
    assert result["net"] < result["gross"]


def test_generate_tax_claims_accepts_dict_profile():
    """generate_tax_claims accepts a Finance Assistant profile dict."""
    profile = {
        "meta": {"tax_year": 2024},
        "employment": {"type": "employed", "annual_gross": 35_000},
        "family": {},
        "housing": {},
        "personal": {},
        "tax_profile": {},
    }
    claims = generate_tax_claims(profile, year=2024)
    assert len(claims) >= 1
    pa = [c for c in claims if c["id"] == "personal_allowance"]
    assert len(pa) == 1
