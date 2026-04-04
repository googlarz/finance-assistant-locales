"""
Polish ZUS (Zakład Ubezpieczeń Społecznych) social contributions.

Employee (pracownik na umowę o pracę):
  Emerytalne (pension):   9.76% employee  + 9.76% employer
  Rentowe (disability):   1.50% employee  + 6.50% employer
  Chorobowe (sickness):   2.45% employee  + 0.00% employer  (voluntary for self-employed)
  Wypadkowe (accident):   0.00% employee  + 1.67% employer  (average rate; varies by sector)
  Fundusz Pracy:          0.00% employee  + 2.45% employer
  FGŚP:                   0.00% employee  + 0.10% employer

Total employee ZUS:  13.71% of gross
Total employer ZUS: ~20.48% of gross

Health insurance (składka zdrowotna):
  9% of (gross − employee ZUS contributions)
  NOT deductible from PIT — changed by Polski Ład 2022.
  (Before 2022: 7.75% was deductible from PIT, 1.25% was not.)

ZUS contribution cap (roczna podstawa wymiaru):
  Emerytalne and rentowe contributions are capped at 30× average monthly salary.
  2024 cap: ~234,720 PLN. Chorobowe/wypadkowe are NOT separately capped (they
  follow the same base but stop when the cap is hit).

Sources:
  https://www.zus.pl/pracujacy/skladki-na-ubezpieczenia-spoleczne
  https://www.zus.pl/baza-wiedzy/skladki-wskazniki-odsetki/skladki/wysokosc-skladek-na-ubezpieczenia-spoleczne
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules, resolve_supported_year


def get_social_contributions(gross: float, year: int) -> dict:
    """
    Calculate ZUS employee and employer contributions plus health insurance.

    Args:
        gross: Annual gross salary in PLN (brutto).
        year:  Tax/calendar year.

    Returns:
        Dict with itemised ZUS contributions, totals, and health insurance.
        All monetary values are annual PLN amounts.
    """
    resolved_year, year_note = resolve_supported_year(year)
    rules = get_tax_year_rules(resolved_year)

    gross = float(gross)
    zus_cap = float(rules["zus_roczna_podstawa_max"])

    # ── ZUS base — capped for pension + disability ────────────────────────
    capped_base = min(gross, zus_cap)

    # ── Employee contributions ─────────────────────────────────────────────
    emerytalne_employee = round(capped_base * rules["zus_emerytalne_employee"], 2)
    rentowe_employee = round(capped_base * rules["zus_rentowe_employee"], 2)
    chorobowe_employee = round(capped_base * rules["zus_chorobowe_employee"], 2)
    wypadkowe_employee = 0.0   # Employees pay nothing for accident insurance

    employee_zus_total = round(
        emerytalne_employee + rentowe_employee + chorobowe_employee + wypadkowe_employee, 2
    )

    # ── Employer contributions ─────────────────────────────────────────────
    emerytalne_employer = round(capped_base * 0.0976, 2)
    rentowe_employer = round(capped_base * 0.065, 2)
    wypadkowe_employer = round(gross * 0.0167, 2)    # Not capped at pension base
    fundusz_pracy_employer = round(gross * 0.0245, 2)
    fgsp_employer = round(gross * 0.001, 2)

    employer_zus_total = round(
        emerytalne_employer + rentowe_employer +
        wypadkowe_employer + fundusz_pracy_employer + fgsp_employer, 2
    )

    # ── Health insurance (składka zdrowotna NFZ) ──────────────────────────
    # Base for health insurance = gross − employee ZUS
    health_base = max(0.0, gross - employee_zus_total)
    health_insurance = round(health_base * rules["skladka_zdrowotna_rate"], 2)

    # ── Employee ZUS rate as a fraction of gross ───────────────────────────
    employee_total_rate = round(employee_zus_total / gross, 4) if gross > 0 else 0.0

    return {
        "year": resolved_year,
        "annual_gross": round(gross, 2),
        "year_note": year_note,

        # Employee ZUS
        "emerytalne_employee": emerytalne_employee,
        "rentowe_employee": rentowe_employee,
        "chorobowe_employee": chorobowe_employee,
        "wypadkowe_employee": wypadkowe_employee,
        "employee_total": employee_zus_total,
        "employee_total_rate": employee_total_rate,

        # Employer ZUS
        "emerytalne_employer": emerytalne_employer,
        "rentowe_employer": rentowe_employer,
        "wypadkowe_employer": wypadkowe_employer,
        "fundusz_pracy_employer": fundusz_pracy_employer,
        "fgsp_employer": fgsp_employer,
        "employer_total": employer_zus_total,

        # Health insurance
        "health_insurance": health_insurance,
        "health_insurance_base": round(health_base, 2),
        "health_insurance_rate": rules["skladka_zdrowotna_rate"],
        "health_insurance_deductible": False,  # NOT deductible since Polski Ład 2022

        # ZUS cap info
        "zus_cap": zus_cap,
        "zus_cap_applied": gross > zus_cap,

        # Rates (for reference)
        "rates": {
            "emerytalne_employee": rules["zus_emerytalne_employee"],
            "rentowe_employee": rules["zus_rentowe_employee"],
            "chorobowe_employee": rules["zus_chorobowe_employee"],
            "wypadkowe_employer": 0.0167,
            "fundusz_pracy_employer": 0.0245,
            "fgsp_employer": 0.001,
            "health_insurance": rules["skladka_zdrowotna_rate"],
        },

        "note": (
            "Employee ZUS: emerytalne 9.76% + rentowe 1.5% + chorobowe 2.45% = 13.71% of gross. "
            "Składka zdrowotna: 9% of (gross − ZUS) — NOT deductible from PIT (Polski Ład 2022). "
            f"ZUS capped at {zus_cap:,.0f} PLN annual base (30× avg monthly salary)."
        ),
    }
