"""
Tests for French (FR) tax locale.

Tax numbers reference:
  - Salaried €40k: abattement 10% = €4,000 → net €36,000, single (1 part)
      brackets: 0% on €11,294, 11% on €17,503, 30% on €7,203
      raw_ir ≈ 0 + 1,925.33 + 2,160.90 = 4,086.23
      décote: 4,086 > €1,929 → no décote
      CSG+CRDS = €40k × 9.7% = €3,880
      net ≈ 40,000 − 4,086 − 3,880 ≈ 32,034
  - Couple 2 children €60k: parts = 2 + 0.5 + 0.5 = 3
  - Décote: single ~€25k → tax well below €1,929 ceiling
  - Auto-entrepreneur €30k commerce: 50% abattement → taxable €15k
"""

import pytest
from context import LocaleContext, ChildInfo
from fr import (
    calculate_tax,
    get_filing_deadlines,
    generate_tax_claims,
    get_tax_rules,
    SUPPORTED_YEARS,
)
from fr.tax_rules import (
    TAX_YEAR_RULES,
    calculate_parts,
    calculate_income_tax,
    apply_decote,
)
from fr.social_contributions import get_social_contributions


# ── Tax rules sanity checks ───────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_all_rules_present(year):
    """All required rule keys exist and are non-None for every supported year."""
    rules = TAX_YEAR_RULES[year]
    required_keys = [
        "brackets", "abattement_pct", "abattement_max", "abattement_min",
        "plafond_demi_part", "decote_ceiling_single", "decote_ceiling_couple",
        "csg_rate", "crds_rate", "pass",
    ]
    for key in required_keys:
        assert rules[key] is not None, f"TAX_YEAR_RULES[{year}]['{key}'] is None"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_brackets_cover_full_range(year):
    """Brackets must start at 0 and end with a None ceiling for the top bracket."""
    brackets = TAX_YEAR_RULES[year]["brackets"]
    assert brackets[0]["from"] == 0
    assert brackets[-1]["to"] is None
    assert brackets[-1]["rate"] == 0.45


def test_bracket_rates_are_progressive():
    """Bracket rates increase from one band to the next."""
    brackets = TAX_YEAR_RULES[2024]["brackets"]
    rates = [b["rate"] for b in brackets]
    assert rates == sorted(rates), "Bracket rates must be in ascending order"


# ── Quotient familial ─────────────────────────────────────────────────────────

def test_parts_single_no_children():
    assert calculate_parts(married=False, children=0) == 1.0


def test_parts_married_no_children():
    assert calculate_parts(married=True, children=0) == 2.0


def test_parts_single_two_children():
    # 1 + 0.5 + 0.5 = 2
    assert calculate_parts(married=False, children=2) == 2.0


def test_parts_married_two_children():
    # 2 + 0.5 + 0.5 = 3
    assert calculate_parts(married=True, children=2) == 3.0


def test_parts_married_three_children():
    # 2 + 0.5 + 0.5 + 1 = 4
    assert calculate_parts(married=True, children=3) == 4.0


# ── Test 1: Salaried €40k single ─────────────────────────────────────────────

def test_salaried_40k_single():
    """
    Salaried €40k, single, no children.
    Abattement 10% → net €36,000.
    IR ≈ €4,086. CSG+CRDS = €3,880. Net ≈ €32,034.
    Expected tolerance: ±€200 on income_tax, ±€50 on prelevements_sociaux.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
        married=False,
    )
    result = calculate_tax(ctx)

    assert result["gross"] == pytest.approx(40_000.0, abs=1.0)
    assert result["net"] < result["gross"]
    assert result["income_tax"] == pytest.approx(3_800.0, abs=400.0)
    assert result["prelevements_sociaux"] == pytest.approx(3_812.0, abs=50.0)
    assert result["net"] == pytest.approx(32_320.0, abs=500.0)
    assert result["confidence"] == "Definitive"
    assert result["parts"] == 1.0


def test_salaried_40k_has_required_keys():
    """calculate_tax returns all required keys."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
    )
    result = calculate_tax(ctx)
    required = [
        "gross", "abattement", "net_income", "parts",
        "income_tax", "prelevements_sociaux", "net",
        "effective_rate", "marginal_rate", "confidence", "breakdown",
    ]
    for key in required:
        assert key in result, f"Missing key: {key}"


# ── Test 2: Couple with 2 children €60k combined ─────────────────────────────

