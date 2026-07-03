"""
Irish income tax calculator.

Calculates income tax, USC, PRSI, and net pay for employed
and self-employed individuals in Ireland for 2024-2026.

Ireland uses a tax credit system:
  1. Calculate gross tax at 20%/40% bands
  2. Subtract tax credits (personal + PAYE/earned income)
  3. Add USC (separate charge on gross income)
  4. Add PRSI (separate social insurance)

Sources:
  https://www.revenue.ie/en/jobs-and-pensions/calculating-your-income-tax/index.aspx
  https://www.revenue.ie/en/jobs-and-pensions/usc/standard-rates-thresholds.aspx
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    resolve_supported_year,
    calculate_income_tax,
    calculate_usc,
    get_total_credits,
)
from .social_contributions import get_social_contributions

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
    Calculate Irish income tax, USC, and PRSI for a given profile.

    Args:
        ctx: LocaleContext or Finance Assistant profile dict.
        year: Override tax year (uses ctx.tax_year if not provided).

    Returns:
        Dict with gross, income_tax, usc, prsi_employee, total_tax,
        net, effective_rate, marginal_rate, confidence, and breakdown.
    """
    if isinstance(ctx, dict):
        LocaleContext = _import_locale_context()
        if year is not None:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    requested_year = ctx.tax_year
    resolved_year, year_note = resolve_supported_year(requested_year)
    rules = get_tax_year_rules(resolved_year)

    gross = float(ctx.annual_gross or 0.0)
    is_self_employed = ctx.employment_type in ("self_employed", "freelancer")
    married = ctx.married

    # ── Income tax (credit system) ───────────────────────────────────────
    gross_tax = calculate_income_tax(gross, rules, married=married)
    credits = get_total_credits(rules, is_employee=(not is_self_employed), married=married)
    income_tax = max(0.0, gross_tax - credits)

    # ── USC ──────────────────────────────────────────────────────────────
    usc = calculate_usc(gross, rules)

    # ── PRSI ─────────────────────────────────────────────────────────────
    prsi_data = get_social_contributions(gross, resolved_year, self_employed=is_self_employed)
    prsi_employee = prsi_data["prsi_employee"]

    # ── Total tax burden ─────────────────────────────────────────────────
    total_tax = round(income_tax + usc + prsi_employee, 2)
    net = round(gross - total_tax, 2)

    # ── Effective and marginal rates ─────────────────────────────────────
    effective_rate = round(total_tax / gross, 4) if gross > 0 else 0.0
    marginal = _calculate_marginal_rate(gross, rules, married=married,
                                        is_employee=(not is_self_employed))

    # ── Confidence ───────────────────────────────────────────────────────
    if year_note:
        confidence = "Likely"
    elif is_self_employed:
        confidence = "Likely"
    else:
        confidence = rules.get("confidence", "Definitive")

    return {
        "gross": round(gross, 2),
        "income_tax": round(income_tax, 2),
        "tax": round(income_tax, 2),  # alias for cross-locale compatibility
        "usc": round(usc, 2),
        "prsi_employee": round(prsi_employee, 2),
        "total_tax": total_tax,
        "total_burden": total_tax,
        "net": net,
        "effective_rate": effective_rate,
        "marginal_rate": marginal,
        "confidence": confidence,
        "currency": rules["currency"],
        "tax_year": resolved_year,
        "year_note": year_note,
        "breakdown": {
            "gross": round(gross, 2),
            "gross_income_tax": round(gross_tax, 2),
            "tax_credits": round(credits, 2),
            "income_tax_after_credits": round(income_tax, 2),
            "usc": round(usc, 2),
            "prsi_employee": round(prsi_employee, 2),
            "prsi_employer": round(prsi_data["prsi_employer"], 2),
            "total_deductions": total_tax,
            "net": net,
        },
        "prsi_detail": prsi_data,
        "is_self_employed": is_self_employed,
    }


def _calculate_marginal_rate(gross: float, rules: dict, married: bool = False,
                             is_employee: bool = True) -> float:
    """
    Return the combined marginal rate (income tax + USC + PRSI) for a given gross.

    Irish marginal rates:
      - Below credits: 0% income tax (but USC + PRSI still apply on gross)
      - Standard band: 20% + USC rate + PRSI rate
      - Higher band: 40% + USC rate + PRSI rate
    """
    band = rules["standard_rate_band_single"]
    if married:
        band = rules["standard_rate_band_married_one_income"]

    # Income tax marginal rate
    if gross <= 0:
        return 0.0

    # Determine if income tax credits are exhausted
    credits = get_total_credits(rules, is_employee=is_employee, married=married)
    gross_tax_at_gross = calculate_income_tax(gross, rules, married=married)
    if gross_tax_at_gross <= credits:
        it_marginal = 0.0
    elif gross <= band:
        it_marginal = rules["standard_rate"]
    else:
        it_marginal = rules["higher_rate"]

    # USC marginal rate at this income level
    usc_marginal = 0.0
    if gross > rules["usc_exempt_threshold"]:
        for upper, rate in rules["usc_bands"]:
            if upper is None or gross <= upper:
                usc_marginal = rate
                break

    # PRSI marginal rate (flat 4% / 4.2% above threshold)
    weekly_gross = gross / 52
    if weekly_gross > rules["prsi_employee_threshold"]:
        prsi_marginal = rules["prsi_employee_rate"]
    else:
        prsi_marginal = 0.0

    return round(it_marginal + usc_marginal + prsi_marginal, 4)
