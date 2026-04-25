"""
French income tax calculator.

Steps:
  1. Compute gross income (salaried employment_type uses annual_gross;
     auto-entrepreneur applies micro abattement first).
  2. Apply abattement forfaitaire 10% (cap abattement_max, floor abattement_min)
     to arrive at net taxable income.
  3. Determine parts (quotient familial) from marital status + children count.
  4. Calculate raw IR via bracket schedule on (net / parts) × parts.
  5. Apply plafonnement du quotient familial.
  6. Apply décote for low earners.
  7. Compute prélèvements sociaux (CSG + CRDS = 9.7% on gross) — separate levy.
  8. Return full breakdown.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    resolve_supported_year,
    calculate_parts,
    calculate_income_tax,
    apply_decote,
    calculate_marginal_rate,
)

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def calculate_tax(ctx: "LocaleContext | dict", year: int = None) -> dict:
    """
    Calculate French income tax and prélèvements sociaux.

    Returns:
        gross                  — gross income used as base
        abattement             — 10% frais professionnels deduction
        net_income             — gross − abattement (IR base)
        parts                  — number of family quotient parts
        income_tax             — impôt sur le revenu after décote
        prelevements_sociaux   — CSG + CRDS (9.7%) on gross
        net                    — gross − income_tax − prelevements_sociaux
        effective_rate         — income_tax / gross
        marginal_rate          — bracket rate on last euro of net income
        confidence             — Definitive / Likely
        breakdown              — detailed sub-amounts
    """
    LocaleContext = _import_locale_context()

    if isinstance(ctx, dict):
        if year:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    requested_year = ctx.tax_year
    resolved_year, year_note = resolve_supported_year(requested_year)
    rules = get_tax_year_rules(resolved_year)

    gross = ctx.annual_gross + ctx.side_income
    employment_type = ctx.employment_type
    children_count = len(ctx.children)
    married = ctx.married

    # ── Micro-entrepreneur abattement (replaces standard 10%) ─────────────
    is_auto_entrepreneur = (employment_type in ("freelancer", "self_employed")
                            and ctx.extra.get("auto_entrepreneur", False))

    if is_auto_entrepreneur:
        ae_type = ctx.extra.get("ae_type", "services")
        if ae_type == "commerce":
            ae_abattement = gross * rules["micro_bic_abattement"]
        else:
            ae_abattement = gross * rules["micro_bnc_abattement"]
        net_income = max(0.0, gross - ae_abattement)
        abattement_applied = ae_abattement
        confidence = "Likely"
    else:
        # Standard 10% abattement for salaried
        raw_abattement = gross * rules["abattement_pct"]
        abattement_applied = max(
            rules["abattement_min"],
            min(raw_abattement, rules["abattement_max"]),
        )
        net_income = max(0.0, gross - abattement_applied)
        confidence = "Definitive"

    if year_note:
        confidence = "Likely"

    # ── Quotient familial ─────────────────────────────────────────────────
    parts = calculate_parts(married, children_count)

    # ── Raw income tax (after plafonnement) ───────────────────────────────
    raw_ir = calculate_income_tax(net_income, parts, resolved_year)

    # ── Décote ────────────────────────────────────────────────────────────
    income_tax = apply_decote(raw_ir, married, resolved_year)
    income_tax = round(income_tax, 2)

    # ── Prélèvements sociaux ──────────────────────────────────────────────
    # CSG (9.2%) + CRDS (0.5%) = 9.7%.
    # For salaried employees, the legal base is gross × 0.9825 — the 1.75%
    # professional abatement (assiette réduite) per Art. L136-2 CSS.
    # TNS / auto-entrepreneurs have no abatement; full gross is the base.
    # Note: the CSG déductible portion (6.8%) normally reduces the IR base
    # for the following year; we note it in breakdown but do not apply it
    # here (it would require prior-year gross, which we do not have).
    if employment_type in ("employed", "salaried", None):
        csg_base = gross * 0.9825  # assiette réduite — Art. L136-2 CSS
    else:
        csg_base = gross  # TNS / auto-entrepreneur: no abatement
    prelevements_sociaux = round(csg_base * (rules["csg_rate"] + rules["crds_rate"]), 2)

    net = round(gross - income_tax - prelevements_sociaux, 2)
    effective_rate = round(income_tax / gross, 4) if gross > 0 else 0.0
    marginal_rate = calculate_marginal_rate(net_income, rules["brackets"])

    return {
        "gross": gross,
        "abattement": round(abattement_applied, 2),
        "net_income": round(net_income, 2),
        "parts": parts,
        "income_tax": income_tax,
        "prelevements_sociaux": prelevements_sociaux,
        "net": net,
        "effective_rate": effective_rate,
        "marginal_rate": marginal_rate,
        "confidence": confidence,
        "breakdown": {
            "gross": gross,
            "abattement": round(abattement_applied, 2),
            "net_income": round(net_income, 2),
            "parts": parts,
            "children_count": children_count,
            "married": married,
            "raw_ir_before_decote": round(raw_ir, 2),
            "income_tax_after_decote": income_tax,
            "csg": round(csg_base * rules["csg_rate"], 2),
            "crds": round(csg_base * rules["crds_rate"], 2),
            "prelevements_sociaux": prelevements_sociaux,
            "net": net,
        },
    }
