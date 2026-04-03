"""
UK National Insurance contributions.

Class 1 NI (employee):
  - 8% on earnings between £12,570 and £50,270 per year (Primary Threshold to UEL)
  - 2% on earnings above £50,270 (above Upper Earnings Limit)
  Note: Rate was reduced from 12% to 8% on 6 January 2024 (Spring Budget 2024)
        and further from 10% to 8% on 6 April 2024.

Class 1 NI (employer):
  - 13.8% on earnings above £9,100 per year (Secondary Threshold)

Self-employed (Class 4 NI):
  - 6% on profits between £12,570 and £50,270
  - 2% on profits above £50,270
  Note: Class 2 NI was abolished from April 2024.

Sources:
  https://www.gov.uk/national-insurance-rates-letters
  https://www.gov.uk/self-employed-national-insurance-rates
"""

from __future__ import annotations


NI_THRESHOLDS = {
    2024: {
        # Employee (Class 1)
        "employee_lower_threshold": 12_570,    # Primary Threshold (annual)
        "employee_upper_threshold": 50_270,    # Upper Earnings Limit (annual)
        "employee_rate_main": 0.08,            # 8% between PT and UEL
        "employee_rate_upper": 0.02,           # 2% above UEL
        # Employer (Class 1)
        "employer_secondary_threshold": 9_100,  # Secondary Threshold (annual)
        "employer_rate": 0.138,                # 13.8% above ST
        # Self-employed (Class 4)
        "se_lower_threshold": 12_570,          # Lower Profits Limit
        "se_upper_threshold": 50_270,          # Upper Profits Limit
        "se_rate_main": 0.06,                  # 6% between LPL and UPL
        "se_rate_upper": 0.02,                 # 2% above UPL
    },
    2025: {
        "employee_lower_threshold": 12_570,
        "employee_upper_threshold": 50_270,
        "employee_rate_main": 0.08,
        "employee_rate_upper": 0.02,
        "employer_secondary_threshold": 9_100,
        "employer_rate": 0.138,
        "se_lower_threshold": 12_570,
        "se_upper_threshold": 50_270,
        "se_rate_main": 0.06,
        "se_rate_upper": 0.02,
    },
    2026: {
        "employee_lower_threshold": 12_570,
        "employee_upper_threshold": 50_270,
        "employee_rate_main": 0.08,
        "employee_rate_upper": 0.02,
        "employer_secondary_threshold": 9_100,
        "employer_rate": 0.138,
        "se_lower_threshold": 12_570,
        "se_upper_threshold": 50_270,
        "se_rate_main": 0.06,
        "se_rate_upper": 0.02,
    },
}


def _resolve_year(year: int) -> int:
    known = sorted(NI_THRESHOLDS.keys())
    if year in NI_THRESHOLDS:
        return year
    return known[-1] if year > known[-1] else known[0]


def get_social_contributions(gross: float, year: int, self_employed: bool = False) -> dict:
    """
    Return National Insurance contribution breakdown.

    Args:
        gross: Annual gross earnings/profits in GBP.
        year: Tax year (e.g. 2024 = 2024/25 tax year).
        self_employed: If True, calculate Class 4 NI instead of Class 1 employee NI.

    Returns:
        Dict with employee NI, employer NI (where applicable), and totals.
    """
    resolved = _resolve_year(year)
    t = NI_THRESHOLDS[resolved]

    if self_employed:
        # Class 4 NI for self-employed
        lower = t["se_lower_threshold"]
        upper = t["se_upper_threshold"]

        main_band = max(0.0, min(gross, upper) - lower)
        upper_band = max(0.0, gross - upper)

        ni_employee = round(
            main_band * t["se_rate_main"] + upper_band * t["se_rate_upper"], 2
        )
        ni_employer = 0.0
        note = (
            "Class 4 NI (self-employed): 6% on £12,570–£50,270, 2% above. "
            "Class 2 NI abolished from April 2024."
        )
    else:
        # Class 1 NI (employee)
        lower = t["employee_lower_threshold"]
        upper = t["employee_upper_threshold"]

        main_band = max(0.0, min(gross, upper) - lower)
        upper_band = max(0.0, gross - upper)

        ni_employee = round(
            main_band * t["employee_rate_main"] + upper_band * t["employee_rate_upper"], 2
        )

        # Employer NI
        er_base = max(0.0, gross - t["employer_secondary_threshold"])
        ni_employer = round(er_base * t["employer_rate"], 2)

        note = (
            "Class 1 NI (employee): 8% on £12,570–£50,270, 2% above. "
            "Rate reduced from 12% to 8% effective 6 Jan / 6 Apr 2024 (Spring Budget). "
            "Employer: 13.8% above £9,100 secondary threshold."
        )

    return {
        "year": resolved,
        "annual_gross": gross,
        "self_employed": self_employed,
        "ni_employee": ni_employee,
        "ni_employer": ni_employer,
        "total_ni": round(ni_employee + ni_employer, 2),
        "rates": {
            "employee_rate_main": t["se_rate_main"] if self_employed else t["employee_rate_main"],
            "employee_rate_upper": t["se_rate_upper"] if self_employed else t["employee_rate_upper"],
            "employer_rate": 0.0 if self_employed else t["employer_rate"],
        },
        "note": note,
    }