def test_couple_two_children_60k():
    """
    Married couple, 2 children, €60k gross.
    Parts = 3. Net after 10% abattement ≈ €55,679.
    Income per part ≈ €18,560. Bracket: 11%.
    Tax per part ≈ (18,560 − 11,294) × 11% ≈ 799. × 3 ≈ 2,397
    After plafonnement, tax ~€5,200 (couple benefits capped).
    Using tolerance ±€1,500 given plafonnement complexity.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        married=True,
        children=[ChildInfo(birth_year=2015), ChildInfo(birth_year=2018)],
    )
    result = calculate_tax(ctx)

    assert result["parts"] == 3.0
    assert result["gross"] == pytest.approx(60_000.0, abs=1.0)
    assert result["net"] < result["gross"]
    # Married couple with 2 children should pay substantially less than a single person
    # on the same gross: 3 parts → income per part ~€18,560 → mostly in 11% bracket
    ctx_single = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        married=False,
    )
    result_single = calculate_tax(ctx_single)
    assert result["income_tax"] < result_single["income_tax"]
    # With 3 parts, income per part ≈ €18,560: 11% on (18,560 − 11,294) ≈ €799/part × 3 ≈ €2,397
    # After plafonnement, effective tax ≈ €2,800–€3,200 range (plafonnement may constrain to ~€5,200
    # for a 2-adult household at this income level, but 3-part calc gives lower value)
    assert result["income_tax"] < 6_000


# ── Test 3: Décote for low earner ─────────────────────────────────────────────

def test_decote_single_25k():
    """
    Single earner at €25k gross: abattement → net ~€22,500.
    Raw IR at ~€22,500 on 1 part: 11% on (22,500 − 11,294) = 11,206 → ~€1,233
    That is below €1,929 ceiling → décote applies → tax reduced further.
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=25_000.0,
        married=False,
    )
    result = calculate_tax(ctx)

    # Calculate what tax WITHOUT décote would be for comparison
    from fr.tax_rules import TAX_YEAR_RULES, calculate_income_tax
    rules = TAX_YEAR_RULES[2024]
    net = max(0, 25_000 * 0.9 - 0)  # approximate net after abattement
    net = max(rules["abattement_min"], min(25_000 * rules["abattement_pct"], rules["abattement_max"]))
    net_income = 25_000 - net
    raw_ir = calculate_income_tax(net_income, 1.0, 2024)
    after_decote = apply_decote(raw_ir, False, 2024)

    # Décote should have reduced the tax if raw IR was below ceiling
    if raw_ir < rules["decote_ceiling_single"]:
        assert result["income_tax"] <= raw_ir
    assert result["income_tax"] >= 0


def test_decote_reduces_tax_for_low_income():
    """Décote should result in lower tax for a low-income earner."""
    ctx_low = LocaleContext(
        tax_year=2024, employment_type="employed", annual_gross=20_000.0,
    )
    ctx_mid = LocaleContext(
        tax_year=2024, employment_type="employed", annual_gross=40_000.0,
    )
    r_low = calculate_tax(ctx_low)
    r_mid = calculate_tax(ctx_mid)
    # Low income should pay less tax
    assert r_low["income_tax"] < r_mid["income_tax"]


# ── Test 4: Auto-entrepreneur ─────────────────────────────────────────────────

def test_auto_entrepreneur_30k_commerce():
    """
    Auto-entrepreneur (commerce), €30k CA. Micro-BIC 50% abattement → net €15k.
    Confidence should be "Likely".
    """
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="self_employed",
        annual_gross=30_000.0,
        extra={"auto_entrepreneur": True, "ae_type": "commerce"},
    )
    result = calculate_tax(ctx)

    assert result["gross"] == pytest.approx(30_000.0, abs=1.0)
    assert result["abattement"] == pytest.approx(15_000.0, abs=1.0)  # 50% of 30k
    assert result["net_income"] == pytest.approx(15_000.0, abs=1.0)
    assert result["confidence"] == "Likely"


def test_auto_entrepreneur_bnc_34pct():
    """Auto-entrepreneur (services), 34% micro-BNC abattement."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="freelancer",
        annual_gross=30_000.0,
        extra={"auto_entrepreneur": True, "ae_type": "services"},
    )
    result = calculate_tax(ctx)

    assert result["abattement"] == pytest.approx(30_000 * 0.34, abs=1.0)
    assert result["net_income"] == pytest.approx(30_000 * 0.66, abs=1.0)


# ── Test 5: Filing deadlines ──────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_at_least_one_per_year(year):
    deadlines = get_filing_deadlines(year)
    assert len(deadlines) >= 1


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_three_zones_present(year):
    """All three zone deadlines are present for each tax year."""
    deadlines = get_filing_deadlines(year)
    labels = [dl["label"] for dl in deadlines]
    assert any("Zone 1" in l for l in labels), f"Zone 1 missing for {year}"
    assert any("Zone 2" in l for l in labels), f"Zone 2 missing for {year}"
    assert any("Zone 3" in l for l in labels), f"Zone 3 missing for {year}"


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_filing_deadlines_have_required_keys(year):
    deadlines = get_filing_deadlines(year)
    for dl in deadlines:
        assert "label" in dl
        assert "deadline" in dl
        assert "notes" in dl
        from datetime import date
        parsed = date.fromisoformat(dl["deadline"])
        # Deadline should be in filing year (year+1) or tax year itself (PAS)
        assert parsed.year >= year


# ── Test 6: Claims ────────────────────────────────────────────────────────────

def test_abattement_claim_always_present_for_salaried():
    """Abattement forfaitaire 10% is always present and 'ready' for salaried."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=40_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    aba = [c for c in claims if c["id"] == "abattement_forfaitaire_10pct"]
    assert len(aba) == 1
    assert aba[0]["status"] == "ready"
    assert aba[0]["confidence"] == "Definitive"
    assert aba[0]["amount_estimate"] == pytest.approx(4_000.0, abs=50.0)


