"""
Irish tax filing deadlines and key dates.

Ireland uses Pay & File for income tax self-assessment.
PAYE employees have deadlines for claiming additional credits.

Sources:
  https://www.revenue.ie/en/self-assessment-and-self-employment/filing-deadlines/index.aspx
  https://www.revenue.ie/en/jobs-and-pensions/end-of-year-process/index.aspx
"""

from __future__ import annotations
from datetime import date, timedelta


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return key Irish tax deadlines for the given tax year.

    Irish tax year = calendar year. Pay & File deadlines fall in the
    FOLLOWING year (e.g. 2024 tax year deadlines are in Oct/Nov 2025).
    """
    filing_year = year + 1

    deadlines = [
        {
            "label": "Preliminary Tax (current year)",
            "deadline": f"{year}-10-31",
            "notes": (
                "Preliminary tax for the current year must be paid by 31 Oct "
                "(paper) or mid-November (ROS online). Must be at least 90% "
                "of final liability, or 100% of prior year liability."
            ),
        },
        {
            "label": "Pay & File — paper deadline",
            "deadline": f"{filing_year}-10-31",
            "notes": (
                f"Paper filing deadline for {year} income tax return (Form 11). "
                "Balance of tax for the prior year due on same date."
            ),
        },
        {
            "label": "Pay & File — ROS extended deadline",
            "deadline": f"{filing_year}-11-15",
            "notes": (
                f"Extended deadline for {year} return filed AND paid via Revenue "
                "Online Service (ROS). Typically mid-November; exact date "
                "confirmed annually by Revenue."
            ),
        },
        {
            "label": "PAYE — claim additional credits/reliefs",
            "deadline": f"{filing_year}-12-31",
            "notes": (
                f"PAYE employees can claim additional tax credits and reliefs "
                f"for {year} via myAccount up to 4 years after year-end."
            ),
        },
        {
            "label": "Four-year claim window closes",
            "deadline": f"{year + 5}-12-31",
            "notes": (
                f"Last date to claim a refund or additional credits for {year}. "
                "Revenue allows claims up to 4 years after the end of the tax year."
            ),
        },
        {
            "label": "Local Property Tax (LPT) — single payment",
            "deadline": f"{year}-01-12",
            "notes": (
                "Annual LPT single debit payment date (if paying in one lump). "
                "Phased deductions from salary start in January."
            ),
        },
    ]

    return deadlines


def get_upcoming_deadlines(year: int, months_ahead: int = 6) -> list[dict]:
    """
    Return deadlines falling within the next N months from today for
    the given tax year's context.

    Useful for proactive tax planning reminders.
    """
    today = date.today()
    cutoff = today + timedelta(days=months_ahead * 30)

    all_deadlines = get_filing_deadlines(year)
    upcoming = []

    for d in all_deadlines:
        try:
            deadline_date = date.fromisoformat(d["deadline"])
        except (ValueError, TypeError):
            continue
        if today <= deadline_date <= cutoff:
            upcoming.append({
                **d,
                "days_until": (deadline_date - today).days,
            })

    upcoming.sort(key=lambda x: x["deadline"])
    return upcoming
