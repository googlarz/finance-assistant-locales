"""
Irish tax credit and deduction discovery rules.

Analyses a LocaleContext profile and identifies credits, reliefs, and
deductions the taxpayer may be eligible to claim.

Sources:
  https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/index.aspx
  https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/health-and-age/medical-expenses/index.aspx
  https://www.revenue.ie/en/property/rental-income/index.aspx
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import get_tax_year_rules, resolve_supported_year

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def generate_ie_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """
    Discover applicable Irish tax credits and reliefs for the given profile.

    Returns a list of claim dicts with: id, title, status, amount_estimate,
    confidence, notes, and source_url.
    """
    if isinstance(ctx, dict):
        LocaleContext = _import_locale_context()
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)

    tax_year = year or ctx.tax_year or 2025
    resolved_year, _ = resolve_supported_year(tax_year)
    rules = get_tax_year_rules(resolved_year)

    claims = []

    # ── Rent credit (introduced 2022) ────────────────────────────────────
    claims.append({
        "id": "ie_rent_credit",
        "title": "Rent Tax Credit",
        "status": "needs_input",
        "amount_estimate": rules.get("rent_credit_single", 1000),
        "confidence": 0.6,
        "notes": (
            f"€{rules.get('rent_credit_single', 1000)} credit per person for "
            "qualifying rent paid. Requires landlord details and proof of payment. "
            "Claim via myAccount Form 12."
        ),
        "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/land-and-property/rent-tax-credit/index.aspx",
    })

    # ── Medical expenses (flat rate relief) ──────────────────────────────
    claims.append({
        "id": "ie_medical_expenses",
        "title": "Medical Expenses Relief",
        "status": "needs_evidence",
        "amount_estimate": None,
        "confidence": 0.7,
        "notes": (
            "Tax relief at 20% on qualifying medical expenses not reimbursed "
            "by VHI/Laya/Irish Life. Includes GP visits, prescriptions, physio, "
            "dental (non-routine). Keep all receipts."
        ),
        "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/health-and-age/medical-expenses/index.aspx",
    })

    # ── Flat-rate expenses (employment) ──────────────────────────────────
    if ctx.employment_type in ("employed", "paye"):
        claims.append({
            "id": "ie_flat_rate_expenses",
            "title": "Flat Rate Expenses",
            "status": "needs_input",
            "amount_estimate": None,
            "confidence": 0.5,
            "notes": (
                "Revenue allows flat-rate expense deductions for specific "
                "occupations (nurses, teachers, shop assistants, etc.). "
                "Check if your job category qualifies. No receipts needed."
            ),
            "source_url": "https://www.revenue.ie/en/jobs-and-pensions/taxation-of-employer-benefits/flat-rate-expense-allowances/index.aspx",
        })

    # ── Remote working relief ────────────────────────────────────────────
    if ctx.employment_type in ("employed", "paye"):
        claims.append({
            "id": "ie_remote_working",
            "title": "Remote Working Relief (e-Working)",
            "status": "needs_input",
            "amount_estimate": None,
            "confidence": 0.6,
            "notes": (
                "30% of the cost of electricity, heating, and broadband for days "
                "worked from home. Employer may pay €3.20/day tax-free, or you "
                "claim the balance directly."
            ),
            "source_url": "https://www.revenue.ie/en/jobs-and-pensions/taxation-of-employer-benefits/e-working-and-tax/index.aspx",
        })

    # ── Pension contributions ────────────────────────────────────────────
    claims.append({
        "id": "ie_pension_contributions",
        "title": "Pension Contribution Relief",
        "status": "needs_input",
        "amount_estimate": None,
        "confidence": 0.8,
        "notes": (
            "Tax relief at marginal rate (20% or 40%) on personal pension "
            f"contributions up to age-related limits (15-40% of earnings, "
            f"max €{rules['pension_earnings_cap']:,} net relevant earnings). "
            "AVC contributions also qualify."
        ),
        "source_url": "https://www.revenue.ie/en/jobs-and-pensions/pension/tax-relief-for-pension-contributions/index.aspx",
    })

    # ── Home carer credit ────────────────────────────────────────────────
    if ctx.married:
        claims.append({
            "id": "ie_home_carer",
            "title": "Home Carer Tax Credit",
            "status": "needs_input",
            "amount_estimate": rules.get("home_carer_credit", 1950),
            "confidence": 0.4,
            "notes": (
                f"€{rules.get('home_carer_credit', 1950)} credit for married "
                "couples where one spouse cares for a dependent person at home "
                "(child, elderly relative). Carer's income must be below threshold."
            ),
            "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/children-and-dependants/home-carer-tax-credit/index.aspx",
        })

    # ── Single Person Child Carer Credit ─────────────────────────────────
    if not ctx.married:
        claims.append({
            "id": "ie_single_parent",
            "title": "Single Person Child Carer Credit (SPCCC)",
            "status": "needs_input",
            "amount_estimate": rules.get("single_person_child_carer_credit", 1900),
            "confidence": 0.3,
            "notes": (
                f"€{rules.get('single_person_child_carer_credit', 1900)} credit "
                "plus extended standard rate band for single/widowed parents "
                "with a qualifying child. Primary claimant only."
            ),
            "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/children-and-dependants/single-person-child-carer-credit/index.aspx",
        })

    # ── Mortgage interest relief (FTB 2004-2012) ─────────────────────────
    claims.append({
        "id": "ie_mortgage_interest",
        "title": "Mortgage Interest Tax Credit",
        "status": "needs_input",
        "amount_estimate": rules.get("mortgage_interest_credit_max", 1250),
        "confidence": 0.3,
        "notes": (
            "Temporary credit for owner-occupiers who had a mortgage between "
            "2004-2012 and are still paying increased interest. "
            f"Max €{rules.get('mortgage_interest_credit_max', 1250)}/year. "
            "Check eligibility via myAccount."
        ),
        "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/land-and-property/mortgage-interest-relief/index.aspx",
    })

    # ── Tuition fees ─────────────────────────────────────────────────────
    claims.append({
        "id": "ie_tuition_fees",
        "title": "Tuition Fees Relief",
        "status": "needs_input",
        "amount_estimate": None,
        "confidence": 0.3,
        "notes": (
            "Tax relief at 20% on qualifying tuition fees for approved "
            "third-level courses. First €3,000 per student disregarded "
            "(€1,500 for part-time). Max claim €7,000/year."
        ),
        "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/education/tuition-fees-paid-for-third-level-education/index.aspx",
    })

    # ── Employment Investment Incentive (EII) ────────────────────────────
    claims.append({
        "id": "ie_eii",
        "title": "Employment Investment Incentive (EII)",
        "status": "needs_input",
        "amount_estimate": None,
        "confidence": 0.2,
        "notes": (
            "Income tax relief at 40% on investments in qualifying companies "
            "(max €250,000/year). High-risk investment. Shares must be held "
            "for minimum 4 years."
        ),
        "source_url": "https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/investment/employment-investment-incentive-scheme/index.aspx",
    })

    return claims
