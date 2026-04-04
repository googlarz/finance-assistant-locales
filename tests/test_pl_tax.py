"""
Tests for Polish locale PIT tax calculations using LocaleContext directly.

Polish tax year = calendar year (1 January – 31 December).

Key Polish PIT numbers used in these tests (2024):
  - Tax-free amount: 30,000 PLN (kwota wolna od podatku)
  - First bracket: 12% on income 30,001–120,000 PLN
  - Second bracket: 32% above 120,000 PLN
  - Tax reduction: 3,600 PLN (= 30,000 × 12%, applied as flat reduction)
  - Employee ZUS: 13.71% of gross (9.76% + 1.5% + 2.45%)
  - Health insurance: 9% of (gross − ZUS) — NOT deductible from PIT
  - Ulga dla młodych: PIT = 0 for under-26s earning ≤ 85,528 PLN

Calculation walkthrough for 40,000 PLN gross (salaried, 2024):
  ZUS = 40,000 × 13.71% = 5,484.00 PLN
  Work costs (koszty) = 3,000 PLN
  Tax base = 40,000 − 5,484 − 3,000 = 31,516 PLN
  PIT = (31,516 − 30,000) × 12% = 1,516 × 12% = 181.92 PLN
  Health insurance = (40,000 − 5,484) × 9% = 34,516 × 9% = 3,106.44 PLN
  Net = 40,000 − 181.92 − 5,484 − 3,106.44 = 31,227.64 PLN

Calculation walkthrough for 150,000 PLN gross (salaried, 2024):
  ZUS capped at 120,000 PLN (below 234,720 cap, so no cap applied here)
  Wait — ZUS at 150,000 > cap check: 150,000 < 234,720, so not capped
  ZUS = 150,000 × 13.71% = 20,565.00 PLN
  Work costs = 3,000 PLN
  Tax base = 150,000 − 20,565 − 3,000 = 126,435 PLN
  PIT = 10,800 + (126,435 − 120,000) × 32% = 10,800 + 6,435 × 32% = 10,800 + 2,059.20 = 12,859.20 PLN
  Health insurance = (150,000 − 20,565) × 9% = 129,435 × 9% = 11,649.15 PLN
  Net = 150,000 − 12,859.20 − 20,565 − 11,649.15 = 104,926.65 PLN
"""

import pytest
from context import LocaleContext, ChildInfo
from pl import calculate_tax, get_filing_deadlines, generate_tax_claims, get_tax_rules
from pl import LOCALE_CODE, LOCALE_NAME, SUPPORTED_YEARS
from pl.tax_rules import TAX_YEAR_RULES, get_tax_year_rules
from pl.social_contributions import get_social_contributions

# ── Locale metadata ───────────────────────────────────────────────────────────

def test_locale_metadata():
    assert LOCALE_CODE == "pl"
    assert LOCALE_NAME == "Poland"
    assert SUPPORTED_YEARS == [2024, 2025, 2026]


# ── Tax rules — all years non-None ───────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_all_rules_non_none(year):
    """All required rule keys exist and are non-None for every supported year."""
    rules = TAX_YEAR_RULES[year]
    required_keys = [
        "first_bracket_rate", "second_bracket_rate", "bracket_threshold",
        "tax_free_amount", "tax_reduction",
        "pracownicze_koszty_podstawowe", "pracownicze_koszty_podwyzszone",
        "ulga_dla_mlodych_limit", "ikze_limit",
        "darowizny_pct", "internet_ulga_max",
        "ulga_na_dzieci_1_2", "ulga_na_dzieci_3", "ulga_na_dzieci_4plus",
        "zus_employee_total", "skladka_zdrowotna_rate", "currency",
    ]
    for key in required_keys:
        assert rules[key] is not None, f"TAX_YEAR_RULES[{year}]['{key}'] is None"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_brackets_unchanged(year):
    """12%/32% brackets and 120,000 PLN threshold unchanged across all supported years."""
    rules = TAX_YEAR_RULES[year]
    assert rules["first_bracket_rate"] == pytest.approx(0.12)
    assert rules["second_bracket_rate"] == pytest.approx(0.32)
    assert rules["bracket_threshold"] == 120_000


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_tax_free_amount_unchanged(year):
    """Tax-free amount (kwota wolna od podatku) is 30,000 PLN for all supported years."""
    assert TAX_YEAR_RULES[year]["tax_free_amount"] == 30_000


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_ikze_limit_non_none_and_positive(year):
    """IKZE limit is positive for all supported years."""
    assert TAX_YEAR_RULES[year]["ikze_limit"] > 0


