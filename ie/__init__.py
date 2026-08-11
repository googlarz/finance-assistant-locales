"""
Ireland locale plugin for Finance Assistant.

Bundles income tax rules, USC (Universal Social Charge), PRSI (Pay Related
Social Insurance), filing deadlines, and deduction discovery for Irish tax
years 2024, 2025, and 2026.

Tax year convention: Ireland uses the calendar year (1 Jan – 31 Dec).

Sources:
  https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/tax-relief-charts/index.aspx
  https://www.revenue.ie/en/jobs-and-pensions/usc/standard-rates-thresholds.aspx
  https://www.gov.ie/en/department-of-social-protection/publications/prsi-class-a-rates/
"""

from __future__ import annotations

from .tax_rules import TAX_YEAR_RULES, get_tax_year_rules, resolve_supported_year
from .tax_calculator import calculate_tax
from .social_contributions import get_social_contributions
from .tax_dates import get_filing_deadlines, get_upcoming_deadlines
from .claim_rules import generate_ie_claims
from .insurance_rules import (
    ESSENTIAL_INSURANCE_TYPES,
    get_income_protection_guidance,
    get_life_insurance_guidance,
)

try:
    from ..context import LocaleContext
except ImportError:
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "ie"
LOCALE_NAME = "Ireland"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "EUR"


def get_tax_rules(year: int) -> dict:
    """Return the raw Irish tax parameters for the given year."""
    return get_tax_year_rules(year)


def get_social_contributions(gross: float, year: int) -> dict:
    """Return PRSI contribution breakdown for the given gross and year."""
    from .social_contributions import get_social_contributions as _get_prsi
    return _get_prsi(gross, year)


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable Irish tax deduction and credit claims."""
    return generate_ie_claims(ctx, year)
