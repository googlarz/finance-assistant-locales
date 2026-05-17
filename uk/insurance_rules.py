"""
UK insurance thresholds and helpers.

Covers NHS context, income protection, life insurance, critical illness,
and mandatory/recommended insurance types for UK residents.

The UK operates a fundamentally different model from Germany:
  - NHS provides free healthcare at point of use — private health insurance (PMI) is optional
  - No mandatory health insurance contribution (NI funds NHS but is not earmarked)
  - Statutory Sick Pay (SSP) replaces GKV Krankengeld but at a much lower rate
  - Self-employed receive NO SSP — private income protection is critical for them

Legal references:
  - Road Traffic Act 1988, s. 143 — compulsory motor insurance
  - Employers' Liability (Compulsory Insurance) Act 1969 — employer liability
  - Social Security Contributions and Benefits Act 1992 — SSP framework
"""

from __future__ import annotations

# ── Statutory Sick Pay (SSP) ─────────────────────────────────────────────────
# Source: https://www.gov.uk/statutory-sick-pay
# Paid by employer for up to 28 weeks; applies to employees earning ≥ LEL.
# Self-employed are NOT eligible.
SSP_WEEKLY = {
    2024: 116.75,   # 2024/25 — gov.uk/statutory-sick-pay (official)
    2025: 116.75,   # 2025/26 — gov.uk/statutory-sick-pay (official; unchanged)
    2026: 116.75,   # estimated — frozen; update when DWP announces
}

# Lower Earnings Limit (LEL) — must earn at least this to qualify for SSP
# Source: https://www.gov.uk/national-insurance-rates-letters
NI_LOWER_EARNINGS_LIMIT_WEEKLY = {
    2024: 123,      # 2024/25 — official
    2025: 125,      # 2025/26 — official
    2026: 125,      # estimated
}

# SSP maximum duration (weeks)
SSP_MAX_WEEKS = 28

# ── Income Protection — typical coverage parameters ──────────────────────────
# ABI (Association of British Insurers) industry guidance: most policies cover
# 50–70% of gross salary, paid monthly after a deferred period (typically
# 4, 8, 13, 26, or 52 weeks). Premiums vary substantially by age, health,
# occupation class, and deferred period; no fixed "market rate" exists.
# Source: https://www.abi.org.uk/products-and-issues/topics-and-issues/income-protection/
INCOME_PROTECTION_COVERAGE_RANGE = (0.50, 0.70)  # 50–70% of gross salary (ABI guidance)

# ── Life insurance — rule of thumb multipliers ───────────────────────────────
# "10× salary" is the widely cited industry rule of thumb (ABI / MoneyHelper).
# For mortgage holders: cover should at minimum equal outstanding mortgage.
# Source: https://www.moneyhelper.org.uk/en/insurance/life-insurance/how-much-life-insurance-do-i-need
LIFE_INSURANCE_SALARY_MULTIPLE = 10  # rule of thumb: 10× gross annual salary

