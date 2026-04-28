"""
US deduction discovery — which deductions likely apply given a profile.

Returns claims in the same 4-status format used across all locales:
  ready | needs_input | needs_evidence | detected
"""

from __future__ import annotations

from datetime import date


def generate_us_claims(ctx, year: int = None) -> list[dict]:
    year = year or date.today().year

    if hasattr(ctx, "gross_income"):
        gross = float(ctx.gross_income or 0)
        emp_type = getattr(ctx, "employment_type", "employed")
        extra = getattr(ctx, "extra", {}) or {}
        housing = getattr(ctx, "housing_type", None)
        has_mortgage = housing in ("mortgage", "owner")
    else:
        emp = ctx.get("employment", {}) or {}
        tp = ctx.get("tax_profile", {}) or {}
        gross = float(emp.get("annual_gross", 0) or 0)
        emp_type = emp.get("type", "employed")
        extra = tp.get("extra", {}) or {}
        housing = ctx.get("housing", {}).get("type")
        has_mortgage = housing in ("mortgage", "owner")

    claims = []

    # 401(k) — always relevant for W-2 employees
    pretax_401k = extra.get("pretax_401k", 0) or 0
    if pretax_401k:
        claims.append({
            "id": "401k_contribution",
            "title": "401(k) pre-tax contributions",
            "status": "ready",
            "confidence": "Definitive",
            "domain": "tax",
            "detail": f"${pretax_401k:,.0f} in pre-tax 401(k) contributions reduce your AGI directly.",
            "next_action": None,
        })
    else:
        claims.append({
            "id": "401k_contribution",
            "title": "401(k) pre-tax contributions",
            "status": "needs_input",
            "confidence": "Likely",
            "domain": "tax",
            "detail": "Most W-2 employees have access to a 401(k). Pre-tax contributions reduce taxable income dollar-for-dollar.",
            "next_action": "Tell me how much you contributed to your 401(k) this year.",
        })

    # HSA
    hsa = extra.get("pretax_hsa", 0) or 0
    if hsa:
        claims.append({
            "id": "hsa",
            "title": "HSA contributions",
            "status": "ready",
            "confidence": "Definitive",
            "domain": "tax",
            "detail": f"${hsa:,.0f} in HSA contributions are fully deductible.",
            "next_action": None,
        })

    # Student loan interest (phases out at higher income)
    if gross < 90_000:
        claims.append({
            "id": "student_loan_interest",
            "title": "Student loan interest deduction",
            "status": "needs_input",
            "confidence": "Likely",
            "domain": "tax",
            "detail": "Up to $2,500/year in student loan interest is deductible if your income qualifies.",
            "next_action": "Do you have student loans? If so, how much interest did you pay this year?",
        })

    # Mortgage interest
    if has_mortgage:
        claims.append({
            "id": "mortgage_interest",
            "title": "Mortgage interest (itemized)",
            "status": "needs_input",
            "confidence": "Likely",
            "domain": "tax",
            "detail": "Mortgage interest is deductible if you itemize. Worth comparing to your standard deduction.",
            "next_action": "How much mortgage interest did you pay this year? (Check your Form 1098.)",
        })

    # Self-employed deductions
    if emp_type in ("self_employed", "freelancer"):
        claims.append({
            "id": "self_employment_tax_deduction",
            "title": "½ self-employment tax deduction",
            "status": "ready",
            "confidence": "Definitive",
            "domain": "tax",
            "detail": "Self-employed filers can deduct half their SE tax from gross income.",
            "next_action": None,
        })
        claims.append({
            "id": "home_office",
            "title": "Home office deduction",
            "status": "needs_input",
            "confidence": "Likely",
            "domain": "tax",
            "detail": "If you have a dedicated workspace at home, you can deduct a portion of rent/mortgage + utilities.",
            "next_action": "Do you work from a dedicated home office? Roughly what % of your home does it occupy?",
        })
        claims.append({
            "id": "sep_ira",
            "title": "SEP-IRA contributions",
            "status": "needs_input",
            "confidence": "Likely",
            "domain": "tax",
            "detail": "Self-employed can contribute up to 25% of net self-employment income to a SEP-IRA (max $69,000 for 2024).",
            "next_action": "Did you make SEP-IRA contributions this year?",
        })

    return claims