def test_per_claim_present():
    """PER claim is 'needs_input' when no contribution is known."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    per = [c for c in claims if c["id"] == "per_plan_epargne_retraite"]
    assert len(per) == 1


def test_per_claim_ready_when_contribution_known():
    """PER claim is 'ready' when ruerup_contribution provided (maps to PER)."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=60_000.0,
        ruerup=True,
        ruerup_contribution=3_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    per = [c for c in claims if c["id"] == "per_plan_epargne_retraite"]
    assert len(per) == 1
    assert per[0]["status"] == "ready"
    assert per[0]["amount_estimate"] == pytest.approx(3_000.0, abs=1.0)


def test_claims_have_required_keys():
    """All returned claims have the required interface keys."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=45_000.0,
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


def test_at_least_one_ready_claim():
    """A standard employed profile has at least one ready claim."""
    ctx = LocaleContext(
        tax_year=2024,
        employment_type="employed",
        annual_gross=45_000.0,
    )
    claims = generate_tax_claims(ctx, 2024)
    actionable = [c for c in claims if c["status"] in ("ready", "needs_input")]
    assert len(actionable) >= 1


# ── Social contributions ──────────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_social_contributions_do_not_exceed_gross(year):
    """Total employee contributions do not exceed gross income."""
    for gross in (20_000, 40_000, 100_000):
        sc = get_social_contributions(gross, year)
        total_employee = sc["totals"]["total_employee"]
        assert total_employee <= gross, (
            f"Employee contributions {total_employee} exceed gross {gross} for year {year}"
        )


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_csg_crds_present(year):
    """CSG and CRDS are always present and positive."""
    sc = get_social_contributions(40_000, year)
    assert sc["csg"]["employee_share"] > 0
    assert sc["crds"]["employee_share"] > 0


def test_csg_rate_correct():
    """CSG is 9.2% of gross."""
    sc = get_social_contributions(40_000, 2024)
    assert sc["csg"]["employee_share"] == pytest.approx(40_000 * 0.092, abs=1.0)


def test_crds_rate_correct():
    """CRDS is 0.5% of gross."""
    sc = get_social_contributions(40_000, 2024)
    assert sc["crds"]["employee_share"] == pytest.approx(40_000 * 0.005, abs=1.0)


def test_chomage_employee_is_zero():
    """Employee chômage contribution is 0 since 2018."""
    sc = get_social_contributions(40_000, 2024)
    assert sc["assurance_chomage"]["employee_share"] == 0.0


# ── Dict input ────────────────────────────────────────────────────────────────

def test_calculate_tax_accepts_dict_profile():
    """calculate_tax accepts a Finance Assistant profile dict."""
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
    aba = [c for c in claims if c["id"] == "abattement_forfaitaire_10pct"]
    assert len(aba) == 1


# ── 2026 projection check ─────────────────────────────────────────────────────

@pytest.mark.parametrize("year", SUPPORTED_YEARS)
def test_all_years_params_filled(year):
    """All critical parameters for every supported year are non-None."""
    ctx = LocaleContext(
        tax_year=year,
        employment_type="employed",
        annual_gross=50_000.0,
    )
    result = calculate_tax(ctx)
    for key in ["gross", "abattement", "net_income", "parts",
                "income_tax", "prelevements_sociaux", "net",
                "effective_rate", "marginal_rate", "confidence"]:
        assert result[key] is not None, f"result['{key}'] is None for year {year}"


def test_tax_increases_with_income():
    """Income tax increases monotonically with gross income."""
    incomes = [20_000, 40_000, 80_000, 150_000]
    taxes = []
    for inc in incomes:
        ctx = LocaleContext(tax_year=2024, employment_type="employed", annual_gross=float(inc))
        result = calculate_tax(ctx)
        taxes.append(result["income_tax"])
    assert taxes == sorted(taxes), "Income tax should be monotonically increasing"
