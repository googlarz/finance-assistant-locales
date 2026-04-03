"""
United Kingdom locale plugin for Finance Assistant.

Bundles income tax rules, National Insurance contributions, filing deadlines,
and deduction discovery for UK tax years 2024, 2025, and 2026.

Tax year convention: year=2024 → 2024/25 (6 April 2024 – 5 April 2025).
"""

from __future__ import annotations

from .tax_rules import TAX_YEAR_RULES, get_tax_year_rules, resolve_supported_year
from .tax_calculator import calculate_tax
from .social_contributions import get_social_contributions
from .tax_dates import get_filing_deadlines, get_upcoming_deadlines
from .claim_rules import generate_uk_claims

try:
    from ..context import LocaleContext
except ImportError:
    # Standalone usage: locales/ root is on sys.path
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "uk"
LOCALE_NAME = "United Kingdom"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "GBP"


def get_tax_rules(year: int) -> dict:
    """Return the raw UK tax parameters for the given year."""
    return get_tax_year_rules(year)


def get_social_contributions(gross: float, year: int) -> dict:
    """Return National Insurance contribution breakdown for the given gross and year."""
    from .social_contributions import get_social_contributions as _get_ni
    return _get_ni(gross, year)


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable UK tax deduction and allowance claims."""
    return generate_uk_claims(ctx, year)
