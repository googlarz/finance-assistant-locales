"""
Polish PIT (podatek dochodowy od osób fizycznych) tax rules.

Polish tax year = calendar year (January 1 – December 31).
"Polski Ład" reform has been in effect since January 1, 2022:
  - 12%/32% brackets
  - 30,000 PLN tax-free amount (kwota wolna od podatku)
  - Health insurance (składka zdrowotna) is no longer deductible from PIT

Sources:
  https://www.podatki.gov.pl/pit/twoj-e-pit/
  https://www.zus.pl/pracujacy/skladki-na-ubezpieczenia-spoleczne
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        # ── PIT brackets (skala podatkowa) ────────────────────────────────
        "first_bracket_rate": 0.12,          # 12% up to 120,000 PLN
        "second_bracket_rate": 0.32,         # 32% above 120,000 PLN
        "bracket_threshold": 120_000,        # PLN — above this, 32% applies
        # ── Tax-free amount (kwota wolna od podatku) ─────────────────────
        "tax_free_amount": 30_000,           # PLN
        "tax_reduction": 3_600,             # = 30,000 × 12% — flat reduction applied
        # ── Work cost deductions (koszty uzyskania przychodu) ─────────────
        "pracownicze_koszty_podstawowe": 3_000,   # Annual work costs (1 employer)
        "pracownicze_koszty_podwyzszone": 3_600,  # If commuting from outside city
        # ── Ulga dla młodych (under-26 exemption) ─────────────────────────
        "ulga_dla_mlodych_limit": 85_528,    # Income limit for under-26 PIT exemption
        # ── IKZE (Individual Pension Account — deductible) ────────────────
        "ikze_limit": 9_388,                 # Annual IKZE deduction cap (1.2× avg salary 2024)
        # ── Charitable donations (darowizny) ─────────────────────────────
        "darowizny_pct": 0.06,               # Up to 6% of income deductible
        # ── Internet expense deduction ────────────────────────────────────
        "internet_ulga_max": 760,            # Max deduction in 2 consecutive years only
        # ── Child relief (ulga na dzieci) ─────────────────────────────────
        "ulga_na_dzieci_1_2": 1_112.04,      # Per child, 1st and 2nd child
        "ulga_na_dzieci_3": 2_000.04,        # 3rd child
        "ulga_na_dzieci_4plus": 2_700.0,     # 4th and subsequent children
        # ── ZUS contribution cap ──────────────────────────────────────────
        "zus_roczna_podstawa_max": 234_720,  # Annual cap for pension/disability ZUS (30× avg monthly)
        # ── ZUS employee rates ────────────────────────────────────────────
        "zus_emerytalne_employee": 0.0976,   # Pension — employee share
        "zus_rentowe_employee": 0.015,       # Disability — employee share
        "zus_chorobowe_employee": 0.0245,    # Sickness — employee share
        "zus_employee_total": 0.1371,        # Total employee ZUS (9.76+1.5+2.45)
        # ── Health insurance ──────────────────────────────────────────────
        "skladka_zdrowotna_rate": 0.09,      # 9% of (gross - employee ZUS) — NOT deductible
        # ── Currency ──────────────────────────────────────────────────────
        "currency": "PLN",
        # ── Confidence ────────────────────────────────────────────────────
        "confidence": "Definitive",
    },
    2025: {
        # Same bracket structure as 2024 — no legislation changing rates for 2025
        "first_bracket_rate": 0.12,
        "second_bracket_rate": 0.32,
        "bracket_threshold": 120_000,
        "tax_free_amount": 30_000,
        "tax_reduction": 3_600,
        "pracownicze_koszty_podstawowe": 3_000,
        "pracownicze_koszty_podwyzszone": 3_600,
        "ulga_dla_mlodych_limit": 85_528,
        # IKZE limit indexed annually ~1.2× avg salary; 2025 projected ~9,700 PLN (Likely)
        "ikze_limit": 9_700,
        "darowizny_pct": 0.06,
        "internet_ulga_max": 760,
        "ulga_na_dzieci_1_2": 1_112.04,
        "ulga_na_dzieci_3": 2_000.04,
        "ulga_na_dzieci_4plus": 2_700.0,
        "zus_roczna_podstawa_max": 242_760,  # Estimated — 30× projected avg monthly salary 2025
        "zus_emerytalne_employee": 0.0976,
        "zus_rentowe_employee": 0.015,
        "zus_chorobowe_employee": 0.0245,
        "zus_employee_total": 0.1371,
        "skladka_zdrowotna_rate": 0.09,
        "currency": "PLN",
        "confidence": "Likely",  # Brackets unchanged; IKZE limit estimated by indexation
    },
    2026: {
        # Projected by the same indexation trend; no announced changes for 2026
        "first_bracket_rate": 0.12,
        "second_bracket_rate": 0.32,
        "bracket_threshold": 120_000,
        "tax_free_amount": 30_000,
        "tax_reduction": 3_600,
        "pracownicze_koszty_podstawowe": 3_000,
        "pracownicze_koszty_podwyzszone": 3_600,
        "ulga_dla_mlodych_limit": 85_528,
        # IKZE 2026 — projected further indexation ~10,000–10,100 PLN (Likely)
        "ikze_limit": 10_080,
        "darowizny_pct": 0.06,
        "internet_ulga_max": 760,
        "ulga_na_dzieci_1_2": 1_112.04,
        "ulga_na_dzieci_3": 2_000.04,
        "ulga_na_dzieci_4plus": 2_700.0,
        "zus_roczna_podstawa_max": 250_920,  # Estimated — projected 2026 avg salary
        "zus_emerytalne_employee": 0.0976,
        "zus_rentowe_employee": 0.015,
        "zus_chorobowe_employee": 0.0245,
        "zus_employee_total": 0.1371,
        "skladka_zdrowotna_rate": 0.09,
        "currency": "PLN",
        "confidence": "Likely",  # Projected by indexation; 2026 PIT law not yet published
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
    """Return the tax rules for the given year, falling back to the nearest known year."""
    resolved, _ = resolve_supported_year(year)
    return TAX_YEAR_RULES[resolved]


def calculate_pit(gross: float, rules: dict) -> tuple[float, float]:
    """
    Calculate Polish PIT using the standard skala podatkowa (progressive scale).

    Returns:
        (income_tax, marginal_rate) — income tax before any personal reliefs/credits.

    Note: This applies the bracket arithmetic only. The tax_reduction (3,600 PLN
    equivalent of the 30,000 PLN tax-free amount) is applied separately so callers
    can inspect the intermediate values.
    """
    threshold = rules["bracket_threshold"]
    rate1 = rules["first_bracket_rate"]
    rate2 = rules["second_bracket_rate"]
    tax_reduction = rules["tax_reduction"]

    if gross <= 0:
        return 0.0, 0.0

    if gross <= threshold:
        tax = gross * rate1 - tax_reduction
        marginal = rate1
    else:
        # First bracket: 120,000 × 12% − 3,600 = 14,400 − 3,600 = 10,800
        first_bracket_tax = threshold * rate1 - tax_reduction
        tax = first_bracket_tax + (gross - threshold) * rate2
        marginal = rate2

    return max(0.0, round(tax, 2)), marginal


def calculate_marginal_rate(gross: float, rules: dict) -> float:
    """Return the marginal PIT rate for a given gross income."""
    if gross <= rules["tax_free_amount"]:
        return 0.0
    if gross <= rules["bracket_threshold"]:
        return rules["first_bracket_rate"]
    return rules["second_bracket_rate"]
