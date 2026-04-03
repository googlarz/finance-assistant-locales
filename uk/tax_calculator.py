"""
UK income tax calculator.

Calculates income tax, National Insurance, and net pay for employed
and self-employed individuals in the UK for 2024-2026.

Tax year convention: year=2024 → 2024/25 (6 Apr 2024 – 5 Apr 2025).

Sources:
  https://www.gov.uk/income-tax-rates
  https://www.gov.uk/national-insurance-rates-letters
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    resolve_supported_year,
    calculate_income_tax,
    calculate_marginal_rate,
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
    Calculate UK income tax and National Insurance for a given profile.

    Args:
        ctx: LocaleContext or Finance Assistant profile dict.
        year: Override tax year (uses ctx.tax_year if not provided).

    Returns:
        Dict with gross, tax, ni_employee, net, effective_rate,
        marginal_rate, confidence, and a breakdown sub-dict.
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

    # ── Income tax ────────────────────────────────────────────────────────
    income_tax = calculate_income_tax(gross, rules)
    marginal = calculate_marginal_rate(gross, rules)

    # ── National Insurance ────────────────────────────────────────────────
    ni_data = get_social_contributions(gross, resolved_year, self_employed=is_self_employed)
    ni_employee = ni_data["ni_employee"]

    # ── Net pay ───────────────────────────────────────────────────────────
    net = gross - income_tax - ni_employee

    # ── Effective rate ────────────────────────────────────────────────────
    effective_rate = round(income_tax / gross, 4) if gross > 0 else 0.0

    # ── Confidence ───────────────────────────────────────────────────────
    if year_note:
        confidence = "Likely"
    elif is_self_employed:
        confidence = "Likely"  # simplified — does not account for allowable expenses
    elif resolved_year == 2026:
        confidence = rules.get("confidence", "Likely")
    else:
        confidence = "Definitive"

    return {
        "gross": round(gross, 2),
        "tax": round(income_tax, 2),
        "ni_employee": round(ni_employee, 2),
        "net": round(net, 2),
        "effective_rate": effective_rate,
        "marginal_rate": marginal,
        "confidence": confidence,
        "currency": rules["currency"],
        "tax_year": resolved_year,
        "year_note": year_note,
        "breakdown": {
            "gross": round(gross, 2),
            "personal_allowance_used": round(
                _get_effective_allowance(gross, rules), 2
            ),
            "taxable_income": round(max(0.0, gross - _get_effective_allowance(gross, rules)), 2),
            "basic_rate_tax": round(_basic_rate_tax(gross, rules), 2),
            "higher_rate_tax": round(_higher_rate_tax(gross, rules), 2),
            "additional_rate_tax": round(_additional_rate_tax(gross, rules), 2),
            "total_income_tax": round(income_tax, 2),
            "ni_employee": round(ni_employee, 2),
            "ni_employer": round(ni_data["ni_employer"], 2),
            "total_deductions": round(income_tax + ni_employee, 2),
            "net": round(net, 2),
        },
        "ni_detail": ni_data,
        "is_self_employed": is_self_employed,
    }


# ── Band helpers (for breakdown) ──────────────────────────────────────────────

def _get_effective_allowance(gross: float, rules: dict) -> float:
    from .tax_rules import calculate_personal_allowance
    return calculate_personal_allowance(gross, rules)


def _basic_rate_tax(gross: float, rules: dict) -> float:
    allowance = _get_effective_allowance(gross, rules)
    basic_ceiling = rules["basic_rate_limit"]
    basic_income = max(0.0, min(gross, basic_ceiling) - allowance)
    return basic_income * rules["basic_rate"]


def _higher_rate_tax(gross: float, rules: dict) -> float:
    basic_ceiling = rules["basic_rate_limit"]
    higher_ceiling = rules["higher_rate_limit"]
    if gross <= basic_ceiling:
        return 0.0
    higher_income = max(0.0, min(gross, higher_ceiling) - basic_ceiling)
    return higher_income * rules["higher_rate"]


def _additional_rate_tax(gross: float, rules: dict) -> float:
    higher_ceiling = rules["higher_rate_limit"]
    if gross <= higher_ceiling:
        return 0.0
    return (gross - higher_ceiling) * rules["additional_rate"]
