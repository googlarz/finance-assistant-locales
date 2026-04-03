"""
UK tax deduction and allowance discovery.

Generates applicable claims for common UK tax reliefs and allowances.
Each claim follows the standard Finance Assistant locale interface:
  id, title, status, amount_estimate, confidence

Sources:
  https://www.gov.uk/income-tax-reliefs
  https://www.gov.uk/marriage-allowance
  https://www.gov.uk/tax-relief-for-employees
  https://www.gov.uk/guidance/tax-relief-for-working-from-home
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import get_tax_year_rules

if TYPE_CHECKING:
    from ..context import LocaleContext


def generate_uk_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """
    Discover applicable UK tax deduction claims for the given profile and year.

    Args:
        ctx: LocaleContext or Finance Assistant profile dict.
        year: Override tax year (uses ctx.tax_year if not provided).

    Returns:
        List of claim dicts, sorted ready → needs_input → needs_evidence → detected.
    """
    if isinstance(ctx, dict):
        try:
            from ..context import LocaleContext
        except ImportError:
            from context import LocaleContext  # type: ignore
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)

    if year is None:
        year = ctx.tax_year

    rules = get_tax_year_rules(year)
    gross = float(ctx.annual_gross or 0.0)
    is_employee = ctx.employment_type in ("employed",)
    is_self_employed = ctx.employment_type in ("self_employed", "freelancer")
    married = ctx.married
    extra = ctx.extra or {}

    # Determine marital status from extra if not set on ctx
    marital_status_known = married or extra.get("marital_status_known", False)

    claims = []

    # ── 1. Personal allowance — always ready ──────────────────────────────
    allowance = rules["personal_allowance"]
    if gross > rules["personal_allowance_taper_threshold"]:
        taper_reduction = min(
            (gross - rules["personal_allowance_taper_threshold"]) / 2,
            allowance,
        )
        effective_allowance = max(0.0, allowance - taper_reduction)
        claims.append(_claim(
            "personal_allowance",
            "Personal Allowance",
            "ready",
            round(effective_allowance, 2),
            "Definitive",
            f"Tapered personal allowance: £{effective_allowance:,.0f} "
            f"(reduced from £{allowance:,} due to income over £{rules['personal_allowance_taper_threshold']:,}).",
        ))
    else:
        claims.append(_claim(
            "personal_allowance",
            "Personal Allowance",
            "ready",
            float(allowance),
            "Definitive",
            f"Standard personal allowance of £{allowance:,} — applies automatically. "
            "No action required for most employees (PAYE handles this).",
        ))

    # ── 2. Marriage allowance ─────────────────────────────────────────────
    marriage_allowance = rules["marriage_allowance"]
    if not marital_status_known:
        claims.append(_claim(
            "marriage_allowance",
            "Marriage Allowance",
            "needs_input",
            float(marriage_allowance),
            "Likely",
            "If married or in a civil partnership and the lower earner has "
            f"income below £{rules['basic_rate_limit']:,}, up to £{marriage_allowance:,} "
            "of personal allowance can be transferred to the higher earner.",
        ))
    elif married and gross > rules["personal_allowance"] and gross <= rules["basic_rate_limit"]:
        # Lower earner — could transfer to partner
        claims.append(_claim(
            "marriage_allowance",
            "Marriage Allowance (transfer to partner)",
            "ready",
            float(marriage_allowance),
            "Likely",
            f"You appear to be the lower earner. You can transfer £{marriage_allowance:,} "
            "of your personal allowance to your partner, saving up to £252 tax.",
        ))
    elif married and gross > rules["basic_rate_limit"]:
        # Higher earner — may receive from partner
        claims.append(_claim(
            "marriage_allowance",
            "Marriage Allowance (receive from partner)",
            "needs_input",
            float(marriage_allowance),
            "Likely",
            f"If your partner earns below £{rules['basic_rate_limit']:,}, "
            f"they can transfer £{marriage_allowance:,} of their personal allowance to you.",
        ))

    # ── 3. Pension contributions ──────────────────────────────────────────
    pension_contrib = float(
        ctx.ruerup_contribution or ctx.bav_contribution or
        extra.get("pension_contribution", 0) or 0
    )
    pension_annual_allowance = rules["pension_annual_allowance"]
    if pension_contrib > 0:
        capped = min(pension_contrib, pension_annual_allowance)
        claims.append(_claim(
            "pension_contributions",
            "Pension Contributions",
            "ready",
            capped,
            "Definitive",
            f"Pension contributions receive full tax relief at your marginal rate. "
            f"Annual allowance: £{pension_annual_allowance:,}. "
            "Employer contributions also count toward the allowance.",
        ))
    else:
        claims.append(_claim(
            "pension_contributions",
            "Pension Contributions",
            "needs_input",
            0.0,
            "Likely",
            f"Add your annual pension contribution amount. Relief is given at your "
            f"marginal rate, up to £{pension_annual_allowance:,} annual allowance.",
        ))

    # ── 4. Gift Aid donations ─────────────────────────────────────────────
    donation_receipts = [
        r for r in ctx.receipts
        if (r.category if hasattr(r, "category") else r.get("category")) == "donation"
    ]
    if donation_receipts:
        total_donations = sum(
            float(r.amount if hasattr(r, "amount") else r.get("amount", 0))
            for r in donation_receipts
        )
        # Gift Aid adds 25p per £1 donated (basic rate reclaim by charity)
        gift_aid_uplift = total_donations * 0.25
        claims.append(_claim(
            "gift_aid_donations",
            "Gift Aid Donations",
            "needs_evidence",
            round(gift_aid_uplift, 2),
            "Likely",
            f"Gift Aid adds 25% uplift to your donations (charity reclaims basic rate). "
            f"If you pay higher rate tax, you can claim the difference via Self Assessment. "
            f"Total donations: £{total_donations:,.2f}. Keep Gift Aid declarations.",
        ))
    else:
        claims.append(_claim(
            "gift_aid_donations",
            "Gift Aid Donations",
            "detected",
            0.0,
            "Likely",
            "If you donated to UK charities under Gift Aid, the charity reclaims "
            "basic rate (25p per £1). Higher/additional rate taxpayers can reclaim "
            "extra relief via Self Assessment. Add donation receipts if applicable.",
        ))

    # ── 5. ISA allowance opportunity ─────────────────────────────────────
    isa_allowance = rules["isa_allowance"]
    isa_used = float(extra.get("isa_contribution", 0) or 0)
    if isa_used < isa_allowance:
        unused = isa_allowance - isa_used
        claims.append(_claim(
            "isa_allowance",
            "ISA Allowance",
            "detected",
            unused,
            "Definitive",
            f"You have £{unused:,.0f} of unused ISA allowance for this tax year "
            f"(annual limit £{isa_allowance:,}). Savings and investments inside an ISA "
            "are free of income tax and CGT. Allowance resets each tax year.",
        ))

    # ── 6. Working from home ──────────────────────────────────────────────
    wfh_rate_per_week = 6.0  # HMRC flat rate £6/week for employees
    wfh_annual = wfh_rate_per_week * 52  # £312/year

    if is_employee:
        ho_days_pw = ctx.homeoffice_days_per_week
        if ho_days_pw is not None and ho_days_pw > 0:
            claims.append(_claim(
                "working_from_home",
                "Working from Home (HMRC flat rate)",
                "ready",
                wfh_annual,
                "Likely",
                f"HMRC flat rate of £{wfh_rate_per_week}/week (£{wfh_annual:.0f}/year) "
                "for employees required to work from home. Claim via Self Assessment "
                "or HMRC online service. Keep evidence of employer requirement.",
            ))
        else:
            claims.append(_claim(
                "working_from_home",
                "Working from Home (HMRC flat rate)",
                "needs_input",
                wfh_annual,
                "Likely",
                f"Employees required to work from home can claim £{wfh_rate_per_week}/week "
                f"(£{wfh_annual:.0f}/year) flat rate. Confirm whether you work from home "
                "and whether your employer requires it.",
            ))

    # ── 7. Professional subscriptions ─────────────────────────────────────
    subscription_receipts = [
        r for r in ctx.receipts
        if (r.category if hasattr(r, "category") else r.get("category"))
        in ("professional_subscription", "union_dues", "fortbildung")
    ]
    if subscription_receipts:
        total_subs = sum(
            float(r.amount if hasattr(r, "amount") else r.get("amount", 0))
            for r in subscription_receipts
        )
        claims.append(_claim(
            "professional_subscriptions",
            "Professional Subscriptions",
            "ready",
            round(total_subs, 2),
            "Likely",
            "Fees paid to HMRC-approved professional bodies are fully deductible "
            "against employment income. Keep membership receipts or statements.",
        ))
    else:
        claims.append(_claim(
            "professional_subscriptions",
            "Professional Subscriptions",
            "needs_evidence",
            0.0,
            "Likely",
            "If you pay fees to a HMRC-approved professional body (e.g. ICAEW, BMA, "
            "Law Society), the subscription is deductible. Add receipts to claim.",
        ))

    # ── 8. Mileage allowance ──────────────────────────────────────────────
    car_business_miles = float(extra.get("car_business_miles", 0) or 0)
    if car_business_miles > 0:
        # 45p/mile first 10,000 miles, 25p after (HMRC Approved Mileage Allowance)
        first_10k = min(car_business_miles, 10_000)
        over_10k = max(0.0, car_business_miles - 10_000)
        mileage_allowance = first_10k * 0.45 + over_10k * 0.25
        claims.append(_claim(
            "mileage_allowance",
            "Business Mileage Allowance",
            "ready",
            round(mileage_allowance, 2),
            "Likely",
            f"HMRC approved mileage: 45p/mile first 10,000 miles, 25p after. "
            f"Business miles claimed: {car_business_miles:,.0f}. "
            "Keep a mileage log with journey purpose, date, and distance.",
        ))
    else:
        claims.append(_claim(
            "mileage_allowance",
            "Business Mileage Allowance",
            "needs_input",
            0.0,
            "Likely",
            "If you use your own vehicle for business journeys (not commuting), "
            "you can claim 45p/mile for the first 10,000 miles, 25p after. "
            "Add car_business_miles to your profile to calculate the allowance.",
        ))

    # ── 9. Capital gains allowance ────────────────────────────────────────
    cg_allowance = rules["capital_gains_allowance"]
    has_investments = extra.get("has_investments", False) or extra.get("investments", False)
    if has_investments:
        claims.append(_claim(
            "capital_gains_allowance",
            "Capital Gains Tax Annual Exemption",
            "detected",
            float(cg_allowance),
            "Definitive",
            f"You have investments that may generate capital gains. "
            f"The annual CGT exemption is £{cg_allowance:,}. Gains above this are "
            "taxed at 18% (basic rate) or 24% (higher/additional rate) for non-residential property. "
            "Consider timing disposals to use the annual exemption each year.",
        ))
    else:
        claims.append(_claim(
            "capital_gains_allowance",
            "Capital Gains Tax Annual Exemption",
            "detected",
            float(cg_allowance),
            "Definitive",
            f"If you sold investments, property (other than your home), or other assets, "
            f"you have a £{cg_allowance:,} annual CGT exemption. Gains above this are taxable. "
            "Flag if you had any disposals this tax year.",
        ))

    # ── Sort: ready first, then by amount descending ──────────────────────
    claims.sort(key=lambda c: (
        {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}.get(c["status"], 9),
        -(c.get("amount_estimate") or 0),
        c["title"],
    ))

    return claims


def _claim(claim_id, title, status, amount_estimate, confidence, notes):
    return {
        "id": claim_id,
        "title": title,
        "status": status,
        "amount_estimate": round(float(amount_estimate), 2) if amount_estimate is not None else 0.0,
        "confidence": confidence,
        "notes": notes,
    }
