"""US federal tax filing deadlines."""

from __future__ import annotations
from datetime import date, timedelta


def _shift_weekend(d: date) -> date:
    """If d falls on a weekend, shift to the next Monday (simplified — does
    not account for federal holidays)."""
    if d.weekday() == 5:   # Saturday
        return d + timedelta(days=2)
    if d.weekday() == 6:   # Sunday
        return d + timedelta(days=1)
    return d


def get_filing_deadline(tax_year: int) -> date:
    """April 15 of the following year (shifted if weekend — simplified)."""
    return _shift_weekend(date(tax_year + 1, 4, 15))


def get_extension_deadline(tax_year: int) -> date:
    """October 15 of the following year (automatic 6-month extension)."""
    return _shift_weekend(date(tax_year + 1, 10, 15))


def get_estimated_tax_deadlines(tax_year: int) -> list[dict]:
    """Q1-Q4 estimated tax payment deadlines for self-employed filers.

    Regression fix: this used to hardcode Q2=June 17 and Q3=September 16
    for EVERY tax_year — those are the real IRS dates only for 2024 (both
    already weekend-shifted from the standard June 15/September 15 base).
    Computed fresh per tax_year now, using the same weekend-shift logic
    get_filing_deadline/get_extension_deadline already had.
    """
    return [
        {"quarter": "Q1", "deadline": _shift_weekend(date(tax_year, 4, 15)).isoformat(), "label": f"Q1 {tax_year} estimated tax"},
        {"quarter": "Q2", "deadline": _shift_weekend(date(tax_year, 6, 15)).isoformat(), "label": f"Q2 {tax_year} estimated tax"},
        {"quarter": "Q3", "deadline": _shift_weekend(date(tax_year, 9, 15)).isoformat(), "label": f"Q3 {tax_year} estimated tax"},
        {"quarter": "Q4", "deadline": _shift_weekend(date(tax_year + 1, 1, 15)).isoformat(), "label": f"Q4 {tax_year} estimated tax"},
    ]
