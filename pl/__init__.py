"""
Polish locale plugin for Finance Assistant.

Bundles PIT tax rules, ZUS social contributions, filing deadlines,
and deduction discovery for 2024–2026 under the Polski Ład framework.

Tax year = calendar year (1 January – 31 December).
"""

from __future__ import annotations

from .tax_rules import TAX_YEAR_RULES, get_tax_year_rules
from .tax_calculator import calculate_tax
from .tax_dates import get_filing_deadlines, get_upcoming_deadlines
from .social_contributions import get_social_contributions
from .claim_rules import generate_polish_claims

try:
    from ..context import LocaleContext
except ImportError:
    # Standalone usage: locales/ root is on sys.path
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "pl"
LOCALE_NAME = "Poland"
SUPPORTED_YEARS = [2024, 2025, 2026]


def get_tax_rules(year: int) -> dict:
    """Return the raw PIT parameters for the given year."""
    return get_tax_year_rules(year)


def get_social_contributions(gross: float, year: int) -> dict:
    """Return ZUS and health insurance contribution breakdown for the given gross and year."""
    from .social_contributions import get_social_contributions as _get
    return _get(gross, year)


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable PIT deduction and relief claims for the given profile and year."""
    return generate_polish_claims(ctx, year)
