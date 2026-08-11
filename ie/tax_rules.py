"""
Irish tax rules for Finance Assistant.

Ireland uses the calendar year (1 Jan – 31 Dec) as the tax year.
Tax is calculated using a credit system: gross tax is computed at 20%/40%
bands, then tax credits are subtracted to arrive at the liability.

USC (Universal Social Charge) is a separate charge on gross income.
PRSI is handled in social_contributions.py.

Sources:
  https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/tax-relief-charts/index.aspx
  https://www.revenue.ie/en/jobs-and-pensions/usc/standard-rates-thresholds.aspx
  Revenue Budget 2026 Summary PDF
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        # ── Income tax bands ─────────────────────────────────────────────
        # Single person standard rate cut-off point
        "standard_rate_band_single": 42_000,
        "standard_rate_band_married_one_income": 51_000,
        "standard_rate_band_married_two_incomes": 51_000,  # + up to €33,000 of 2nd earner
        "second_earner_increase_max": 33_000,
        "standard_rate_band_single_parent": 46_000,
        # ── Income tax rates ─────────────────────────────────────────────
        "standard_rate": 0.20,
        "higher_rate": 0.40,
        # ── Tax credits ──────────────────────────────────────────────────
        "personal_credit_single": 1_875,
        "personal_credit_married": 3_750,
        "employee_credit": 1_875,  # PAYE tax credit
        "earned_income_credit": 1_875,  # for self-employed
        "single_person_child_carer_credit": 1_750,
        "home_carer_credit": 1_800,
        "widowed_person_credit": 2_415,
        "age_credit_single": 245,
        "age_credit_married": 490,
        "rent_credit_single": 1_000,
        "rent_credit_married": 2_000,
        "mortgage_interest_credit_max": 1_250,
        # ── USC thresholds and rates ─────────────────────────────────────
        "usc_exempt_threshold": 13_000,
        "usc_bands": [
            # (upper_limit, rate) — cumulative bands
            (12_012, 0.005),   # 0.5% on first €12,012
            (25_760, 0.02),    # 2% on next €13,748
            (70_044, 0.04),    # 4% on next €44,284
            (None, 0.08),      # 8% on balance
        ],
        # ── Pension relief ───────────────────────────────────────────────
        "pension_earnings_cap": 115_000,
        "pension_age_limits": {
            # age_lower: percentage of net relevant earnings
            0: 0.15,    # under 30
            30: 0.20,   # 30-39
            40: 0.25,   # 40-49
            50: 0.30,   # 50-54
            55: 0.35,   # 55-59
            60: 0.40,   # 60+
        },
        # ── PRSI (employee Class A — for reference; calc in social_contributions.py)
        "prsi_employee_threshold": 352,  # weekly — no employee PRSI below this
        "prsi_employee_rate": 0.04,      # 4% of all gross
        "prsi_employer_rate_low": 0.0875,  # 8.75% on earnings up to €441/week
        "prsi_employer_rate_high": 0.1105,  # 11.05% above €441/week
        # ── Other ────────────────────────────────────────────────────────
        "currency": "EUR",
        "confidence": "Definitive",
    },
    2025: {
        "standard_rate_band_single": 44_000,
        "standard_rate_band_married_one_income": 53_000,
        "standard_rate_band_married_two_incomes": 53_000,
        "second_earner_increase_max": 35_000,
        "standard_rate_band_single_parent": 48_000,
        "standard_rate": 0.20,
        "higher_rate": 0.40,
        "personal_credit_single": 2_000,
        "personal_credit_married": 4_000,
        "employee_credit": 2_000,
        "earned_income_credit": 2_000,
        "single_person_child_carer_credit": 1_900,
        "home_carer_credit": 1_950,
        "widowed_person_credit": 2_540,
        "age_credit_single": 245,
        "age_credit_married": 490,
        "rent_credit_single": 1_000,
        "rent_credit_married": 2_000,
        "mortgage_interest_credit_max": 1_250,
        "usc_exempt_threshold": 13_000,
        "usc_bands": [
            (12_012, 0.005),
            (27_382, 0.02),    # next €15,370
            (70_044, 0.03),    # next €42,662 (rate dropped from 4% to 3%)
            (None, 0.08),
        ],
        "pension_earnings_cap": 115_000,
        "pension_age_limits": {
            0: 0.15, 30: 0.20, 40: 0.25, 50: 0.30, 55: 0.35, 60: 0.40,
        },
        "prsi_employee_threshold": 352,
        "prsi_employee_rate": 0.04,
        "prsi_employer_rate_low": 0.0875,
        "prsi_employer_rate_high": 0.1105,
        "currency": "EUR",
        "confidence": "Definitive",
    },
    2026: {
        "standard_rate_band_single": 44_000,
        "standard_rate_band_married_one_income": 53_000,
        "standard_rate_band_married_two_incomes": 53_000,
        "second_earner_increase_max": 35_000,
        "standard_rate_band_single_parent": 48_000,
        "standard_rate": 0.20,
        "higher_rate": 0.40,
        "personal_credit_single": 2_000,
        "personal_credit_married": 4_000,
        "employee_credit": 2_000,
        "earned_income_credit": 2_000,
        "single_person_child_carer_credit": 1_900,
        "home_carer_credit": 1_950,
        "widowed_person_credit": 2_540,
        "age_credit_single": 245,
        "age_credit_married": 490,
        "rent_credit_single": 1_000,
        "rent_credit_married": 2_000,
        "mortgage_interest_credit_max": 1_250,
        "usc_exempt_threshold": 13_000,
        "usc_bands": [
            (12_012, 0.005),
            (28_700, 0.02),    # next €16,688
            (70_044, 0.03),    # next €41,344
            (None, 0.08),
        ],
        "pension_earnings_cap": 115_000,
        "pension_age_limits": {
            0: 0.15, 30: 0.20, 40: 0.25, 50: 0.30, 55: 0.35, 60: 0.40,
        },
        # PRSI rates increase 1 Oct 2026 — use the pre-October rates as
        # the annual default; social_contributions.py handles the split.
        "prsi_employee_threshold": 352,
        "prsi_employee_rate": 0.042,  # 4.2% (up from 4.0% in 2025)
        "prsi_employer_rate_low": 0.09,
        "prsi_employer_rate_high": 0.1125,
        "currency": "EUR",
        "confidence": "Definitive",
    },
}


def resolve_supported_year(year: int) -> tuple[int, Optional[str]]:
    """Return the closest supported year and an optional warning note."""
    if year in TAX_YEAR_RULES:
        return year, None
    supported = sorted(TAX_YEAR_RULES)
    if year < supported[0]:
        return supported[0], (
            f"Tax year {year} is older than bundled rules. "
            f"Using {supported[0]} as fallback."
        )
    latest = supported[-1]
    return latest, (
        f"Tax year {year} is newer than bundled rules. "
        f"Using {latest} as fallback."
    )


def get_tax_year_rules(year: int) -> dict:
    resolved, _ = resolve_supported_year(year)
    return TAX_YEAR_RULES[resolved]


def calculate_usc(gross: float, rules: dict) -> float:
    """
    Calculate Universal Social Charge on gross income.

    USC is charged on total income before deductions or credits.
    If gross <= exemption threshold, no USC is due.
    """
    if gross <= rules["usc_exempt_threshold"]:
        return 0.0

    usc = 0.0
    remaining = gross
    prev_upper = 0

    for upper, rate in rules["usc_bands"]:
        if remaining <= 0:
            break
        if upper is None:
            usc += remaining * rate
            remaining = 0
        else:
            band_size = upper - prev_upper
            in_band = min(remaining, band_size)
            usc += in_band * rate
            remaining -= in_band
            prev_upper = upper

    return round(usc, 2)


def calculate_income_tax(gross: float, rules: dict, married: bool = False,
                         two_incomes: bool = False) -> float:
    """
    Calculate Irish income tax (before credits) at 20%/40% bands.

    Ireland uses a tax credit system: first compute gross tax, then
    subtract credits separately. This function returns gross tax only.
    """
    if married and not two_incomes:
        band = rules["standard_rate_band_married_one_income"]
    elif married and two_incomes:
        band = rules["standard_rate_band_married_two_incomes"]
    else:
        band = rules["standard_rate_band_single"]

    standard_portion = min(gross, band)
    higher_portion = max(0.0, gross - band)

    tax = standard_portion * rules["standard_rate"] + higher_portion * rules["higher_rate"]
    return round(tax, 2)


def get_total_credits(rules: dict, is_employee: bool = True,
                      married: bool = False) -> float:
    """Return the sum of basic tax credits for a typical taxpayer."""
    if married:
        credits = rules["personal_credit_married"]
    else:
        credits = rules["personal_credit_single"]

    if is_employee:
        credits += rules["employee_credit"]
    else:
        credits += rules["earned_income_credit"]

    return float(credits)
