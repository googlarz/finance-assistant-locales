"""
Netherlands locale plugin for Finance Assistant.

Bundles Dutch income tax rules (Box 1/2/3), social contributions
(volksverzekeringen embedded in Box 1, ZVW), filing deadlines, and
deduction discovery for tax years 2024–2026.

Dutch tax year = calendar year (1 Jan – 31 Dec).

CAUTION: Box 3 (savings and investments) is subject to ongoing legal
challenge (Kerstarrest, HR 24-12-2021). Box 3 results are marked
"Debatable" when significant assets are present.
"""

from __future__ import annotations

from .tax_rules import TAX_YEAR_RULES, get_tax_year_rules, resolve_supported_year
from .tax_calculator import calculate_tax
from .tax_dates import get_filing_deadlines
from .social_contributions import get_social_contributions
from .claim_rules import generate_dutch_claims

try:
    from ..context import LocaleContext
except ImportError:
    from context import LocaleContext  # type: ignore

LOCALE_CODE = "nl"
LOCALE_NAME = "Netherlands"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "EUR"


def get_tax_rules(year: int) -> dict:
    """Return the raw tax parameters for the given year."""
    return get_tax_year_rules(year)


def generate_tax_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """Discover applicable Dutch deduction/credit claims for the given profile."""
    return generate_dutch_claims(ctx, year)