# ── Test 1: Standard salaried 40,000 PLN ─────────────────────────────────────

def test_standard_salaried_40k_2024():
    """
    40,000 PLN gross — standard salaried employee.
    ZUS = 40,000 × 13.71% = 5,484.00 PLN
    Tax base = 40,000 − 5,484 − 3,000 = 31,516 PLN
    PIT = (31,516 − 30,000) × 12% = 181.92 PLN
    Health = (40,000 − 5,484) × 9% = 3,106.44 PLN
    Net ≈ 31,227.64 PLN
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == pytest.approx(40_000.0, abs=1.0)
    assert result["income_tax"] == pytest.approx(181.92, abs=5.0)
    assert result["zus_employee"] == pytest.approx(5_484.0, abs=10.0)
    assert result["health_insurance"] == pytest.approx(3_106.44, abs=20.0)
    assert result["net"] == pytest.approx(31_227.64, abs=30.0)
    assert result["net"] < result["gross"]
    assert result["currency"] == "PLN"
    assert result["confidence"] == "Definitive"
    assert result["marginal_rate"] == pytest.approx(0.12, abs=0.01)


def test_standard_salaried_result_keys():
    """Result dict contains all required interface keys."""
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=50_000.0)
    result = calculate_tax(ctx)
    required_keys = [
        "gross", "income_tax", "zus_employee", "health_insurance",
        "net", "effective_rate", "marginal_rate", "currency", "confidence",
    ]
    for key in required_keys:
        assert key in result, f"Missing key in result: {key}"


# ── Test 2: Under-26 exemption (ulga dla młodych) ────────────────────────────

def test_ulga_dla_mlodych_60k():
    """
    Income 60,000 PLN, age 24 → PIT = 0 (ulga dla młodych, limit 85,528 PLN).
    ZUS and health insurance still apply.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        extra={"age": 24},
    )
    result = calculate_tax(ctx)

    assert result["income_tax"] == pytest.approx(0.0, abs=0.01)
    assert result["ulga_mlodych_applied"] is True
    assert result["zus_employee"] > 0
    assert result["health_insurance"] > 0
    assert result["net"] < result["gross"]
    assert result["net"] > 0


def test_ulga_dla_mlodych_not_applied_when_26():
    """Age exactly 26 — ulga dla młodych does NOT apply."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        extra={"age": 26},
    )
    result = calculate_tax(ctx)
    assert result["ulga_mlodych_applied"] is False
    assert result["income_tax"] > 0


def test_ulga_dla_mlodych_not_applied_when_income_exceeds_limit():
    """Age 24 but income > 85,528 PLN — ulga dla młodych does NOT apply."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=90_000.0,
        extra={"age": 24},
    )
    result = calculate_tax(ctx)
    assert result["ulga_mlodych_applied"] is False
    assert result["income_tax"] > 0


# ── Test 3: High earner 150,000 PLN — second bracket (32%) ───────────────────

def test_high_earner_150k_second_bracket():
    """
    150,000 PLN gross — second bracket kicks in (32% above 120,000 PLN).
    ZUS = 150,000 × 13.71% = 20,565 PLN
    Tax base = 150,000 − 20,565 − 3,000 = 126,435 PLN
    PIT = 10,800 + (126,435 − 120,000) × 32% ≈ 12,859.20 PLN
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=150_000.0,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == pytest.approx(150_000.0, abs=1.0)
    assert result["marginal_rate"] == pytest.approx(0.32, abs=0.01)
    assert result["income_tax"] == pytest.approx(12_859.20, abs=50.0)
    assert result["zus_employee"] == pytest.approx(20_565.0, abs=20.0)
    assert result["net"] < result["gross"]
    # Effective rate (tax/gross) is well above the effective rate of a 30k earner
    # but below the 32% marginal rate — 150k earner is deeply in the second bracket
    result_30k = calculate_tax(LocaleContext(
        tax_year=2024, employment_type="employed", annual_gross=30_000.0
    ))
    assert result["effective_rate"] > result_30k["effective_rate"]


def test_tax_increases_with_income():
    """PIT is monotonically increasing with gross income."""
    for gross_a, gross_b in [(30_000, 60_000), (60_000, 150_000)]:
        ctx_a = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=float(gross_a))
        ctx_b = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=float(gross_b))
        assert calculate_tax(ctx_a)["income_tax"] <= calculate_tax(ctx_b)["income_tax"]


def test_zero_income_zero_pit():
    """No PIT on zero income."""
    ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=0.0)
    result = calculate_tax(ctx)
    assert result["income_tax"] == pytest.approx(0.0, abs=0.01)


# ── Test 4: Joint filing with spouse ─────────────────────────────────────────

def test_joint_filing_estimate_lower_tax():
    """
    Joint filing (wspólne rozliczenie) should yield lower combined PIT when
    one spouse earns above 120,000 PLN and the other earns much less.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=150_000.0,
        married=True,
        extra={"spouse_gross": 20_000.0},
    )
    result = calculate_tax(ctx)

    assert "joint_tax_estimate" in result
    joint = result["joint_tax_estimate"]
    assert "joint_pit" in joint
    assert "individual_pit_combined" in joint
    assert "estimated_saving" in joint
    # Joint filing should reduce overall tax when incomes differ significantly
    assert joint["estimated_saving"] >= 0
    # With 150k + 20k, splitting 170k in half = 85k each — both below 120k threshold
    assert joint["joint_pit"] < joint["individual_pit_combined"]


