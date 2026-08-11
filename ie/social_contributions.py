"""
Irish PRSI (Pay Related Social Insurance) calculations.

PRSI Class A applies to most employees. Class S applies to self-employed.
Employer PRSI is also calculated for completeness.

Sources:
  https://www.gov.ie/en/publication/prsi-class-a-rates/
  https://www.citizensinformation.ie/en/social-welfare/irish-social-welfare-system/social-insurance-prsi/paying-social-insurance/
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules, resolve_supported_year


def get_social_contributions(gross: float, year: int,
                             self_employed: bool = False) -> dict:
    """
    Calculate PRSI contributions for Irish workers.

    Args:
        gross: Annual gross income in EUR.
        year: Tax year.
        self_employed: If True, use Class S rates instead of Class A.

    Returns:
        Dict with prsi_employee, prsi_employer, total_prsi, rates, note.
    """
    resolved_year, _ = resolve_supported_year(year)
    rules = get_tax_year_rules(resolved_year)

    if self_employed:
        return _class_s(gross, rules, resolved_year)
    return _class_a(gross, rules, resolved_year)


def _class_a(gross: float, rules: dict, year: int) -> dict:
    """
    PRSI Class A (employees).

    Employee: flat rate on all earnings once weekly income exceeds threshold.
    A tapered credit applies for low earners (€352-€424/week).
    Employer: split rate (lower on earnings up to €441/week, higher above).
    """
    employee_rate = rules["prsi_employee_rate"]
    weekly_threshold = rules["prsi_employee_threshold"]
    annual_threshold = weekly_threshold * 52

    # Employee PRSI
    if gross <= annual_threshold:
        prsi_employee = 0.0
    else:
        # PRSI is charged on ALL earnings (not just excess) once threshold is exceeded
        prsi_employee = round(gross * employee_rate, 2)

        # Tapered PRSI credit for earnings between €352 and €424/week
        weekly_gross = gross / 52
        if weekly_gross <= 424:
            # Credit = max(12, 1/6 * (424 - weekly_gross)) per week
            weekly_credit = min(12.0, (424 - weekly_gross) / 6)
            annual_credit = round(weekly_credit * 52, 2)
            prsi_employee = max(0.0, round(prsi_employee - annual_credit, 2))

    # Employer PRSI
    employer_rate_low = rules["prsi_employer_rate_low"]
    employer_rate_high = rules["prsi_employer_rate_high"]
    employer_weekly_threshold = 441  # €441/week boundary
    annual_employer_threshold = employer_weekly_threshold * 52

    if gross <= annual_employer_threshold:
        prsi_employer = round(gross * employer_rate_low, 2)
    else:
        prsi_employer = round(gross * employer_rate_high, 2)

    total = round(prsi_employee + prsi_employer, 2)

    return {
        "prsi_employee": prsi_employee,
        "prsi_employer": prsi_employer,
        "total_prsi": total,
        "total": total,
        "class": "A",
        "rates": {
            "employee": employee_rate,
            "employer_low": employer_rate_low,
            "employer_high": employer_rate_high,
        },
        "note": (
            f"Class A ({year}). Employee: {employee_rate*100:.1f}% on all earnings "
            f"(nil if weekly income ≤ €{weekly_threshold}). "
            f"Employer: {employer_rate_low*100:.2f}%/​{employer_rate_high*100:.2f}% "
            f"split at €441/week."
        ),
    }


def _class_s(gross: float, rules: dict, year: int) -> dict:
    """
    PRSI Class S (self-employed).

    Flat 4% on all income, minimum contribution €500.
    No employer component.
    """
    rate = rules["prsi_employee_rate"]
    minimum = 500.0

    if gross <= 5000:
        prsi_employee = 0.0
    else:
        prsi_employee = max(minimum, round(gross * rate, 2))

    return {
        "prsi_employee": prsi_employee,
        "prsi_employer": 0.0,
        "total_prsi": prsi_employee,
        "total": prsi_employee,
        "class": "S",
        "rates": {
            "employee": rate,
            "minimum": minimum,
        },
        "note": (
            f"Class S ({year}). {rate*100:.1f}% on all income, "
            f"minimum €{minimum:.0f}. No employer PRSI for self-employed."
        ),
    }
