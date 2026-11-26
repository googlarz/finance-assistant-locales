"""
Canada locale plugin for Finance Assistant.

Bundles Canadian federal and provincial tax rules, Canada Pension Plan (CPP) /
Quebec Pension Plan (QPP), Employment Insurance (EI), filing deadlines,
and deduction discovery for Canadian tax years 2024, 2025, and 2026.

Supports all 10 provinces and 3 territories (AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT).
Tax year convention: Canada uses the calendar year (1 Jan - 31 Dec).

Sources:
  Canada Revenue Agency (CRA)
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/canadian-income-tax-rates-individuals-current-previous-years.html
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/adjustment-personal-income-tax-benefit-amounts.html
"""

from __future__ import annotations

from .tax_rules import TAX_YEAR_RULES, get_tax_year_rules, resolve_supported_year, PROVINCE_CODES
from .tax_calculator import calculate_tax
from .social_contributions import calculate_social_contributions
from .tax_dates import get_filing_deadlines
from .claim_rules import generate_ca_claims

try:
    from ..context import LocaleContext
except ImportError:
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "ca"
LOCALE_NAME = "Canada"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "CAD"


def get_tax_rules(year: int) -> dict:
    """Return the raw Canadian federal and provincial tax parameters for the given year."""
    return get_tax_year_rules(year)


def get_social_contributions(gross: float, year: int, province: str = "ON") -> dict:
    """Return CPP/QPP and EI social contribution breakdown for the given gross and year."""
    return calculate_social_contributions(gross, year, province=province)


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable Canadian tax deductions, tax credits, and allowance claims."""
    return generate_ca_claims(ctx, year)