# ── Essential insurance types for UK residents ───────────────────────────────
ESSENTIAL_INSURANCE_TYPES = [
    {
        "id": "motor",
        "name": "Motor Insurance (Third Party at minimum)",
        "obligation": "mandatory_if_vehicle",
        "legal_basis": "Road Traffic Act 1988, s. 143",
        "note": (
            "Driving or keeping a vehicle on a public road without at least "
            "third-party insurance is a criminal offence."
        ),
    },
    {
        "id": "employer_liability",
        "name": "Employers' Liability Insurance",
        "obligation": "mandatory_if_employing",
        "legal_basis": "Employers' Liability (Compulsory Insurance) Act 1969",
        "note": (
            "Required for any business with at least one employee (including "
            "part-time and temporary workers). Minimum cover £5 million. "
            "Sole traders with no employees are exempt."
        ),
    },
    {
        "id": "income_protection",
        "name": "Income Protection Insurance",
        "obligation": "strongly_recommended",
        "legal_basis": "none",
        "note": (
            "SSP pays only £116.75/week for up to 28 weeks (2024/25); self-employed "
            "receive nothing. Income protection replaces 50–70% of gross salary "
            "after a chosen deferred period. Especially critical for the self-employed, "
            "contractors, and anyone with dependants or a mortgage."
        ),
    },
    {
        "id": "life_insurance",
        "name": "Life Insurance (Term or Whole of Life)",
        "obligation": "strongly_recommended_if_dependants",
        "legal_basis": "none",
        "note": (
            "Rule of thumb: 10× annual gross salary, or enough to clear the mortgage "
            "plus support dependants for the required period. Not needed if no dependants "
            "and no outstanding debts. Level term is cheapest for mortgage cover."
        ),
    },
    {
        "id": "critical_illness",
        "name": "Critical Illness Cover",
        "obligation": "recommended",
        "legal_basis": "none",
        "note": (
            "Pays a tax-free lump sum on diagnosis of a specified serious illness "
            "(e.g. cancer, heart attack, stroke). Uniquely popular in the UK. "
            "Often combined with life insurance. Useful to clear mortgage or fund "
            "adaptations if unable to work long-term."
        ),
    },
    {
        "id": "private_health",
        "name": "Private Medical Insurance (PMI)",
        "obligation": "optional",
        "legal_basis": "none",
        "note": (
            "NHS provides free treatment at point of use. PMI adds faster access, "
            "choice of consultant, and private facilities. Not necessary for most people "
            "but valued by those who want to bypass NHS waiting lists."
        ),
    },
    {
        "id": "buildings_contents",
        "name": "Buildings and Contents Insurance",
        "obligation": "optional_but_recommended",
        "legal_basis": "none",
        "note": (
            "Buildings insurance is typically required by mortgage lenders as a "
            "condition of the loan. Contents insurance is optional but recommended. "
            "Renters need contents only (landlord insures the building)."
        ),
    },
    {
        "id": "travel",
        "name": "Travel Insurance",
        "obligation": "optional",
        "legal_basis": "none",
        "note": (
            "Recommended for any travel outside the UK. EHIC/GHIC covers emergency "
            "NHS-equivalent treatment in most of Europe but does not cover repatriation, "
            "cancellation, or lost luggage."
        ),
    },
]


def _resolve_year(year: int, table: dict) -> int:
    known = sorted(table.keys())
    if year in table:
        return year
    return known[-1] if year > known[-1] else known[0]


def get_income_protection_guidance(gross: float, year: int = 2025) -> dict:
    """Return income protection guidance for a UK resident.

    Based on gross annual salary, SSP rate for the year, and ABI industry
    coverage conventions (50–70% of gross). Premium ranges are not quoted
    because they vary materially by age, health, and occupation class.

    Args:
        gross: Annual gross salary in GBP.
        year: Tax year (e.g. 2025 = 2025/26).

    Returns:
        Dict with:
          recommended_monthly_benefit_low  — 50% of gross / 12
          recommended_monthly_benefit_high — 70% of gross / 12
          typical_premium_range_monthly    — "varies by age/health/occupation"
          ssp_context                      — SSP rate and duration for the year
          adequacy_note                    — narrative guidance
          source                           — provenance
    """
    resolved = _resolve_year(year, SSP_WEEKLY)
    ssp_weekly = SSP_WEEKLY[resolved]
    ssp_annual = round(ssp_weekly * 52, 2)
    ssp_max_payout = round(ssp_weekly * SSP_MAX_WEEKS, 2)

    low_monthly = round(gross * INCOME_PROTECTION_COVERAGE_RANGE[0] / 12, 2)
    high_monthly = round(gross * INCOME_PROTECTION_COVERAGE_RANGE[1] / 12, 2)

    return {
        "year": resolved,
        "gross_annual": gross,
        "recommended_monthly_benefit_low": low_monthly,
        "recommended_monthly_benefit_high": high_monthly,
        "typical_premium_range_monthly": "Varies by age, health, occupation class, and deferred period — obtain quotes (ABI guidance; no fixed market rate)",
        "ssp_context": {
            "ssp_weekly_gbp": ssp_weekly,
            "ssp_annual_equivalent_gbp": ssp_annual,
            "ssp_max_total_payout_gbp": ssp_max_payout,
            "ssp_max_weeks": SSP_MAX_WEEKS,
            "self_employed_eligible": False,
            "source": "https://www.gov.uk/statutory-sick-pay",
        },
        "adequacy_note": (
            f"SSP pays £{ssp_weekly}/week (£{ssp_annual:.0f}/year equivalent) for up to "
            f"{SSP_MAX_WEEKS} weeks — far below most people's living costs. "
            f"A policy covering {int(INCOME_PROTECTION_COVERAGE_RANGE[0]*100)}–"
            f"{int(INCOME_PROTECTION_COVERAGE_RANGE[1]*100)}% of gross (£{low_monthly:,.0f}–"
            f"£{high_monthly:,.0f}/month) provides meaningful protection. "
            "Self-employed individuals receive no SSP and should treat income protection as essential."
        ),
        "source": "https://www.abi.org.uk/products-and-issues/topics-and-issues/income-protection/",
    }


