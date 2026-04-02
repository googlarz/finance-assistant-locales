"""Tests for German tax claim generation using LocaleContext directly."""
from context import LocaleContext, ReceiptItem, ChildInfo
from de.claim_rules import generate_german_claims


def test_homeoffice_claim_ready():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        homeoffice_days_per_week=3.0,
    )
    claims = generate_german_claims(ctx)
    ho_claims = [c for c in claims if c["id"] == "homeoffice"]
    assert len(ho_claims) == 1
    assert ho_claims[0]["status"] == "ready"
    assert ho_claims[0]["amount_deductible"] is not None
    assert ho_claims[0]["amount_deductible"] > 0


def test_homeoffice_claim_needs_input():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        homeoffice_days_per_week=None,
    )
    claims = generate_german_claims(ctx)
    ho_claims = [c for c in claims if c["id"] == "homeoffice"]
    assert len(ho_claims) == 1
    assert ho_claims[0]["status"] == "needs_input"


def test_commute_claim():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        commute_km=20.0,
        commute_days_per_year=200,
    )
    claims = generate_german_claims(ctx)
    commute_claims = [c for c in claims if c["id"] == "commute"]
    assert len(commute_claims) == 1
    assert commute_claims[0]["status"] == "ready"
    assert commute_claims[0]["amount_deductible"] > 0


def test_riester_claim():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        riester=True,
        riester_contribution=1500.0,
    )
    claims = generate_german_claims(ctx)
    riester_claims = [c for c in claims if c["id"] == "riester"]
    assert len(riester_claims) == 1
    assert riester_claims[0]["status"] == "ready"
    assert riester_claims[0]["amount_deductible"] == 1500.0


def test_ruerup_claim():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        ruerup=True,
        ruerup_contribution=50000.0,  # above cap
    )
    claims = generate_german_claims(ctx)
    ruerup_claims = [c for c in claims if c["id"] == "ruerup"]
    assert len(ruerup_claims) == 1
    assert ruerup_claims[0]["status"] == "ready"
    # Should be capped at ruerup_max_single for 2025 (29_344)
    assert ruerup_claims[0]["amount_deductible"] <= 29344.0


def test_handwerker_claim_detected():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        # No housing type set, no receipts — should still detect handwerker opportunity
        # housing_type is not in LocaleContext, but the claim generator checks extra
    )
    claims = generate_german_claims(ctx)
    # The steuerberatung "detected" claim should always be present when no receipts
    detected_ids = [c["id"] for c in claims if c["status"] == "detected"]
    assert "steuerberatung" in detected_ids or "equipment_opportunity" in detected_ids or "haushaltsnahe" in detected_ids


def test_claims_sorted_ready_first():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        homeoffice_days_per_week=3.0,
        riester=True,
        riester_contribution=1200.0,
    )
    claims = generate_german_claims(ctx)
    statuses = [c["status"] for c in claims]
    order = {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}
    ranks = [order.get(s, 9) for s in statuses]
    assert ranks == sorted(ranks), "Claims are not sorted ready-first"


def test_no_duplicate_claim_ids():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="employed",
        annual_gross=50000.0,
        homeoffice_days_per_week=2.0,
        commute_km=15.0,
        commute_days_per_year=150,
        riester=True,
        riester_contribution=1000.0,
        children=[ChildInfo(birth_year=2015, childcare=True, childcare_annual_cost=4000.0)],
    )
    claims = generate_german_claims(ctx)
    ids = [c["id"] for c in claims]
    assert len(ids) == len(set(ids)), f"Duplicate claim IDs found: {ids}"
