"""
Dutch deduction and tax credit claim discovery.

Generates a list of applicable claims for a given profile, following the
standard locale claim interface (id, title, status, amount_estimate, confidence).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    calculate_heffingskorting,
    calculate_arbeidskorting,
)

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def generate_dutch_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable Dutch deduction and tax credit claims."""
    LocaleContext = _import_locale_context()

    if isinstance(ctx, dict):
        if year:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    resolved_year = ctx.tax_year
    rules = get_tax_year_rules(resolved_year)
    gross = ctx.annual_gross + ctx.side_income
    employment_type = ctx.employment_type
    married = ctx.married
    partner = married

    claims: list[dict] = []

    # ── 1. Algemene heffingskorting ────────────────────────────────────────
    hk = calculate_heffingskorting(gross, rules)
    claims.append({
        "id": "heffingskorting",
        "title": "Algemene heffingskorting",
        "status": "ready",
        "amount_estimate": round(hk, 2),
        "confidence": "Definitive",
        "notes": (
            "General tax credit applied automatically. "
            "Phases out above €{start:,}.".format(start=rules["heffingskorting_taper_start"])
        ),
    })

    # ── 2. Arbeidskorting ──────────────────────────────────────────────────
    if employment_type == "employed":
        ak = calculate_arbeidskorting(gross, rules)
        claims.append({
            "id": "arbeidskorting",
            "title": "Arbeidskorting (employment tax credit)",
            "status": "ready",
            "amount_estimate": round(ak, 2),
            "confidence": "Definitive",
            "notes": (
                "Employment credit applied automatically to salaried income. "
                "Maximum €{max:,}; phases out above €{taper:,}.".format(
                    max=rules["arbeidskorting_max"],
                    taper=rules["arbeidskorting_taper_start"],
                )
            ),
        })
    elif employment_type in ("freelancer", "self_employed"):
        claims.append({
            "id": "arbeidskorting",
            "title": "Arbeidskorting (employment tax credit)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "Arbeidskorting applies to winst uit onderneming (business profit) as well. "
                "Please confirm income type to determine eligibility."
            ),
        })

    # ── 3. Hypotheekrenteaftrek (mortgage interest deduction) ─────────────
    mortgage_interest = ctx.extra.get("mortgage_interest_annual", None)
    has_mortgage = ctx.extra.get("has_mortgage", False)
    if mortgage_interest is not None and float(mortgage_interest) > 0:
        claims.append({
            "id": "hypotheekrenteaftrek",
            "title": "Hypotheekrenteaftrek (mortgage interest deduction)",
            "status": "ready",
            "amount_estimate": float(mortgage_interest),
            "confidence": "Definitive",
            "notes": (
                "Mortgage interest on your primary residence is deductible in Box 1. "
                "Deduction rate limited to first bracket rate (eigenwoningforfait applies)."
            ),
        })
    elif has_mortgage or ctx.commute_km > 0:
        claims.append({
            "id": "hypotheekrenteaftrek",
            "title": "Hypotheekrenteaftrek (mortgage interest deduction)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Definitive",
            "notes": (
                "If you have a mortgage on your primary residence (eigenwoningschuld), "
                "the interest paid is deductible in Box 1. Provide annual interest amount."
            ),
        })

    # ── 4. Alimentatie (maintenance payments) ─────────────────────────────
    alimentatie = ctx.extra.get("alimentatie_annual", None)
    if alimentatie is not None and float(alimentatie) > 0:
        claims.append({
            "id": "alimentatie",
            "title": "Alimentatie (partneralimentatie)",
            "status": "ready",
            "amount_estimate": float(alimentatie),
            "confidence": "Definitive",
            "notes": "Partner maintenance (partneralimentatie) is deductible in Box 1.",
        })
    elif not married and len(ctx.children) > 0:
        claims.append({
            "id": "alimentatie",
            "title": "Alimentatie (partneralimentatie)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "If you pay maintenance to a former partner, it may be deductible. "
                "Note: kinderalimentatie (child maintenance) is not deductible."
            ),
        })

    # ── 5. Zorgkosten (specific medical costs) ────────────────────────────
    medical_expenses = ctx.extra.get("zorgkosten_annual", None)
    if medical_expenses is not None and float(medical_expenses) > 0:
        # Threshold: roughly 1.65% of income or €150, whichever higher
        threshold_pct = gross * 0.0165
        excess = max(0.0, float(medical_expenses) - threshold_pct)
        claims.append({
            "id": "zorgkosten",
            "title": "Specifieke zorgkosten",
            "status": "needs_evidence",
            "amount_estimate": round(excess, 2),
            "confidence": "Likely",
            "notes": (
                "Qualifying medical expenses above the income-related threshold "
                "are deductible (e.g. wheelchair, hearing aid, transport). Receipts required."
            ),
        })

    # ── 6. Giftenaftrek (charitable donations) ────────────────────────────
    donations = sum(r.amount for r in ctx.receipts if r.category == "donation")
    gift_threshold = max(60.0, gross * 0.01)
    if donations > gift_threshold:
        deductible_gifts = min(donations, gross * 0.10)
        claims.append({
            "id": "giftenaftrek",
            "title": "Giftenaftrek",
            "status": "needs_evidence",
            "amount_estimate": round(deductible_gifts, 2),
            "confidence": "Definitive",
            "notes": (
                "Charitable donations above €60 or 1% of income are deductible, "
                "up to 10% of taxable income. Receipts required."
            ),
        })
    else:
        claims.append({
            "id": "giftenaftrek",
            "title": "Giftenaftrek",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Definitive",
            "notes": (
                "Donations to ANBI-registered charities above €60 or 1% of income "
                "qualify for deduction (up to 10% of taxable income)."
            ),
        })

    # ── 7. Lijfrentepremies / pensioenbijdragen ────────────────────────────
    pension_contribution = ctx.ruerup_contribution or ctx.extra.get("lijfrente_annual", 0.0)
    if pension_contribution and float(pension_contribution) > 0:
        claims.append({
            "id": "lijfrentepremies",
            "title": "Lijfrentepremies / pensioenbijdragen",
            "status": "ready",
            "amount_estimate": float(pension_contribution),
            "confidence": "Definitive",
            "notes": (
                "Annuity premiums or supplementary pension contributions are deductible "
                "within the jaarruimte (annual margin) based on prior-year income."
            ),
        })
    else:
        claims.append({
            "id": "lijfrentepremies",
            "title": "Lijfrentepremies / pensioenbijdragen",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "If your employer pension is below the fiscal maximum, you may top up "
                "via lijfrente. Deduction limited by jaarruimte calculation."
            ),
        })

    # ── 8. Box 3 vrijstelling alert ───────────────────────────────────────
    savings = float(ctx.extra.get("savings", 0.0) or 0.0)
    investments = float(ctx.extra.get("investments", 0.0) or 0.0)
    exemption = (
        rules["box3_exemption_partner"] if partner
        else rules["box3_exemption_single"]
    )
    total_assets = savings + investments
    if total_assets > 0:
        status = "detected" if total_assets > exemption else "ready"
        claims.append({
            "id": "box3_vrijstelling",
            "title": "Box 3 heffingvrij vermogen",
            "status": status,
            "amount_estimate": float(exemption),
            "confidence": rules["box3_confidence"],
            "notes": (
                "Box 3 exemption of €{ex:,} per person. Your total assets (€{assets:,.0f}) "
                "{over}. Note: Box 3 system is under legal challenge (Kerstarrest).".format(
                    ex=int(exemption),
                    assets=total_assets,
                    over="exceed the exemption" if total_assets > exemption
                         else "are within the exemption",
                )
            ),
        })

    # ── 9. 30%-regeling (expat ruling) ────────────────────────────────────
    if ctx.expat:
        has_ruling = ctx.extra.get("has_30_ruling", False)
        if has_ruling:
            claims.append({
                "id": "dertig_procent_regeling",
                "title": "30%-regeling (expat ruling)",
                "status": "detected",
                "amount_estimate": round(gross * 0.30, 2),
                "confidence": "Likely",
                "notes": (
                    "You appear to have the 30% ruling. Up to 30% of gross salary can be "
                    "paid tax-free as an extraterritorial cost reimbursement. "
                    "Confirm with your employer that the ruling is active."
                ),
            })
        else:
            claims.append({
                "id": "dertig_procent_regeling",
                "title": "30%-regeling (expat ruling) — possible opportunity",
                "status": "detected",
                "amount_estimate": 0.0,
                "confidence": "Likely",
                "notes": (
                    "As an expat, you may qualify for the 30%-regeling if you were recruited "
                    "from abroad within the last 5 years and meet the scarcity/salary criteria. "
                    "Applied for jointly with your employer."
                ),
            })

    return claims
