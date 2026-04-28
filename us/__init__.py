"""
US locale plugin for Finance Assistant.

Federal income tax, FICA/Medicare, filing deadlines, and common deductions
for W-2 employees and self-employed filers.

Status: stub — contributions welcome!
See CONTRIBUTING.md for how to fill this out.
"""

from __future__ import annotations

try:
    from ..context import LocaleContext
except ImportError:
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "us"
LOCALE_NAME = "United States"
SUPPORTED_YEARS = [2024, 2025]
CURRENCY = "USD"


def get_tax_rules(year: int) -> dict:
    from .tax_rules import get_tax_year_rules
    return get_tax_year_rules(year)


def calculate_tax(ctx: "LocaleContext | dict", year: int = None) -> dict:
    from .tax_calculator import calculate_liability
    if isinstance(ctx, dict):
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    return calculate_liability(ctx)


def get_filing_deadlines(year: int) -> list[dict]:
    from .tax_dates import get_filing_deadline, get_extension_deadline
    return [
        {
            "type": "standard",
            "deadline": get_filing_deadline(year).isoformat(),
            "label": f"File by April 15, {year + 1} (standard)",
        },
        {
            "type": "extension",
            "deadline": get_extension_deadline(year).isoformat(),
            "label": f"Extension deadline: October 15, {year + 1}",
        },
    ]


def get_social_contributions(gross: float, year: int) -> dict:
    from .social_contributions import estimate_fica
    return estimate_fica(gross, year)


def get_deduction_categories() -> list[dict]:
    return [
        {"id": "401k", "name": "401(k) contributions", "basis": "IRC §401(k)"},
        {"id": "ira", "name": "Traditional IRA", "basis": "IRC §219"},
        {"id": "hsa", "name": "HSA contributions", "basis": "IRC §223"},
        {"id": "mortgage_interest", "name": "Mortgage interest", "basis": "IRC §163(h)"},
        {"id": "salt", "name": "State & local taxes (SALT, capped $10k)", "basis": "IRC §164"},
        {"id": "charitable", "name": "Charitable donations", "basis": "IRC §170"},
        {"id": "student_loan_interest", "name": "Student loan interest", "basis": "IRC §221"},
        {"id": "home_office", "name": "Home office (self-employed)", "basis": "IRC §280A"},
        {"id": "self_employment_tax", "name": "½ self-employment tax deduction", "basis": "IRC §164(f)"},
        {"id": "health_insurance_se", "name": "Self-employed health insurance", "basis": "IRC §162(l)"},
    ]


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    from .claim_rules import generate_us_claims
    return generate_us_claims(ctx, year)
