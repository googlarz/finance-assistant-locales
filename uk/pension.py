"""
UK pension annual allowance, carry-forward, and salary sacrifice calculations.

Key rules (2023/24 onwards):
  - Annual allowance: £60,000 (raised from £40,000 in 2023/24)
  - Tapered annual allowance: applies when adjusted income > £260,000
      Reduces by £1 per £2 of adjusted income above £260,000
      Minimum tapered allowance: £10,000
  - Carry-forward: unused allowance from up to 3 prior tax years
      Earliest year used first; requires pension scheme membership in prior years
  - Salary sacrifice: employer pays pension contributions from gross pay
      Saves employee income tax at marginal rate + NI at main/upper rate
      Saves employer NI at 13.8%

Sources:
  https://www.gov.uk/tax-on-your-private-pension/annual-allowance
  https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm057100
  HMRC PTM057200 — carry-forward rules
  HMRC PTM044100 — salary sacrifice and pensions
"""

from __future__ import annotations

from typing import Optional

try:
    from tax_rules import get_tax_year_rules
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from tax_rules import get_tax_year_rules


# ── Tapering ──────────────────────────────────────────────────────────────────

_TAPER_RULES = {
    # tax_year: (threshold_income, adjusted_income_trigger, taper_per_2_pounds, minimum_allowance)
    2023: (200_000, 260_000, 1, 10_000),
    2024: (200_000, 260_000, 1, 10_000),
    2025: (200_000, 260_000, 1, 10_000),
}


