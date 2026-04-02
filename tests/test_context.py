"""Tests for LocaleContext construction and from_finance_profile()."""
from context import LocaleContext, ChildInfo, ReceiptItem


def test_default_context():
    ctx = LocaleContext(tax_year=2025)
    assert ctx.tax_year == 2025
    assert ctx.employment_type == "employed"
    assert ctx.annual_gross == 0.0
    assert ctx.tax_class == "I"
    assert ctx.church_tax is False
    assert ctx.married is False
    assert ctx.children == []
    assert ctx.receipts == []
    assert ctx.homeoffice_days_per_week is None
    assert ctx.commute_km == 0.0
    assert ctx.disability_grade == 0
    assert ctx.expat is False
    assert ctx.extra == {}


def test_direct_construction():
    ctx = LocaleContext(
        tax_year=2025,
        employment_type="freelancer",
        annual_gross=80000.0,
        side_income=5000.0,
        tax_class="III",
        church_tax=True,
        region="Bayern",
        married=True,
        children=[ChildInfo(birth_year=2015, childcare=True, childcare_annual_cost=6000.0)],
        homeoffice_days_per_week=4.0,
        commute_km=30.0,
        commute_days_per_year=180,
        riester=True,
        riester_contribution=1500.0,
        ruerup=True,
        ruerup_contribution=10000.0,
        bav=True,
        bav_contribution=2000.0,
        union_dues=300.0,
        disability_grade=50,
        receipts=[ReceiptItem(category="equipment", amount=1200.0, business_use_pct=80.0)],
        expat=False,
        dba_relevant=True,
        extra={"custom_key": "value"},
    )
    assert ctx.annual_gross == 80000.0
    assert ctx.tax_class == "III"
    assert ctx.married is True
    assert len(ctx.children) == 1
    assert ctx.children[0].birth_year == 2015
    assert ctx.riester_contribution == 1500.0
    assert ctx.union_dues == 300.0
    assert ctx.disability_grade == 50
    assert ctx.extra["custom_key"] == "value"


def test_from_finance_profile():
    profile = {
        "meta": {"tax_year": 2025},
        "employment": {"type": "employed", "annual_gross": 65000, "side_income": 2000},
        "tax_profile": {
            "tax_class": "I",
            "church_tax": False,
            "extra": {
                "riester": True,
                "riester_contribution": 1200,
                "ruerup": False,
                "bav": False,
                "gewerkschaft_beitrag": 240,
                "disability_grade": 0,
            },
        },
        "family": {"status": "single", "children": []},
        "housing": {
            "homeoffice_days_per_week": 3,
            "commute_km": 20,
            "commute_days_per_year": 200,
        },
        "personal": {"region": "Berlin"},
        "current_year_receipts": [],
    }
    ctx = LocaleContext.from_finance_profile(profile)
    assert ctx.tax_year == 2025
    assert ctx.employment_type == "employed"
    assert ctx.annual_gross == 65000.0
    assert ctx.side_income == 2000.0
    assert ctx.tax_class == "I"
    assert ctx.married is False
    assert ctx.homeoffice_days_per_week == 3
    assert ctx.commute_km == 20.0
    assert ctx.commute_days_per_year == 200
    assert ctx.riester is True
    assert ctx.riester_contribution == 1200.0
    assert ctx.union_dues == 240.0
    assert ctx.region == "Berlin"


def test_from_finance_profile_children():
    profile = {
        "meta": {"tax_year": 2025},
        "employment": {"type": "employed", "annual_gross": 50000},
        "tax_profile": {"tax_class": "III", "extra": {}},
        "family": {
            "status": "married",
            "children": [
                {"birth_year": 2018, "childcare": True, "childcare_annual_cost": 5000},
                {"birth_year": 2020, "kita": True, "kita_annual_cost": 4500},
            ],
        },
        "housing": {},
        "personal": {},
        "current_year_receipts": [],
    }
    ctx = LocaleContext.from_finance_profile(profile)
    assert ctx.married is True
    assert len(ctx.children) == 2
    assert ctx.children[0].birth_year == 2018
    assert ctx.children[0].childcare is True
    assert ctx.children[0].childcare_annual_cost == 5000.0
    assert ctx.children[1].birth_year == 2020
    assert ctx.children[1].childcare is True
    assert ctx.children[1].childcare_annual_cost == 4500.0


def test_from_finance_profile_receipts():
    profile = {
        "meta": {"tax_year": 2025},
        "employment": {"type": "employed", "annual_gross": 50000},
        "tax_profile": {"tax_class": "I", "extra": {}},
        "family": {"status": "single"},
        "housing": {},
        "personal": {},
        "current_year_receipts": [
            {"category": "equipment", "amount": 1500.0, "business_use_pct": 100.0, "description": "laptop"},
            {"category": "donation", "amount": 500.0},
            {"category": "equipment", "amount": 300.0, "deductible_amount": 200.0},
        ],
    }
    ctx = LocaleContext.from_finance_profile(profile)
    assert len(ctx.receipts) == 3
    assert ctx.receipts[0].category == "equipment"
    assert ctx.receipts[0].amount == 1500.0
    assert ctx.receipts[0].description == "laptop"
    assert ctx.receipts[1].category == "donation"
    assert ctx.receipts[2].deductible_amount == 200.0