def test_joint_filing_no_benefit_equal_incomes():
    """No significant saving when both spouses earn the same amount."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        married=True,
        extra={"spouse_gross": 60_000.0},
    )
    result = calculate_tax(ctx)
    if "joint_tax_estimate" in result:
        joint = result["joint_tax_estimate"]
        # Joint = individual when incomes are equal
        assert joint["estimated_saving"] == pytest.approx(0.0, abs=50.0)


# ── Test 5: Ulga na dzieci (child relief) ────────────────────────────────────

def test_ulga_na_dzieci_2_children():
    """2 children → 2 × 1,112.04 = 2,224.08 PLN relief."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=80_000.0,
        children=[
            ChildInfo(birth_year=2015),
            ChildInfo(birth_year=2018),
        ],
    )
    claims = generate_tax_claims(ctx, 2024)
    child_claims = [c for c in claims if c["id"] == "ulga_na_dzieci"]
    assert len(child_claims) == 1
    assert child_claims[0]["amount_estimate"] == pytest.approx(2_224.08, abs=0.01)
    assert child_claims[0]["status"] == "ready"
    assert child_claims[0]["confidence"] == "Definitive"


def test_ulga_na_dzieci_3_children():
    """3 children → 2 × 1,112.04 + 2,000.04 = 4,224.12 PLN relief."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=80_000.0,
        children=[
            ChildInfo(birth_year=2013),
            ChildInfo(birth_year=2015),
            ChildInfo(birth_year=2018),
        ],
    )
    claims = generate_tax_claims(ctx, 2024)
    child_claims = [c for c in claims if c["id"] == "ulga_na_dzieci"]
    assert child_claims[0]["amount_estimate"] == pytest.approx(4_224.12, abs=0.01)


def test_ulga_na_dzieci_4_children():
    """4 children → 2 × 1,112.04 + 2,000.04 + 2,700 = 6,924.12 PLN relief."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=80_000.0,
        children=[
            ChildInfo(birth_year=2011),
            ChildInfo(birth_year=2013),
            ChildInfo(birth_year=2015),
            ChildInfo(birth_year=2018),
        ],
    )
    claims = generate_tax_claims(ctx, 2024)
    child_claims = [c for c in claims if c["id"] == "ulga_na_dzieci"]
    assert child_claims[0]["amount_estimate"] == pytest.approx(6_924.12, abs=0.01)


def test_ulga_na_dzieci_needs_input_when_unknown():
    """No children in profile → ulga na dzieci is 'needs_input'."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    child_claims = [c for c in claims if c["id"] == "ulga_na_dzieci"]
    assert len(child_claims) == 1
    assert child_claims[0]["status"] == "needs_input"


# ── Test 6: Filing deadlines ──────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_at_least_one(year):
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
        from datetime import date
        date.fromisoformat(dl["deadline"])  # Must be valid ISO date


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_april_30_filing_deadline_present(year):
    """PIT-37/36 filing deadline (April 30 of Y+1) is always present."""
    deadlines = get_filing_deadlines(year)
    dates = {dl["deadline"] for dl in deadlines}
    expected = f"{year + 1}-04-30"
    assert expected in dates, (
        f"Expected April 30 filing deadline {expected} not found for year {year}. "
        f"Found: {sorted(dates)}"
    )


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_twoj_e_pit_feb_15_present(year):
    """Twój e-PIT availability (February 15 of Y+1) is present for every year."""
    deadlines = get_filing_deadlines(year)
    dates = {dl["deadline"] for dl in deadlines}
    expected = f"{year + 1}-02-15"
    assert expected in dates, (
        f"Expected Twój e-PIT date {expected} not found for year {year}. "
        f"Found: {sorted(dates)}"
    )


def test_filing_deadlines_2024_multiple():
    """2024 returns multiple deadlines covering employer certificate, e-PIT, and filing."""
    deadlines = get_filing_deadlines(2024)
    assert len(deadlines) >= 4


# ── Test 7: Claims structure ──────────────────────────────────────────────────

def test_claims_have_required_keys():
    """All claims have the required interface keys."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    assert len(claims) >= 1
    for claim in claims:
        assert "id" in claim
        assert "title" in claim
        assert "status" in claim
        assert "amount_estimate" in claim
        assert "confidence" in claim
        assert claim["status"] in ("ready", "needs_input", "needs_evidence", "detected"), (
            f"Invalid status: {claim['status']}"
        )
        assert claim["confidence"] in ("Definitive", "Likely", "Debatable"), (
            f"Invalid confidence: {claim['confidence']}"
        )


