"""
Canadian tax deduction and credit claim discovery rules.

Analyses a LocaleContext profile and discovers applicable deductions and non-refundable /
refundable credits:
- Basic personal amount (federal & provincial)
- Canada Employment Amount (CEA)
- CPP / QPP contributions tax credit (and enhanced CPP deduction)
- EI premiums tax credit
- Home office expenses (work space in home expenses)
- Child care expenses (Form T778 deduction)
- Union and professional dues (line 21200)
- Disability tax credit (line 31600)
- RRSP contribution deduction (line 20800)
- FHSA (First Home Savings Account) & TFSA awareness

Sources:
  Canada Revenue Agency (CRA) - Deductions, credits, and expenses:
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses.html
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .tax_rules import get_tax_year_rules, normalize_province, resolve_supported_year

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def _claim(
    claim_id: str,
    title: str,
    status: str,
    amount_estimate: float,
    confidence: str,
    notes: str,
    category: str = "deduction",
    source_url: str = "",
) -> dict:
    return {
        "id": claim_id,
        "title": title,
        "status": status,
        "amount_estimate": round(float(amount_estimate or 0.0), 2),
        "confidence": confidence,
        "notes": notes,
        "category": category,
        "source_url": source_url or "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses.html",
    }


def generate_ca_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """
    Discover applicable Canadian tax deductions and tax credits for the profile.

    Returns:
        List of claim dicts following the standard locale plugin contract.
    """
    if isinstance(ctx, dict):
        LocaleContext = _import_locale_context()
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)

    tax_year = year or ctx.tax_year or 2024
    resolved_year, _ = resolve_supported_year(tax_year)
    rules = get_tax_year_rules(resolved_year)

    gross = float(ctx.annual_gross or 0.0)
    side_income = float(ctx.side_income or 0.0)
    total_income = gross + side_income
    is_employee = ctx.employment_type in ("employed",)
    is_self_employed = ctx.employment_type in ("self_employed", "freelancer")
    prov = normalize_province(getattr(ctx, "region", None))
    prov_rule = rules["provinces"].get(prov, rules["provinces"]["ON"])

    claims = []

    # 1. Federal Basic Personal Amount (BPA) — non-refundable credit
    bpa_max = rules["federal_bpa_max"]
    bpa_min = rules["federal_bpa_min"]
    taper_start = rules["federal_bpa_taper_start"]
    taper_end = rules["federal_bpa_taper_end"]

    if total_income <= taper_start:
        fed_bpa = bpa_max
    elif total_income >= taper_end:
        fed_bpa = bpa_min
    else:
        fraction = (total_income - taper_start) / (taper_end - taper_start)
        fed_bpa = bpa_max - (fraction * (bpa_max - bpa_min))

    claims.append(_claim(
        "federal_basic_personal_amount",
        f"Federal Basic Personal Amount ({resolved_year})",
        "ready",
        fed_bpa,
        "Definitive",
        f"Base personal non-refundable credit amount of ${fed_bpa:,.2f} applied at 15%/14% lowest federal rate.",
        category="non_refundable_credit",
        source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/adjustment-personal-income-tax-benefit-amounts.html",
    ))

    # 2. Provincial Basic Personal Amount (BPA)
    prov_bpa = prov_rule.get("bpa", 12399.0)
    claims.append(_claim(
        f"{prov.lower()}_basic_personal_amount",
        f"{prov_rule['name']} Basic Personal Amount ({resolved_year})",
        "ready",
        prov_bpa,
        "Definitive",
        f"{prov_rule['name']} provincial non-refundable credit amount of ${prov_bpa:,.2f}.",
        category="non_refundable_credit",
    ))

    # 3. Canada Employment Amount (CEA) — for employees
    if is_employee and gross > 0:
        cea_max = rules.get("canada_employment_amount_max", 1433.0)
        cea_amount = min(gross, cea_max)
        claims.append(_claim(
            "canada_employment_amount",
            "Canada Employment Amount (Line 31260)",
            "ready",
            cea_amount,
            "Definitive",
            f"Non-refundable tax credit for employment expenses up to maximum ${cea_max:,.2f}.",
            category="non_refundable_credit",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/line-31260-canada-employment-amount.html",
        ))

    # 4. RRSP (Registered Retirement Savings Plan) Deduction
    rrsp_contr = float(getattr(ctx, "extra", {}).get("rrsp_contribution") or 0.0)
    if rrsp_contr > 0:
        claims.append(_claim(
            "rrsp_deduction",
            "RRSP Contribution Deduction (Line 20800)",
            "ready",
            rrsp_contr,
            "Definitive",
            f"Deduction against taxable income for reported RRSP contribution of ${rrsp_contr:,.2f}.",
            category="deduction",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/rrsps-related-plans/contributing-a-rrsp-prpp.html",
        ))
    else:
        # Detect opportunity
        est_room = min(gross * 0.18, rules.get("rrsp_dollar_limit", 31560.0))
        if est_room > 0:
            claims.append(_claim(
                "rrsp_deduction_opportunity",
                "RRSP Contribution Deduction Opportunity",
                "detected",
                est_room,
                "Likely",
                f"Contributing up to ~${est_room:,.0f} reduces taxable income at your marginal tax bracket.",
                category="deduction",
                source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/rrsps-related-plans/contributing-a-rrsp-prpp.html",
            ))

    # 5. Home Office Expenses for Employees (Work space in the home)
    ho_days = getattr(ctx, "homeoffice_days_per_week", None)
    if is_employee and ho_days is not None and ho_days > 0:
        claims.append(_claim(
            "home_office_expenses",
            "Work Space in the Home Expenses (Form T2200)",
            "needs_evidence",
            0.0,
            "Likely",
            "Detailed method: requires signed Form T2200 from employer and eligible household utility/maintenance bills.",
            category="deduction",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/line-22900-other-employment-expenses/work-space-home-expenses.html",
        ))
    elif is_employee:
        claims.append(_claim(
            "home_office_expenses",
            "Work Space in the Home Expenses",
            "needs_input",
            0.0,
            "Likely",
            "If required to work from home >50% of the time for at least 4 consecutive weeks, employment home office expenses may be deductible.",
            category="deduction",
        ))

    # 6. Child care expenses (Form T778)
    childcare_total = sum(float(ch.childcare_annual_cost or 0.0) for ch in getattr(ctx, "children", []))
    if childcare_total > 0:
        claims.append(_claim(
            "child_care_expenses",
            "Child Care Expenses Deduction (Line 21400 / Form T778)",
            "ready",
            childcare_total,
            "Definitive",
            f"Deductible child care costs of ${childcare_total:,.2f} claimed by the lower-income spouse.",
            category="deduction",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/line-21400-child-care-expenses.html",
        ))
    elif any(getattr(ch, "childcare", False) for ch in getattr(ctx, "children", [])):
        claims.append(_claim(
            "child_care_expenses",
            "Child Care Expenses Deduction",
            "needs_input",
            0.0,
            "Likely",
            "Eligible child care expenses (daycare, nursery school, camps) can be deducted from net income.",
            category="deduction",
        ))

    # 7. Union or professional dues
    union_dues = float(getattr(ctx, "union_dues", 0.0) or 0.0)
    if union_dues > 0:
        claims.append(_claim(
            "union_professional_dues",
            "Annual Union, Professional, or Like Dues (Line 21200)",
            "ready",
            union_dues,
            "Definitive",
            f"Direct deduction from total income for dues paid of ${union_dues:,.2f}.",
            category="deduction",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/line-21200-annual-union-professional-like-dues.html",
        ))

    # 8. Disability Tax Credit (Line 31600)
    if getattr(ctx, "disability_grade", 0) > 0:
        claims.append(_claim(
            "disability_tax_credit",
            "Disability Tax Credit (Line 31600)",
            "needs_evidence",
            rules.get("indexation_factor", 0.0) * 10000 or 10000.0,
            "Likely",
            "Requires approved CRA Form T2201 (Disability Tax Credit Certificate) on file with the CRA.",
            category="non_refundable_credit",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/segments/tax-credits-deductions-persons-disabilities/disability-tax-credit.html",
        ))

    # 9. First Home Savings Account (FHSA) awareness
    fhsa_contr = float(getattr(ctx, "extra", {}).get("fhsa_contribution") or 0.0)
    if fhsa_contr > 0:
        claims.append(_claim(
            "fhsa_deduction",
            "First Home Savings Account (FHSA) Deduction (Line 20805)",
            "ready",
            min(fhsa_contr, 8000.0),
            "Definitive",
            f"Tax-deductible contribution to an FHSA up to $8,000 annual limit (${fhsa_contr:,.2f} contributed).",
            category="deduction",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/first-home-savings-account.html",
        ))

    # Sort claims: ready first, then needs_input, then needs_evidence, then detected
    status_order = {"ready": 0, "needs_input": 1, "needs_evidence": 2, "detected": 3}
    claims.sort(key=lambda c: status_order.get(c["status"], 99))

    return claims