def get_tapered_annual_allowance(
    adjusted_income: float,
    tax_year: int = 2024,
) -> tuple[float, str]:
    """
    Return the tapered annual allowance and a note explaining any reduction.

    'Adjusted income' = net income + all employer pension contributions.
    This function accepts gross income as a proxy when employer contributions
    are unknown — note the limitation in the returned explanation.

    Source: HMRC PTM057100

    Args:
        adjusted_income: Gross income + employer pension contributions
        tax_year: UK tax year start year (e.g. 2024 = 2024/25 tax year)

    Returns:
        (annual_allowance_pounds, explanation_note)
    """
    rules = get_tax_year_rules(tax_year)
    full_allowance = float(rules.get("pension_annual_allowance", 60_000))

    taper_params = _TAPER_RULES.get(tax_year, _TAPER_RULES.get(2024))
    _, adj_trigger, _, minimum = taper_params

    if adjusted_income <= adj_trigger:
        return full_allowance, (
            f"Full annual allowance of £{full_allowance:,.0f} applies "
            f"(adjusted income £{adjusted_income:,.0f} ≤ taper trigger £{adj_trigger:,.0f})."
        )

    excess = adjusted_income - adj_trigger
    reduction = (excess // 2)  # £1 reduction per £2 over trigger
    tapered = max(float(minimum), full_allowance - reduction)
    return tapered, (
        f"Tapered annual allowance: £{tapered:,.0f}. "
        f"Full allowance £{full_allowance:,.0f} reduced by £{reduction:,.0f} "
        f"(adjusted income £{adjusted_income:,.0f} exceeds £{adj_trigger:,.0f} trigger by £{excess:,.0f})."
    )


# ── Carry-forward ─────────────────────────────────────────────────────────────

def calculate_pension_carry_forward(
    prior_year_data: list[dict],
    current_year_gross: float,
    current_year_contribution: float,
    tax_year: int = 2024,
    adjusted_income: Optional[float] = None,
) -> dict:
    """
    Calculate available pension carry-forward from up to 3 prior tax years.

    Carry-forward rules (HMRC PTM057200):
      1. You must have been a member of a registered pension scheme in each
         prior year you wish to carry forward from.
      2. Unused allowance = min(that year's annual allowance, earnings) - contributions
      3. Carry-forward is used in order: earliest year first.
      4. You cannot carry forward more than you earned in the current year.

    Args:
        prior_year_data: List of up to 3 dicts (oldest → newest), each with:
            {
              "tax_year": int,           # e.g. 2021 for 2021/22
              "annual_allowance": float, # allowance for that year (before tapering)
              "contributions": float,    # total contributions in that year
              "was_member": bool,        # were you in a pension scheme? (default True)
            }
        current_year_gross: Gross employment/self-employment income this tax year
        current_year_contribution: Pension contributions already made this tax year
        tax_year: Current tax year (e.g. 2024 = 2024/25)
        adjusted_income: Adjusted income for tapering (gross + employer contributions).
            If None, uses current_year_gross as proxy.

    Returns:
        {
          "current_annual_allowance": float,     # possibly tapered
          "taper_note": str,
          "carry_forward_available": float,       # unused from prior years
          "carry_forward_detail": [               # per prior year
            {"tax_year": int, "unused": float, "cumulative_available": float}
          ],
          "total_pension_capacity": float,        # current allowance + carry-forward
          "remaining_this_year": float,           # capacity - current contributions
          "earnings_cap": float,                  # max relief = current gross income
          "effective_limit": float,               # min(total_pension_capacity, earnings_cap)
          "note": str,
          "currency": "GBP",
        }
    """
    if adjusted_income is None:
        adjusted_income = current_year_gross

    current_allowance, taper_note = get_tapered_annual_allowance(adjusted_income, tax_year)

    carry_forward = 0.0
    detail = []

    for yr_data in prior_year_data[-3:]:  # only 3 prior years allowed
        if not yr_data.get("was_member", True):
            detail.append({
                "tax_year": yr_data.get("tax_year"),
                "unused": 0.0,
                "note": "Not a pension scheme member — no carry-forward available for this year.",
            })
            continue

        yr_allowance = float(yr_data.get("annual_allowance", 40_000))
        yr_contributions = float(yr_data.get("contributions", 0))
        unused = max(0.0, yr_allowance - yr_contributions)
        carry_forward += unused
        detail.append({
            "tax_year": yr_data.get("tax_year"),
            "annual_allowance": yr_allowance,
            "contributions": yr_contributions,
            "unused": round(unused, 2),
        })

    total_capacity = current_allowance + carry_forward
    remaining = max(0.0, total_capacity - current_year_contribution)
    # Relief is capped at 100% of UK earnings (employment + self-employment income)
    earnings_cap = current_year_gross
    effective_limit = min(total_capacity, earnings_cap)

    notes = []
    if carry_forward > 0:
        notes.append(
            f"Carry-forward of £{carry_forward:,.0f} available from prior {len(detail)} year(s)."
        )
    if current_year_contribution > current_allowance:
        notes.append(
            f"Current contributions (£{current_year_contribution:,.0f}) already exceed "
            f"this year's allowance (£{current_allowance:,.0f}) — carry-forward being used."
        )
    if earnings_cap < total_capacity:
        notes.append(
            f"Contributions are capped at gross earnings (£{earnings_cap:,.0f}) "
            "regardless of carry-forward. Relief cannot exceed 100% of UK earnings."
        )
    notes.append(
        "Carry-forward requires pension scheme membership in each prior year used."
    )

    return {
        "current_annual_allowance": round(current_allowance, 2),
        "taper_note": taper_note,
        "carry_forward_available": round(carry_forward, 2),
        "carry_forward_detail": detail,
        "total_pension_capacity": round(total_capacity, 2),
        "remaining_this_year": round(remaining, 2),
        "earnings_cap": round(earnings_cap, 2),
        "effective_limit": round(effective_limit, 2),
        "note": " ".join(notes),
        "currency": "GBP",
    }


# ── Salary Sacrifice ──────────────────────────────────────────────────────────

def calculate_salary_sacrifice(
    gross_salary: float,
    sacrifice_amount: float,
    tax_year: int = 2024,
    include_employer_saving: bool = True,
) -> dict:
    """
    Model the net financial impact of a salary sacrifice pension arrangement.

    In a salary sacrifice scheme the employee formally reduces their contractual
    salary by the sacrifice amount; the employer pays that sum directly into the
    pension. This means:
      - Employee pays income tax on the reduced salary (saves tax at marginal rate)
      - Employee pays NI on the reduced salary (saves NI at applicable rate)
      - Employer pays NI on the reduced salary (saves employer NI at 13.8%)

    The employer's NI saving is sometimes passed on to employees or used to
    increase the pension contribution. This function shows both scenarios.

    Source: HMRC Employment Income Manual EIM42750, HMRC PTM044100

    Args:
        gross_salary: Pre-sacrifice gross annual salary
        sacrifice_amount: Annual salary to sacrifice into the pension
        tax_year: UK tax year (e.g. 2024 = 2024/25)
        include_employer_saving: Whether to surface employer NI saving

    Returns:
        {
          "gross_salary": float,
          "sacrifice_amount": float,
          "new_gross_salary": float,        # gross_salary - sacrifice_amount
          "income_tax_saving": float,        # income tax saved at marginal rate
          "employee_ni_saving": float,       # NI saved at applicable rate
          "total_employee_saving": float,
          "net_cost_to_employee": float,     # sacrifice - total saving
          "employer_ni_saving": float,       # employer NI saved (13.8%)
          "effective_pension_contribution": float,  # sacrifice + optional employer NI pass-through
          "marginal_income_tax_rate": float,
          "employee_ni_rate_on_sacrifice": float,
          "note": str,
          "currency": "GBP",
        }
    """
    try:
        from tax_rules import calculate_marginal_rate, get_tax_year_rules
    except ImportError:
        from locales.uk.tax_rules import calculate_marginal_rate, get_tax_year_rules

    rules = get_tax_year_rules(tax_year)
    new_gross = gross_salary - sacrifice_amount

    if new_gross < 0:
        raise ValueError(
            f"sacrifice_amount (£{sacrifice_amount:,.0f}) exceeds gross_salary "
            f"(£{gross_salary:,.0f}). Cannot sacrifice more than full salary."
        )

    # Income tax saving at marginal rate on the sacrifice amount
    marginal_rate = calculate_marginal_rate(gross_salary, rules)
    income_tax_saving = sacrifice_amount * marginal_rate

    # NI saving: depends on where sacrifice falls in the NI bands
    main_rate = rules["ni_employee_rate_main"]      # 8% within main band
    upper_rate = rules["ni_employee_rate_upper"]    # 2% above UEL
    lower_threshold = rules["ni_employee_lower_threshold"]  # £12,570
    upper_threshold = rules["ni_employee_upper_threshold"]  # £50,270

    def _ni_on_range(income: float) -> float:
        """Calculate employee NI on a given income level."""
        ni = 0.0
        if income <= lower_threshold:
            return ni
        main_band_income = max(0.0, min(income, upper_threshold) - lower_threshold)
        ni += main_band_income * main_rate
        if income > upper_threshold:
            ni += (income - upper_threshold) * upper_rate
        return ni

    ni_before = _ni_on_range(gross_salary)
    ni_after = _ni_on_range(new_gross)
    employee_ni_saving = ni_before - ni_after

    # NI rate applicable to the sacrificed slice (for reporting)
    if gross_salary <= lower_threshold:
        ni_rate_on_sacrifice = 0.0
    elif new_gross >= upper_threshold:
        ni_rate_on_sacrifice = upper_rate
    elif gross_salary > upper_threshold and new_gross < upper_threshold:
        # Sacrifice spans both NI bands — weighted average
        upper_portion = gross_salary - upper_threshold
        lower_portion = sacrifice_amount - upper_portion
        weighted = (upper_portion * upper_rate + lower_portion * main_rate) / sacrifice_amount
        ni_rate_on_sacrifice = round(weighted, 4)
    else:
        ni_rate_on_sacrifice = main_rate

    total_employee_saving = income_tax_saving + employee_ni_saving
    net_cost = sacrifice_amount - total_employee_saving

    # Employer NI saving
    employer_rate = rules["ni_employer_rate"]
    emp_sec_threshold = rules["ni_employer_secondary_threshold"]
    def _employer_ni_on_range(income: float) -> float:
        return max(0.0, income - emp_sec_threshold) * employer_rate
    employer_ni_saving = _employer_ni_on_range(gross_salary) - _employer_ni_on_range(new_gross)

    notes = []
    if marginal_rate == 0.60:
        notes.append(
            "You're in the 60% effective marginal rate zone (£100,000–£125,140 taper). "
            "Salary sacrifice is especially tax-efficient here — it also restores personal allowance."
        )
    if include_employer_saving and employer_ni_saving > 0:
        notes.append(
            f"Employer saves £{employer_ni_saving:,.0f} in NI — some employers pass this "
            "to the employee's pension. Ask your employer if they offer NI matching."
        )
    notes.append(
        "Salary sacrifice reduces contractual pay, which may affect mortgage applications, "
        "life cover, and state pension contributions. Verify with your employer."
    )

    return {
        "gross_salary": gross_salary,
        "sacrifice_amount": sacrifice_amount,
        "new_gross_salary": round(new_gross, 2),
        "income_tax_saving": round(income_tax_saving, 2),
        "employee_ni_saving": round(employee_ni_saving, 2),
        "total_employee_saving": round(total_employee_saving, 2),
        "net_cost_to_employee": round(net_cost, 2),
        "employer_ni_saving": round(employer_ni_saving, 2),
        "effective_pension_contribution": sacrifice_amount,
        "marginal_income_tax_rate": marginal_rate,
        "employee_ni_rate_on_sacrifice": ni_rate_on_sacrifice,
        "note": " ".join(notes),
        "currency": "GBP",
    }
