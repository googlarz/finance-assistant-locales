"""
French deduction and tax credit claim discovery.

Generates a list of applicable claims for a given profile, following the
standard locale claim interface (id, title, status, amount_estimate, confidence).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import get_tax_year_rules, calculate_parts

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def generate_french_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable French deduction and tax credit claims."""
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
    children_count = len(ctx.children)
    is_auto_entrepreneur = (
        employment_type in ("freelancer", "self_employed")
        and ctx.extra.get("auto_entrepreneur", False)
    )

    claims: list[dict] = []

    # ── 1. Abattement forfaitaire 10% ─────────────────────────────────────
    if not is_auto_entrepreneur:
        raw_aba = gross * rules["abattement_pct"]
        aba = max(rules["abattement_min"], min(raw_aba, rules["abattement_max"]))
        claims.append({
            "id": "abattement_forfaitaire_10pct",
            "title": "Abattement forfaitaire 10% (frais professionnels)",
            "status": "ready",
            "amount_estimate": round(aba, 2),
            "confidence": "Definitive",
            "notes": (
                "Applied automatically for salaried workers. "
                "Capped at €{max} / floor €{min}.".format(
                    max=rules["abattement_max"], min=rules["abattement_min"]
                )
            ),
        })

    # ── 2. Frais réels ────────────────────────────────────────────────────
    # If actual professional expenses likely exceed the 10% flat amount
    actual_expenses = sum(
        r.amount for r in ctx.receipts
        if r.category in ("equipment", "fortbildung", "transport", "frais_reels")
    )
    raw_aba_est = gross * rules["abattement_pct"]
    if actual_expenses > raw_aba_est and actual_expenses > 0:
        claims.append({
            "id": "frais_reels",
            "title": "Déduction des frais réels",
            "status": "needs_evidence",
            "amount_estimate": round(actual_expenses, 2),
            "confidence": "Likely",
            "notes": (
                "Actual professional expenses appear to exceed the 10% flat rate. "
                "Submit detailed receipts in lieu of the abattement forfaitaire."
            ),
        })
    elif employment_type == "employed":
        claims.append({
            "id": "frais_reels",
            "title": "Déduction des frais réels (option)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "If your actual professional expenses exceed the 10% abattement, "
                "you may elect to deduct them instead. Receipts required."
            ),
        })

    # ── 3. Pension alimentaire ─────────────────────────────────────────────
    pension_amount = ctx.extra.get("pension_alimentaire", None)
    if pension_amount is not None:
        claims.append({
            "id": "pension_alimentaire",
            "title": "Pension alimentaire versée",
            "status": "ready",
            "amount_estimate": float(pension_amount),
            "confidence": "Definitive",
            "notes": "Maintenance payments to a former spouse or dependent child are fully deductible.",
        })
    elif not married and children_count > 0:
        claims.append({
            "id": "pension_alimentaire",
            "title": "Pension alimentaire versée",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "If you pay maintenance to a separated/divorced co-parent, "
                "the amount is deductible. Please provide the annual amount."
            ),
        })

    # ── 4. Dons aux associations ──────────────────────────────────────────
    donation_amount = sum(r.amount for r in ctx.receipts if r.category == "donation")
    if donation_amount > 0:
        # 66% credit, max 20% of net income
        credit_66 = donation_amount * 0.66
        claims.append({
            "id": "dons_associations_66pct",
            "title": "Dons aux associations (crédit 66%)",
            "status": "needs_evidence",
            "amount_estimate": round(credit_66, 2),
            "confidence": "Definitive",
            "notes": (
                "Tax credit of 66% on donations to eligible associations, "
                "capped at 20% of net income. Receipts (reçus fiscaux) required."
            ),
        })
    else:
        claims.append({
            "id": "dons_associations_66pct",
            "title": "Dons aux associations (crédit 66%)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "Donations to eligible associations qualify for a 66% tax credit "
                "(75% for Restos du Cœur etc.), capped at 20% of net income."
            ),
        })

    # ── 5. Emploi à domicile ──────────────────────────────────────────────
    home_help = ctx.extra.get("emploi_domicile_cost", None)
    if home_help is not None:
        eligible = min(float(home_help), 12_000)
        credit = eligible * 0.50
        claims.append({
            "id": "emploi_domicile",
            "title": "Emploi à domicile (crédit d'impôt 50%)",
            "status": "ready",
            "amount_estimate": round(credit, 2),
            "confidence": "Definitive",
            "notes": (
                "50% tax credit on home help costs (cleaning, childcare, gardening), "
                "up to €12,000 base per year (€6,000 credit maximum)."
            ),
        })
    else:
        claims.append({
            "id": "emploi_domicile",
            "title": "Emploi à domicile (crédit d'impôt 50%)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "If you employ household help (ménage, garde d'enfants, jardinage), "
                "a 50% tax credit applies on eligible costs up to €12,000."
            ),
        })

    # ── 6. Plan d'Épargne Retraite (PER) ──────────────────────────────────
    per_contribution = ctx.ruerup_contribution or ctx.extra.get("per_contribution", 0.0)
    per_max = min(gross * 0.10, rules["pass"] * 8)
    if per_contribution > 0:
        deductible = min(float(per_contribution), per_max)
        claims.append({
            "id": "per_plan_epargne_retraite",
            "title": "Plan d'Épargne Retraite (PER) — versements déductibles",
            "status": "ready",
            "amount_estimate": round(deductible, 2),
            "confidence": "Definitive",
            "notes": (
                "PER contributions deductible up to 10% of prior-year net professional income, "
                "capped at 8× PASS (€{cap:,.0f} for {yr}).".format(
                    cap=per_max, yr=resolved_year
                )
            ),
        })
    else:
        claims.append({
            "id": "per_plan_epargne_retraite",
            "title": "Plan d'Épargne Retraite (PER)",
            "status": "needs_input",
            "amount_estimate": 0.0,
            "confidence": "Likely",
            "notes": (
                "PER contributions are fully deductible from taxable income "
                "(up to 10% of income, capped at 8× PASS). "
                "Please provide your annual PER contribution amount."
            ),
        })

    # ── 7. Micro-entrepreneur threshold alert ─────────────────────────────
    if is_auto_entrepreneur:
        ae_type = ctx.extra.get("ae_type", "services")
        ca_threshold = 77_700 if ae_type == "services" else 188_700  # 2024 CA limits
        claims.append({
            "id": "micro_entrepreneur_abattement",
            "title": "Abattement micro-entrepreneur",
            "status": "ready",
            "amount_estimate": round(
                gross * (rules["micro_bic_abattement"] if ae_type == "commerce"
                         else rules["micro_bnc_abattement"]),
                2,
            ),
            "confidence": "Definitive",
            "notes": (
                "Micro-BIC (commerce) abattement 50%, or micro-BNC (services) 34%, "
                "already applied to arrive at taxable income."
            ),
        })
        if gross > ca_threshold * 0.85:
            claims.append({
                "id": "micro_entrepreneur_seuil",
                "title": "Alerte seuil chiffre d'affaires micro-entrepreneur",
                "status": "detected",
                "amount_estimate": 0.0,
                "confidence": "Likely",
                "notes": (
                    "Your CA is approaching the micro-entrepreneur ceiling "
                    "(€{threshold:,.0f} for {type}). "
                    "Exceeding it triggers a switch to régime réel.".format(
                        threshold=ca_threshold, type=ae_type
                    )
                ),
            })

    # ── 8. Quotient familial benefit note ─────────────────────────────────
    if children_count > 0:
        parts = calculate_parts(married, children_count)
        claims.append({
            "id": "quotient_familial",
            "title": "Quotient familial (réduction liée aux enfants)",
            "status": "ready",
            "amount_estimate": 0.0,  # Already embedded in tax calc
            "confidence": "Definitive",
            "notes": (
                "{parts} parts used for tax calculation ({children} child(ren)). "
                "Benefit is capped at €{cap} per half-part.".format(
                    parts=parts,
                    children=children_count,
                    cap=rules["plafond_demi_part"],
                )
            ),
        })

    return claims