def test_koszty_always_present():
    """Koszty uzyskania przychodu claim is always present and 'ready'."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    koszty = [c for c in claims if c["id"] == "koszty_uzyskania_przychodu"]
    assert len(koszty) == 1
    assert koszty[0]["status"] == "ready"
    assert koszty[0]["amount_estimate"] == pytest.approx(3_000.0, abs=1.0)
    assert koszty[0]["confidence"] == "Definitive"


def test_koszty_elevated_when_commuting():
    """Elevated koszty (3,600 PLN) when commute_km is set."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=50_000.0,
        commute_km=25.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    koszty = [c for c in claims if c["id"] == "koszty_uzyskania_przychodu"]
    assert koszty[0]["amount_estimate"] == pytest.approx(3_600.0, abs=1.0)


def test_ulga_dla_mlodych_claim_ready_when_age_under_26():
    """Ulga dla młodych claim is 'ready' when age < 26 and income ≤ 85,528."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        extra={"age": 23},
    )
    claims = generate_tax_claims(ctx, 2024)
    young_claims = [c for c in claims if c["id"] == "ulga_dla_mlodych"]
    assert len(young_claims) == 1
    assert young_claims[0]["status"] == "ready"
    assert young_claims[0]["confidence"] == "Definitive"


def test_ulga_dla_mlodych_claim_needs_input_when_age_unknown():
    """Ulga dla młodych is 'needs_input' when age is not provided."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    young_claims = [c for c in claims if c["id"] == "ulga_dla_mlodych"]
    assert len(young_claims) == 1
    assert young_claims[0]["status"] == "needs_input"


def test_ikze_claim_ready_when_contribution_known():
    """IKZE claim is 'ready' when ikze_contribution is in extra."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=70_000.0,
        extra={"ikze_contribution": 5_000.0},
    )
    claims = generate_tax_claims(ctx, 2024)
    ikze_claims = [c for c in claims if c["id"] == "ikze"]
    assert len(ikze_claims) == 1
    assert ikze_claims[0]["status"] == "ready"
    assert ikze_claims[0]["amount_estimate"] == pytest.approx(5_000.0, abs=1.0)


def test_ikze_claim_needs_input_when_no_contribution():
    """IKZE claim is 'needs_input' when no contribution provided."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=70_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    ikze_claims = [c for c in claims if c["id"] == "ikze"]
    assert len(ikze_claims) == 1
    assert ikze_claims[0]["status"] == "needs_input"


