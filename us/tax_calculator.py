"""
US federal income tax calculator.

Computes estimated federal tax liability / refund for W-2 and self-employed filers.
Does NOT cover state taxes — that's a separate locale concern.

TODO: itemized deductions (currently always uses standard), AMT, QBI deduction (§199A)
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules


def _apply_brackets(taxable: float, brackets: list[tuple]) -> float:
    tax = 0.0
    for rate, low, high in brackets:
        if taxable <= low:
            break
        ceiling = high if high is not None else taxable
        tax += rate * (min(taxable, ceiling) - low)
    return tax


def calculate_liability(ctx) -> dict:
    """
    Calculate federal income tax liability and estimated refund.

    ctx: LocaleContext or dict with keys:
      - employment.annual_gross (float)
      - tax_profile.filing_status: "single" | "married_filing_jointly" | "head_of_household"
      - tax_profile.tax_year (int, defaults to current year)
      - tax_profile.extra.withheld (float, optional — tax already withheld)
      - tax_profile.extra.pretax_401k (float, optional)
      - tax_profile.extra.pretax_hsa (float, optional)
      - tax_profile.extra.other_pretax (float, optional)
    """
    from datetime import date

    # Resolve inputs from ctx
    if hasattr(ctx, "gross_income"):
        gross = float(ctx.gross_income or 0)
        filing_status = getattr(ctx, "filing_status", "single") or "single"
        year = getattr(ctx, "tax_year", None) or date.today().year
        extra = getattr(ctx, "extra", {}) or {}
    else:
        emp = ctx.get("employment", {}) or {}
        tp = ctx.get("tax_profile", {}) or {}
        gross = float(emp.get("annual_gross", 0) or 0)
        filing_status = tp.get("filing_status", "single") or "single"
        year = tp.get("tax_year") or date.today().year
        extra = tp.get("extra", {}) or {}

    rules = get_tax_year_rules(year)

    # Pre-tax deductions
    pretax_401k = float(extra.get("pretax_401k", 0) or 0)
    pretax_hsa = float(extra.get("pretax_hsa", 0) or 0)
    other_pretax = float(extra.get("other_pretax", 0) or 0)
    agi = gross - pretax_401k - pretax_hsa - other_pretax

    # Standard deduction (itemized not yet implemented)
    std_deduction = rules["standard_deduction"].get(filing_status, rules["standard_deduction"]["single"])
    taxable_income = max(0.0, agi - std_deduction)

    # Federal income tax
    bracket_key = filing_status if filing_status in rules["brackets"] else "single"
    federal_tax = _apply_brackets(taxable_income, rules["brackets"][bracket_key])

    # FICA (W-2 employee share)
    fica = rules["fica"]
    ss_tax = min(gross, fica["social_security_wage_base"]) * fica["social_security_rate"]
    medicare_tax = gross * fica["medicare_rate"]
    add_medicare_threshold = fica.get("additional_medicare_threshold_single", 200_000)
    if gross > add_medicare_threshold:
        medicare_tax += (gross - add_medicare_threshold) * fica["additional_medicare_rate"]

    total_tax = federal_tax + ss_tax + medicare_tax
    withheld = float(extra.get("withheld", 0) or 0)
    refund = withheld - federal_tax  # FICA is already withheld separately

    effective_rate = (federal_tax / gross) if gross > 0 else 0.0

    return {
        "year": year,
        "gross_income": gross,
        "agi": round(agi, 2),
        "standard_deduction": std_deduction,
        "taxable_income": round(taxable_income, 2),
        "federal_income_tax": round(federal_tax, 2),
        "social_security_tax": round(ss_tax, 2),
        "medicare_tax": round(medicare_tax, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 4),
        "withheld": withheld,
        "estimated_refund": round(refund, 2) if withheld else None,
        "filing_status": filing_status,
        "currency": "USD",
        "note": "Federal only. State taxes not included. Itemized deductions not yet supported.",
    }
