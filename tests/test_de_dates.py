"""Tests for German tax filing deadlines and dates."""
from de.tax_dates import (
    get_filing_deadline,
    get_upcoming_deadlines,
    IMPORTANT_DATES,
)
from de import get_filing_deadlines
from datetime import date


def test_standard_deadline_format():
    deadlines = get_filing_deadlines(2025)
    assert isinstance(deadlines, list)
    assert len(deadlines) == 2
    for d in deadlines:
        assert "deadline" in d
        assert "type" in d
        # deadline should be a valid ISO date string
        parsed = date.fromisoformat(d["deadline"])
        assert parsed.year >= 2025


def test_advised_later_than_standard():
    deadlines = get_filing_deadlines(2025)
    standard = next(d for d in deadlines if d["type"] == "standard")
    advised = next(d for d in deadlines if d["type"] == "with_adviser")
    assert date.fromisoformat(advised["deadline"]) > date.fromisoformat(standard["deadline"])


def test_upcoming_deadlines_returns_list():
    result = get_upcoming_deadlines(2025)
    assert isinstance(result, list)


def test_important_dates_present():
    # Should have all 4 quarterly VAT entries
    vat_keys = [k for k, v in IMPORTANT_DATES.items() if v.get("category") == "vat_prepayment"]
    assert len(vat_keys) >= 4, f"Expected 4 VAT entries, got {len(vat_keys)}: {vat_keys}"


def test_2024_non_advised_deadline_matches_standard_rule():
    """Regression: 2024's non-advised deadline was hardcoded to 2026-04-30,
    contradicting its own inline comment ("standard deadline: 31 Jul 2025")
    and the file's documented § 149 Abs. 2 AO rule (31 July of year+1)."""
    d = get_filing_deadline(2024, advised=False)
    assert d == date(2025, 7, 31)


def test_2025_advised_deadline_matches_standard_rule():
    """Regression: 2025's advised deadline was hardcoded to 2028-02-28,
    a year later than § 149 Abs. 3 AO's "last day of Feb of year+2" rule
    (and later than its own comment, "last day Feb 2028" vs 2025+2=2027)."""
    d = get_filing_deadline(2025, advised=True)
    assert d == date(2027, 2, 28)