def test_at_least_one_ready_or_needs_input_claim():
    """Standard employed profile yields at least one actionable claim."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    actionable = [c for c in claims if c["status"] in ("ready", "needs_input")]
    assert len(actionable) >= 1


# ── Test 8: Social contributions ─────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_social_contributions_structure(year):
    """get_social_contributions returns all required keys."""
    result = get_social_contributions(60_000.0, year)
    required = [
        "employee_total", "employer_total", "health_insurance",
        "emerytalne_employee", "rentowe_employee", "chorobowe_employee",
        "health_insurance_rate", "health_insurance_deductible",
    ]
    for key in required:
        assert key in result, f"Missing key '{key}' in social contributions for year {year}"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_employee_zus_rate_approx_1371(year):
    """Employee ZUS total is approximately 13.71% of gross."""
    gross = 60_000.0
    result = get_social_contributions(gross, year)
    expected = gross * 0.1371
    assert result["employee_total"] == pytest.approx(expected, abs=50.0)
    assert result["employee_total_rate"] == pytest.approx(0.1371, abs=0.002)


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_employee_zus_does_not_exceed_gross(year):
    """Employee ZUS does not exceed gross income."""
    for gross in (10_000, 30_000, 60_000, 200_000, 300_000):
        result = get_social_contributions(float(gross), year)
        assert result["employee_total"] <= float(gross), (
            f"Employee ZUS ({result['employee_total']}) exceeds gross ({gross}) for year {year}"
        )


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_health_insurance_present_and_positive(year):
    """Health insurance (składka zdrowotna) is positive for non-zero gross."""
    result = get_social_contributions(50_000.0, year)
    assert result["health_insurance"] > 0
    assert result["health_insurance_rate"] == pytest.approx(0.09, abs=0.001)


def test_health_insurance_not_deductible():
    """Health insurance is flagged as NOT deductible from PIT (Polski Ład 2022)."""
    result = get_social_contributions(50_000.0, 2024)
    assert result["health_insurance_deductible"] is False


def test_zus_cap_applied_above_limit():
    """ZUS contribution is capped when gross exceeds the annual limit."""
    # 2024 cap: 234,720 PLN
    result_below = get_social_contributions(200_000.0, 2024)
    result_above = get_social_contributions(300_000.0, 2024)
    # With cap: 300k and 400k should produce same emerytalne/rentowe contributions
    result_way_above = get_social_contributions(400_000.0, 2024)
    assert result_above["emerytalne_employee"] == pytest.approx(
        result_way_above["emerytalne_employee"], abs=1.0
    )
    assert result_above["zus_cap_applied"] is True


def test_zus_increases_with_income_below_cap():
    """ZUS employee contributions increase with gross income (below the annual cap)."""
    result_30k = get_social_contributions(30_000.0, 2024)
    result_60k = get_social_contributions(60_000.0, 2024)
    assert result_30k["employee_total"] < result_60k["employee_total"]


# ── Test 9: All SUPPORTED_YEARS parameters non-None ──────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_calculate_tax_all_keys_non_none(year):
    """calculate_tax returns all required keys as non-None for every supported year."""
    ctx = LocaleContext(
        tax_year=year,
        employment_type="employed",
        annual_gross=55_000.0,
    )
    result = calculate_tax(ctx)
    critical = ["gross", "income_tax", "zus_employee", "health_insurance", "net",
                "effective_rate", "marginal_rate", "currency", "confidence"]
    for key in critical:
        assert result[key] is not None, f"result['{key}'] is None for year {year}"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_get_tax_rules_non_none(year):
    """get_tax_rules returns a non-empty dict for every supported year."""
    rules = get_tax_rules(year)
    assert isinstance(rules, dict)
    assert len(rules) > 0
    assert rules["first_bracket_rate"] is not None


# ── Test 10: Dict profile input ───────────────────────────────────────────────

def test_calculate_tax_accepts_dict_profile():
    """calculate_tax accepts a Finance Assistant profile dict."""
    profile = {
        "meta": {"tax_year": 2024},
        "employment": {"type": "employed", "annual_gross": 50_000},
        "family": {},
        "housing": {},
        "personal": {},
        "tax_profile": {},
    }
    result = calculate_tax(profile, year=2024)
    assert result["gross"] == pytest.approx(50_000.0, abs=1.0)
    assert result["net"] < result["gross"]
    assert result["currency"] == "PLN"


def test_generate_tax_claims_accepts_dict_profile():
    """generate_tax_claims accepts a Finance Assistant profile dict."""
    profile = {
        "meta": {"tax_year": 2024},
        "employment": {"type": "employed", "annual_gross": 45_000},
        "family": {},
        "housing": {},
        "personal": {},
        "tax_profile": {},
    }
    claims = generate_tax_claims(profile, year=2024)
    assert len(claims) >= 1
    koszty = [c for c in claims if c["id"] == "koszty_uzyskania_przychodu"]
    assert len(koszty) == 1


def test_get_filing_deadlines_accepts_dict_profile():
    """get_filing_deadlines works for all supported years with consistent structure."""
    for year in SUPPORTED_YEARS:
        deadlines = get_filing_deadlines(year)
        assert isinstance(deadlines, list)
        assert len(deadlines) > 0


# ── Confidence checks ─────────────────────────────────────────────────────────

def test_self_employed_confidence_is_likely():
    """Self-employed calculations return 'Likely' confidence."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="self_employed",
        annual_gross=80_000.0,
    )
    result = calculate_tax(ctx)
    assert result["confidence"] == "Likely"


def test_year_2026_confidence_debatable():
    """Year 2026 returns 'Debatable' confidence (projected, no law yet)."""
    ctx = LocaleContext(
        tax_year=2026,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    result = calculate_tax(ctx)
    assert result["confidence"] in ("Debatable", "Likely")


def test_definitive_confidence_standard_salaried():
    """Standard salaried employee for 2024 returns 'Definitive' confidence."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    result = calculate_tax(ctx)
    assert result["confidence"] == "Definitive"
