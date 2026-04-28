"""US federal tax filing deadlines."""

from __future__ import annotations
from datetime import date


def get_filing_deadline(tax_year: int) -> date:
    """April 15 of the following year (shifted if weekend/holiday — simplified)."""
    d = date(tax_year + 1, 4, 15)
    # If April 15 falls on a weekend, shift to next Monday
    if d.weekday() == 5:   # Saturday
        return date(tax_year + 1, 4, 17)
    if d.weekday() == 6:   # Sunday
        return date(tax_year + 1, 4, 16)
    return d


def get_extension_deadline(tax_year: int) -> date:
    """October 15 of the following year (automatic 6-month extension)."""
    d = date(tax_year + 1, 10, 15)
    if d.weekday() == 5:
        return date(tax_year + 1, 10, 17)
    if d.weekday() == 6:
        return date(tax_year + 1, 10, 16)
    return d


def get_estimated_tax_deadlines(tax_year: int) -> list[dict]:
    """Q1–Q4 estimated tax payment deadlines for self-employed filers."""
    return [
        {"quarter": "Q1", "deadline": date(tax_year, 4, 15).isoformat(), "label": f"Q1 {tax_year} estimated tax"},
        {"quarter": "Q2", "deadline": date(tax_year, 6, 17).isoformat(), "label": f"Q2 {tax_year} estimated tax"},
        {"quarter": "Q3", "deadline": date(tax_year, 9, 16).isoformat(), "label": f"Q3 {tax_year} estimated tax"},
        {"quarter": "Q4", "deadline": date(tax_year + 1, 1, 15).isoformat(), "label": f"Q4 {tax_year} estimated tax"},
    ]
