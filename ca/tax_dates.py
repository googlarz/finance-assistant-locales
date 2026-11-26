"""
Canadian tax filing and payment deadlines for individuals and self-employed.

Sources:
  Canada Revenue Agency (CRA) - Important dates for individuals:
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/important-dates-individuals.html
"""

from __future__ import annotations
from datetime import date
from .tax_rules import resolve_supported_year


def get_filing_deadlines(year: int = 2024) -> list[dict]:
    """
    Return all relevant tax filing and payment deadlines for the given tax year.

    In Canada:
    - Standard individual return filing & tax balance due date: April 30 of the following year.
    - Self-employed (and spouse) return filing deadline: June 15 of the following year
      (Note: Any tax balance owed is still due April 30).
    - RRSP contribution deadline for tax deduction: 60 days after year-end (around March 1-3).
    - Quarterly instalment payment dates: March 15, June 15, September 15, December 15 of current year.
    """
    resolved_year, _ = resolve_supported_year(year)
    following_year = resolved_year + 1

    # Adjust for weekend rules (if April 30 or June 15 falls on weekend, deadline is next business day)
    # 2024 tax year -> filed in 2025: April 30, 2025 is Wednesday; June 15, 2025 is Sunday -> Monday June 16, 2025
    # 2025 tax year -> filed in 2026: April 30, 2026 is Thursday; June 15, 2026 is Monday
    # 2026 tax year -> filed in 2027: April 30, 2027 is Friday; June 15, 2027 is Tuesday

    if following_year == 2025:
        standard_deadline = "2025-04-30"
        self_employed_deadline = "2025-06-16"
        rrsp_deadline = "2025-03-03"
    elif following_year == 2026:
        standard_deadline = "2026-04-30"
        self_employed_deadline = "2026-06-15"
        rrsp_deadline = "2026-03-02"
    else:  # 2027
        standard_deadline = "2027-04-30"
        self_employed_deadline = "2027-06-15"
        rrsp_deadline = "2027-03-01"

    deadlines = [
        {
            "type": "standard_individual",
            "label": f"T1 Individual income tax filing & payment deadline ({following_year})",
            "deadline": standard_deadline,
            "notes": (
                "Filing deadline for employed individuals and final payment deadline for any "
                "balance of tax owing to the CRA."
            ),
        },
        {
            "type": "self_employed_filing",
            "label": f"Self-employed filing deadline ({following_year})",
            "deadline": self_employed_deadline,
            "notes": (
                "Filing deadline for self-employed individuals and their spouse/partner. "
                f"Note that any balance owing was still due on {standard_deadline}."
            ),
        },
        {
            "type": "rrsp_contribution",
            "label": f"RRSP contribution deadline for {resolved_year} tax year",
            "deadline": rrsp_deadline,
            "notes": (
                f"Last day to contribute to an RRSP to deduct contributions on your {resolved_year} "
                "tax return (first 60 days of the year)."
            ),
        },
        {
            "type": "instalment_q1",
            "label": f"Q1 Tax instalment deadline ({resolved_year})",
            "deadline": f"{resolved_year}-03-15",
            "notes": "First quarterly tax instalment for individuals required to pay in instalments.",
        },
        {
            "type": "instalment_q2",
            "label": f"Q2 Tax instalment deadline ({resolved_year})",
            "deadline": f"{resolved_year}-06-15",
            "notes": "Second quarterly tax instalment.",
        },
        {
            "type": "instalment_q3",
            "label": f"Q3 Tax instalment deadline ({resolved_year})",
            "deadline": f"{resolved_year}-09-15",
            "notes": "Third quarterly tax instalment.",
        },
        {
            "type": "instalment_q4",
            "label": f"Q4 Tax instalment deadline ({resolved_year})",
            "deadline": f"{resolved_year}-12-15",
            "notes": "Fourth quarterly tax instalment.",
        },
    ]

    return deadlines
