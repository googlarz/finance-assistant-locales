"""
UK tax rules for Finance Assistant.

UK tax year runs 6 April to 5 April of the following calendar year.
For this plugin, year=2024 means the 2024/25 tax year (6 Apr 2024 – 5 Apr 2025).

All income tax thresholds are frozen at 2024/25 levels until April 2028
per the Autumn Budget 2022. NI rates reflect the reductions effective
6 January 2024 (Spring Budget 2024).

Sources:
  https://www.gov.uk/income-tax-rates
  https://www.gov.uk/national-insurance-rates-letters
  https://www.gov.uk/individual-savings-accounts
  https://www.gov.uk/tax-on-your-private-pension/annual-allowance
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        # ── Income tax thresholds (2024/25) ──────────────────────────────
        "personal_allowance": 12_570,           # Tax-free allowance
        "basic_rate_limit": 50_270,             # Upper bound of basic rate band
        "higher_rate_limit": 125_140,           # Upper bound of higher rate band
        "additional_rate_threshold": 125_140,   # Income above which additional rate applies
        "personal_allowance_taper_threshold": 100_000,  # £1 lost per £2 over this
        # ── Income tax rates ──────────────────────────────────────────────
        "basic_rate": 0.20,
        "higher_rate": 0.40,
        "additional_rate": 0.45,
        # ── Allowances ────────────────────────────────────────────────────
        "dividend_allowance": 500,
        "capital_gains_allowance": 3_000,
        "marriage_allowance": 1_260,
        "pension_annual_allowance": 60_000,
        "isa_allowance": 20_000,
        # ── National Insurance (Class 1 employee) — reduced Jan 2024 ─────
        "ni_employee_lower_threshold": 12_570,  # Primary Threshold (annualised)
        "ni_employee_upper_threshold": 50_270,  # Upper Earnings Limit
        "ni_employee_rate_main": 0.08,          # 8% on £12,570–£50,270 (Spring Budget 2024)
        "ni_employee_rate_upper": 0.02,         # 2% above UEL
        # ── National Insurance (Class 1 employer) ─────────────────────────
        "ni_employer_secondary_threshold": 9_100,  # Secondary Threshold (annual)
        "ni_employer_rate": 0.138,              # 13.8% above secondary threshold
        # ── Currency ──────────────────────────────────────────────────────
        "currency": "GBP",
        # ── Scottish income tax bands (2024/25) ──────────────────────────
        "scottish_bands": [
            # (rate, lower, upper) — taxable income thresholds (after personal allowance)
            (0.19, 0,       2_306),    # Starter rate
            (0.20, 2_306,   13_991),   # Basic rate
            (0.21, 13_991,  31_092),   # Intermediate rate
            (0.42, 31_092,  62_430),   # Higher rate
            (0.45, 62_430,  125_140),  # Advanced rate
            (0.48, 125_140, None),     # Top rate
        ],
        # ── Confidence ────────────────────────────────────────────────────
        "confidence": "Definitive",
    },
    2025: {
        # Frozen at 2024/25 levels — same thresholds per government policy
        "personal_allowance": 12_570,
        "basic_rate_limit": 50_270,
        "higher_rate_limit": 125_140,
        "additional_rate_threshold": 125_140,
        "personal_allowance_taper_threshold": 100_000,
        "basic_rate": 0.20,
        "higher_rate": 0.40,
        "additional_rate": 0.45,
        "dividend_allowance": 500,
        "capital_gains_allowance": 3_000,
        "marriage_allowance": 1_260,
        "pension_annual_allowance": 60_000,
        "isa_allowance": 20_000,
        "ni_employee_lower_threshold": 12_570,
        "ni_employee_upper_threshold": 50_270,
        "ni_employee_rate_main": 0.08,
        "ni_employee_rate_upper": 0.02,
        "ni_employer_secondary_threshold": 9_100,
        "ni_employer_rate": 0.138,
        "currency": "GBP",
        # ── Scottish income tax bands (2025/26) ──────────────────────────
        "scottish_bands": [
            # (rate, lower, upper) — taxable income thresholds (after personal allowance)
            (0.19, 0,       2_827),    # Starter rate
            (0.20, 2_827,   14_921),   # Basic rate
            (0.21, 14_921,  31_092),   # Intermediate rate
            (0.42, 31_092,  62_430),   # Higher rate
            (0.45, 62_430,  125_140),  # Advanced rate
            (0.48, 125_140, None),     # Top rate
        ],
        "confidence": "Definitive",
    },
    2026: {
        # Still frozen per current projection (until April 2028); marked Likely
        "personal_allowance": 12_570,
        "basic_rate_limit": 50_270,
        "higher_rate_limit": 125_140,
        "additional_rate_threshold": 125_140,
        "personal_allowance_taper_threshold": 100_000,
        "basic_rate": 0.20,
        "higher_rate": 0.40,
        "additional_rate": 0.45,
        "dividend_allowance": 500,
        "capital_gains_allowance": 3_000,
        "marriage_allowance": 1_260,
        "pension_annual_allowance": 60_000,
        "isa_allowance": 20_000,
        "ni_employee_lower_threshold": 12_570,
        "ni_employee_upper_threshold": 50_270,
        "ni_employee_rate_main": 0.08,
        "ni_employee_rate_upper": 0.02,
        "ni_employer_secondary_threshold": 9_100,
        "ni_employer_rate": 0.138,
        "currency": "GBP",
        "confidence": "Likely",  # Frozen thresholds confirmed to 2028; 2026/27 projection
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


def calculate_personal_allowance(gross: float, rules: dict) -> float:
    """
    Apply the personal allowance taper for high earners.

    For income > £100,000, the personal allowance is reduced by £1 for every
    £2 of income above £100,000. At £125,140 the allowance reaches £0.
    """
    taper_threshold = rules["personal_allowance_taper_threshold"]
    base_allowance = rules["personal_allowance"]
    if gross <= taper_threshold:
        return float(base_allowance)
    reduction = (gross - taper_threshold) / 2
    return max(0.0, base_allowance - reduction)


def calculate_income_tax(gross: float, rules: dict) -> float:
    """
    Calculate UK income tax using the tapered personal allowance and
    basic/higher/additional rate bands.
    """
    allowance = calculate_personal_allowance(gross, rules)
    taxable = max(0.0, gross - allowance)

    basic_band_top = rules["basic_rate_limit"] - rules["personal_allowance"]
    higher_band_top = rules["higher_rate_limit"] - rules["personal_allowance"]

    # Recompute band boundaries relative to gross (post-allowance taxable income)
    # Basic rate: taxable income £0 – (basic_rate_limit - personal_allowance)
    # But after taper, the bands shift — simpler to work from gross bands directly.
    # Basic rate applies to income between personal_allowance and basic_rate_limit.
    # Higher rate applies between basic_rate_limit and higher_rate_limit.
    # Additional rate applies above higher_rate_limit.

    basic_allowance_floor = allowance
    basic_ceiling = rules["basic_rate_limit"]
    higher_ceiling = rules["higher_rate_limit"]

    tax = 0.0

    # Basic rate band
    basic_income = max(0.0, min(gross, basic_ceiling) - basic_allowance_floor)
    tax += basic_income * rules["basic_rate"]

    # Higher rate band
    if gross > basic_ceiling:
        higher_income = max(0.0, min(gross, higher_ceiling) - basic_ceiling)
        tax += higher_income * rules["higher_rate"]

    # Additional rate
    if gross > higher_ceiling:
        additional_income = gross - higher_ceiling
        tax += additional_income * rules["additional_rate"]

    return max(0.0, round(tax, 2))


def calculate_marginal_rate(gross: float, rules: dict) -> float:
    """Return the marginal income tax rate for a given gross income.

    The 60% trap (£100,000 – £125,140):
      For each £2 earned above £100k, £1 of personal allowance is lost.
      On £1 of extra income in this zone, you pay:
        • 40% higher-rate tax on that £1                             = £0.40
        • 40% higher-rate tax on the £0.50 of lost allowance        = £0.20
      Total marginal rate = 60%  (confirmed statutory rate — NOT an error)

    Outside the taper zone the bands are straightforward:
      £0        – personal allowance:  0%
      PA        – £50,270:            20% (basic rate)
      £50,270   – £100,000:           40% (higher rate)
      £100,000  – £125,140:           60% (taper zone — see above)
      > £125,140:                     45% (additional rate)
    """
    taper_threshold = rules["personal_allowance_taper_threshold"]
    higher_ceiling = rules["higher_rate_limit"]
    basic_ceiling = rules["basic_rate_limit"]

    if gross <= rules["personal_allowance"]:
        return 0.0
    if gross <= basic_ceiling:
        return rules["basic_rate"]
    if gross <= taper_threshold:
        return rules["higher_rate"]
    if gross <= higher_ceiling:
        # Taper zone — effective marginal rate 60% (see docstring for derivation)
        return 0.60
    return rules["additional_rate"]
