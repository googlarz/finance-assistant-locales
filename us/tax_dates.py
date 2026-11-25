"""US federal tax filing deadlines."""

from __future__ import annotations
from datetime import date, timedelta


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th (1-based) given weekday (Mon=0) of a month; n=-1 means the last."""
    if n > 0:
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """Federal observance rule: Saturday holidays -> Friday, Sunday -> Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _us_federal_holidays(year: int) -> set[date]:
    """Federal legal holidays (5 U.S.C. 6103) as observed in `year`, plus the
    adjacent-year New Year's observance that can fall on Dec 31 (Fri) of `year`."""
    fixed = [(1, 1), (6, 19), (7, 4), (11, 11), (12, 25)]
    days = {_observed(date(y, m, d)) for y in (year, year + 1) for m, d in fixed}
    days |= {
        _nth_weekday(year, 1, 0, 3),    # MLK Day
        _nth_weekday(year, 2, 0, 3),    # Washington's Birthday
        _nth_weekday(year, 5, 0, -1),   # Memorial Day
        _nth_weekday(year, 9, 0, 1),    # Labor Day
        _nth_weekday(year, 10, 0, 2),   # Columbus / Indigenous Peoples' Day
        _nth_weekday(year, 11, 3, 4),   # Thanksgiving
    }
    return days


def _shift_weekend(d: date) -> date:
    """Roll d forward to the next business day: skips Saturdays, Sundays and
    US federal holidays (e.g. Jan 15 2028 is a Saturday, Jan 17 is MLK Day,
    so the due date is Tuesday Jan 18). DC Emancipation Day (Apr 16), which
    can move the April filing deadline, is not handled."""
    while d.weekday() >= 5 or d in _us_federal_holidays(d.year):
        d += timedelta(days=1)
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
