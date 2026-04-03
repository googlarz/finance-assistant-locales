"""
UK tax filing deadlines and important dates.

UK tax year runs 6 April to 5 April of the following calendar year.
For year=2024 this means the 2024/25 tax year ending 5 April 2025.

Self Assessment key dates:
  - Paper return deadline: 31 October of the same calendar year as year-end
  - Online (HMRC) return deadline: 31 January of the following calendar year
  - Tax payment deadline: 31 January of the following calendar year
  - Second payment on account: 31 July of the following calendar year
  - PAYE coding notice review: April (start of new tax year)

Payments on account are required where the Self Assessment tax bill exceeds
£1,000 and less than 80% is collected at source (PAYE). Each payment on
account is 50% of the prior year's SA tax bill.

Sources:
  https://www.gov.uk/self-assessment-tax-returns/deadlines
  https://www.gov.uk/pay-self-assessment-tax-bill
"""

from __future__ import annotations
from datetime import date, timedelta


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return all relevant Self Assessment filing and payment deadlines
    for the UK tax year ending 5 April of (year+1).

    Args:
        year: The tax year start (e.g. 2024 = 2024/25 tax year).

    Returns:
        List of dicts with keys: label, deadline (ISO 8601), notes.
    """
    # Tax year ends 5 April of year+1; filing window is in that same calendar year.
    # The paper and online return deadlines are relative to the tax year end date.
    tax_year_end = year + 1  # e.g. 2024 → deadlines fall in 2025

    deadlines = [
        {
            "label": "Tax year end",
            "deadline": f"{tax_year_end}-04-05",
            "notes": (
                f"End of UK tax year {year}/{str(tax_year_end)[-2:]}. "
                "Ensure all income and reliefs are recorded."
            ),
        },
        {
            "label": "Register for Self Assessment",
            "deadline": f"{tax_year_end}-10-05",
            "notes": (
                "Deadline to register for Self Assessment if filing for the "
                f"first time for tax year {year}/{str(tax_year_end)[-2:]}."
            ),
        },
        {
            "label": "Paper Self Assessment return",
            "deadline": f"{tax_year_end}-10-31",
            "notes": (
                f"Paper return for tax year {year}/{str(tax_year_end)[-2:]} must "
                "reach HMRC by 31 October. Filing online gives an extra 3 months."
            ),
        },
        {
            "label": "Online Self Assessment return",
            "deadline": f"{tax_year_end + 1}-01-31",
            "notes": (
                f"Online Self Assessment return for tax year "
                f"{year}/{str(tax_year_end)[-2:]} due 31 January "
                f"{tax_year_end + 1} via HMRC online or commercial software."
            ),
        },
        {
            "label": "Tax payment (balancing + first payment on account)",
            "deadline": f"{tax_year_end + 1}-01-31",
            "notes": (
                f"Balancing payment for {year}/{str(tax_year_end)[-2:]} plus "
                f"first payment on account for {tax_year_end}/{str(tax_year_end + 1)[-2:]} "
                "both due 31 January. Interest applies from this date."
            ),
        },
        {
            "label": "Second payment on account",
            "deadline": f"{tax_year_end + 1}-07-31",
            "notes": (
                f"Second payment on account for {tax_year_end}/{str(tax_year_end + 1)[-2:]} "
                "tax year due 31 July. Each payment on account is 50% of "
                "the prior year Self Assessment liability."
            ),
        },
        {
            "label": "PAYE tax code review",
            "deadline": f"{tax_year_end}-04-06",
            "notes": (
                "Start of new tax year. Review HMRC P2 notice of coding to "
                "ensure your PAYE tax code correctly reflects your allowances "
                "and any outstanding liabilities."
            ),
        },
    ]

    return deadlines


def get_upcoming_deadlines(year: int, months_ahead: int = 3) -> list[dict]:
    """
    Return filing and payment deadlines falling within the next N months
    from 1 January of the given year.

    Args:
        year: Calendar year to base the window on (not the tax year).
        months_ahead: How many calendar months ahead to look (default 3).

    Returns:
        List of deadline dicts sorted by date ascending, containing only
        deadlines that fall within the window.
    """
    window_start = date(year, 1, 1)
    # Advance by months_ahead calendar months
    end_month = window_start.month + months_ahead
    end_year = window_start.year + (end_month - 1) // 12
    end_month = ((end_month - 1) % 12) + 1
    window_end = date(end_year, end_month, 1)

    # Collect deadlines for the tax year that started in year-1 and year
    candidates = []
    for tax_year in (year - 2, year - 1, year):
        for dl in get_filing_deadlines(tax_year):
            candidates.append(dl)

    results = []
    for dl in candidates:
        try:
            dl_date = date.fromisoformat(dl["deadline"])
        except ValueError:
            continue
        if window_start <= dl_date < window_end:
            results.append(dl)

    results.sort(key=lambda x: x["deadline"])
    return results