def get_life_insurance_guidance(
    gross: float,
    mortgage: float = 0,
    dependants: int = 0,
) -> dict:
    """Return life insurance cover guidance for a UK resident.

    Uses the industry rule of thumb of 10× gross salary as a baseline,
    then adds outstanding mortgage if provided.

    Args:
        gross: Annual gross salary in GBP.
        mortgage: Outstanding mortgage balance in GBP (default 0).
        dependants: Number of financial dependants (default 0).

    Returns:
        Dict with:
          recommended_cover  — higher of (10× salary) and (mortgage + income multiple)
          salary_based_cover — 10× gross
          mortgage_cover     — mortgage amount passed in
          note               — narrative guidance
          source             — provenance
    """
    salary_based = round(gross * LIFE_INSURANCE_SALARY_MULTIPLE, 2)
    mortgage_plus_income = round(mortgage + gross * LIFE_PROTECTION_YEARS_IF_DEPENDANTS(dependants), 2)
    recommended = max(salary_based, mortgage_plus_income, mortgage)

    note_parts = []
    if dependants == 0 and mortgage == 0:
        note_parts.append(
            "No dependants and no mortgage: life insurance may not be necessary. "
            "Consider whether anyone else relies on your income before purchasing."
        )
    else:
        if mortgage > 0:
            note_parts.append(f"Cover should at minimum clear the outstanding mortgage (£{mortgage:,.0f}).")
        if dependants > 0:
            note_parts.append(
                f"With {dependants} dependant(s), the 10× salary rule of thumb (£{salary_based:,.0f}) "
                "is a reasonable starting point; adjust for specific income-replacement needs."
            )

    return {
        "gross_annual": gross,
        "dependants": dependants,
        "mortgage": mortgage,
        "salary_based_cover": salary_based,
        "mortgage_cover": mortgage,
        "recommended_cover": recommended,
        "note": " ".join(note_parts) if note_parts else f"Recommended cover: £{recommended:,.0f}.",
        "source": "https://www.moneyhelper.org.uk/en/insurance/life-insurance/how-much-life-insurance-do-i-need",
    }


def LIFE_PROTECTION_YEARS_IF_DEPENDANTS(dependants: int) -> float:
    """Return salary multiple for income replacement based on number of dependants.

    Simple heuristic: 0 dependants → 0, 1–2 → 5× salary, 3+ → 7× salary.
    The 10× rule already covers most scenarios; this adjusts upward for
    larger families when combined with a mortgage.
    """
    if dependants == 0:
        return 0.0
    if dependants <= 2:
        return 5.0
    return 7.0
