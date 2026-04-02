"""
German locale plugin for Finance Assistant.

Bundles tax rules, social contributions, filing deadlines, insurance thresholds,
and deduction discovery for 2024-2026.
"""

from __future__ import annotations

# Import from co-located locale modules
from .tax_rules import (
    TAX_YEAR_RULES,
    calculate_income_tax,
    calculate_soli,
    get_tax_year_rules,
    resolve_supported_year,
    calculate_equipment_deduction,
    coerce_receipt_deductible_amount,
    equipment_useful_life,
)
from .tax_calculator import calculate_refund, format_refund_display
from .tax_dates import get_filing_deadline, format_deadline_label

try:
    from ..context import LocaleContext
except ImportError:
    # Standalone usage: locales/ root is on sys.path, so `de` is a top-level package
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "de"
LOCALE_NAME = "Germany"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "EUR"


def get_tax_rules(year: int) -> dict:
    return get_tax_year_rules(year)


def calculate_tax(ctx: "LocaleContext | dict", year: int = None) -> dict:
    if isinstance(ctx, dict):
        if year:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)
    return calculate_refund(ctx)


def get_filing_deadlines(year: int) -> list[dict]:
    return [
        {
            "type": "standard",
            "deadline": get_filing_deadline(year, advised=False).isoformat(),
            "label": format_deadline_label(year, advised=False),
        },
        {
            "type": "with_adviser",
            "deadline": get_filing_deadline(year, advised=True).isoformat(),
            "label": format_deadline_label(year, advised=True),
        },
    ]


def get_social_contributions(gross: float, year: int) -> dict:
    from .social_contributions import estimate_employee_social_contributions
    return estimate_employee_social_contributions(gross, year)


def get_deduction_categories() -> list[dict]:
    return [
        {"id": "homeoffice", "name": "Homeoffice-Pauschale", "basis": "§4 Abs. 5 Nr. 6b EStG"},
        {"id": "commute", "name": "Pendlerpauschale", "basis": "§9 Abs. 1 Nr. 4 EStG"},
        {"id": "equipment", "name": "Arbeitsmittel", "basis": "§9 Abs. 1 Nr. 6 EStG"},
        {"id": "education", "name": "Fortbildungskosten", "basis": "§9 Abs. 1 Nr. 6 EStG"},
        {"id": "donation", "name": "Spenden", "basis": "§10b EStG"},
        {"id": "childcare", "name": "Kinderbetreuungskosten", "basis": "§10 Abs. 1 Nr. 5 EStG"},
        {"id": "riester", "name": "Riester", "basis": "§10a EStG"},
        {"id": "ruerup", "name": "Rürup / Basisrente", "basis": "§10 Abs. 1 Nr. 2b EStG"},
        {"id": "bav", "name": "bAV", "basis": "§3 Nr. 63 EStG"},
        {"id": "union_dues", "name": "Gewerkschaftsbeiträge", "basis": "§9 Abs. 1 Nr. 3d EStG"},
        {"id": "disability", "name": "Behinderten-Pauschbetrag", "basis": "§33b EStG"},
    ]


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    from .claim_rules import generate_german_claims
    return generate_german_claims(ctx, year)
