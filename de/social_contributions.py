"""
German social contribution calculation.

Covers employee and employer shares for all four branches of the
German social insurance system (Sozialversicherung):

  RV  — Rentenversicherung (§ 157 SGB VI): 18.6% total, 9.3% each
  ALV — Arbeitslosenversicherung (§ 341 SGB III): 2.6% total, 1.3% each
  GKV — Krankenversicherung (§ 241 SGB V): 14.6% base + avg. Zusatzbeitrag
  PV  — Pflegeversicherung (§ 55 SGB XI): 3.6% for parents, 4.2% childless
        (childless surcharge since July 2023); from 2025: 3.6% / 4.4%

Beitragsbemessungsgrenzen (caps):
  RV/ALV (West): 2024 €90,600 | 2025 €96,600 | 2026 €101,400
  GKV/PV:        2024 €62,100 | 2025 €66,150 | 2026 €69,750

Sources:
  - § 157 SGB VI (RV-Beitragssatz)
  - § 341 Abs. 2 SGB III (ALV-Beitragssatz)
  - § 241 SGB V (GKV allgemeiner Beitragssatz 14.6%)
  - § 55 SGB XI (PV-Beitragssatz)
  - § 55 Abs. 3 SGB XI (Kinderlosenzuschlag)
  - GKV-Spitzenverband Bekanntmachungen (BBG, Zusatzbeitrag)
  - BMAS Sozialversicherungsrechengrößen (annual regulation)
"""

from __future__ import annotations

# ── Beitragsbemessungsgrenzen ─────────────────────────────────────────────
# Source: BMAS Sozialversicherungsrechengrößen-Verordnung; § 159 SGB VI
SOCIAL_CAPS = {
    2024: {"rv_alv": 90_600, "gkv_pv": 62_100},
    2025: {"rv_alv": 96_600, "gkv_pv": 66_150},
    2026: {"rv_alv": 101_400, "gkv_pv": 69_750},  # 2026: estimated
}

# ── Employee contribution rates ───────────────────────────────────────────
# Source: § 157 SGB VI, § 341 SGB III, § 241 SGB V, § 55 SGB XI
SOCIAL_RATES = {
    # These are the *employee* half-rates used by the legacy function
    "rv_employee": 0.093,    # RV 18.6% / 2
    "alv_employee": 0.013,   # ALV 2.6% / 2
    "gkv_employee": 0.0815,  # GKV 14.6% / 2 + avg Zusatzbeitrag ~1.7%/2 (2024 baseline)
    "pv_employee": 0.018,    # PV half of 3.6% (with children); see PV_RATES below
}

# ── Full contribution rates (total, employer share, employee share) ────────
# Source: BMAS Sozialversicherungsrechengrößen; SGB VI/III/V/XI as above
CONTRIBUTION_RATES = {
    "rv_total": 0.186,         # § 157 SGB VI — Rentenversicherung total
    "rv_employee": 0.093,      # employee half
    "rv_employer": 0.093,      # employer half

    "alv_total": 0.026,        # § 341 SGB III — Arbeitslosenversicherung total
    "alv_employee": 0.013,
    "alv_employer": 0.013,

    "gkv_base_total": 0.146,   # § 241 SGB V — fixed base rate
    "gkv_base_employee": 0.073,
    "gkv_base_employer": 0.073,
    # Zusatzbeitrag split 50/50 employer/employee since 2019 (§ 249 SGB V)
}

# ── Pflegeversicherung rates by year and parental status ──────────────────
# Source: § 55 SGB XI; § 55 Abs. 3 SGB XI (Kinderlosenzuschlag)
# July 2023: PV reformed — new rates from 2023-07-01
# 2025+: childless rate raised to 4.4%
PV_RATES = {
    2024: {
        "with_children_total": 0.036,    # 3.6% total; 1.8% each
        "with_children_employee": 0.018,
        "with_children_employer": 0.018,
        "childless_total": 0.042,        # 4.2% (surcharge +0.6% on employee)
        "childless_employee": 0.024,     # 1.8% + 0.6% surcharge
        "childless_employer": 0.018,     # employer always 1.8%
    },
    2025: {
        "with_children_total": 0.036,
        "with_children_employee": 0.018,
        "with_children_employer": 0.018,
        "childless_total": 0.044,        # 4.4% from 2025 (§ 55 Abs. 3 SGB XI)
        "childless_employee": 0.026,     # 1.8% + 0.8% surcharge
        "childless_employer": 0.018,
    },
    2026: {  # estimated — same as 2025 pending legislation
        "with_children_total": 0.036,
        "with_children_employee": 0.018,
        "with_children_employer": 0.018,
        "childless_total": 0.044,
        "childless_employee": 0.026,
        "childless_employer": 0.018,
    },
}

# ── Average GKV Zusatzbeitrag ─────────────────────────────────────────────
# Source: § 242a SGB V; BMG Bekanntmachung
GKV_ZUSATZBEITRAG_AVG = {
    2024: 0.017,   # BMG Bekanntmachung Dez 2023
    2025: 0.025,   # BMG Bekanntmachung Dez 2024
    2026: 0.025,   # estimated
}

# ── Freelancer GKV Mindestbeitrag (approximate) ───────────────────────────
# Source: § 240 SGB V; GKV-Spitzenverband Grundsätze zur Beitragsbemessung
# Mindestbemessungsgrundlage for self-employed: 1/3 of monthly BBG (~€1.178 in 2024)
# Approximate total monthly minimum premium (all-in):
FREELANCER_GKV_MIN_MONTHLY = {
    2024: 215,   # approx. monthly total (Mindestbemessungsgrundlage × full rate)
    2025: 230,   # approx.
    2026: 245,   # estimated
}


def _resolve_year(year: int) -> int:
    """Return the closest supported year."""
    known = sorted(SOCIAL_CAPS.keys())
    if year in SOCIAL_CAPS:
        return year
    return known[-1] if year > known[-1] else known[0]


def estimate_employee_social_contributions(annual_gross: float, year: int) -> dict:
    """Estimate employee social contributions (legacy-compatible function).

    Args:
        annual_gross: Annual gross salary in EUR.
        year: Calendar year.

    Returns:
        Dict with pension, unemployment, health, care, total (all EUR, annual).
    """
    resolved = _resolve_year(year)
    caps = SOCIAL_CAPS[resolved]
    rv_base = min(annual_gross, caps["rv_alv"])
    gkv_base = min(annual_gross, caps["gkv_pv"])

    # Use SOCIAL_RATES for backward compatibility (2024 baseline Zusatzbeitrag baked in)
    breakdown = {
        "pension": round(rv_base * SOCIAL_RATES["rv_employee"], 2),
        "unemployment": round(rv_base * SOCIAL_RATES["alv_employee"], 2),
        "health": round(gkv_base * SOCIAL_RATES["gkv_employee"], 2),
        "care": round(gkv_base * SOCIAL_RATES["pv_employee"], 2),
    }
    breakdown["total"] = round(sum(breakdown.values()), 2)
    return breakdown


def get_full_contribution_picture(
    annual_gross: float,
    year: int,
    has_children: bool = True,
    zusatzbeitrag_rate: float | None = None,
) -> dict:
    """Return full contribution picture for employee + employer.

    Computes both employee and employer shares for all four branches,
    using the correct Pflegeversicherung rate based on parental status.

    Args:
        annual_gross: Annual gross salary in EUR.
        year: Calendar year.
        has_children: True if the employee has children (affects PV rate).
        zusatzbeitrag_rate: Override GKV Zusatzbeitrag. Defaults to annual average.

    Returns:
        Dict with branches (employee/employer/total per branch), grand totals,
        and freelancer_gkv_min_monthly for reference.
    """
    resolved = _resolve_year(year)
    caps = SOCIAL_CAPS[resolved]
    pv_rates = PV_RATES[resolved]
    zb_rate = zusatzbeitrag_rate if zusatzbeitrag_rate is not None else GKV_ZUSATZBEITRAG_AVG[resolved]

    rv_base = min(annual_gross, caps["rv_alv"])
    gkv_base = min(annual_gross, caps["gkv_pv"])

    pv_key = "with_children" if has_children else "childless"

    # ── RV ───────────────────────────────────────────────────────────────
    rv_employee = round(rv_base * CONTRIBUTION_RATES["rv_employee"], 2)
    rv_employer = round(rv_base * CONTRIBUTION_RATES["rv_employer"], 2)

    # ── ALV ──────────────────────────────────────────────────────────────
    alv_employee = round(rv_base * CONTRIBUTION_RATES["alv_employee"], 2)
    alv_employer = round(rv_base * CONTRIBUTION_RATES["alv_employer"], 2)

    # ── GKV ──────────────────────────────────────────────────────────────
    # Employee: base 7.3% + Zusatzbeitrag/2; employer: base 7.3% + Zusatzbeitrag/2
    gkv_ee_rate = CONTRIBUTION_RATES["gkv_base_employee"] + zb_rate / 2
    gkv_er_rate = CONTRIBUTION_RATES["gkv_base_employer"] + zb_rate / 2
    gkv_employee = round(gkv_base * gkv_ee_rate, 2)
    gkv_employer = round(gkv_base * gkv_er_rate, 2)

    # ── PV ───────────────────────────────────────────────────────────────
    pv_employee = round(gkv_base * pv_rates[f"{pv_key}_employee"], 2)
    pv_employer = round(gkv_base * pv_rates[f"{pv_key}_employer"], 2)

    # ── Totals ────────────────────────────────────────────────────────────
    total_employee = round(rv_employee + alv_employee + gkv_employee + pv_employee, 2)
    total_employer = round(rv_employer + alv_employer + gkv_employer + pv_employer, 2)
    total_combined = round(total_employee + total_employer, 2)

    return {
        "year": resolved,
        "annual_gross": annual_gross,
        "has_children": has_children,
        "zusatzbeitrag_rate": zb_rate,
        "caps": {"rv_alv": caps["rv_alv"], "gkv_pv": caps["gkv_pv"]},
        "branches": {
            "pension_rv": {
                "employee": rv_employee, "employer": rv_employer,
                "total": round(rv_employee + rv_employer, 2),
                "rate_total": CONTRIBUTION_RATES["rv_total"],
                "legal_basis": "§ 157 SGB VI",
            },
            "unemployment_alv": {
                "employee": alv_employee, "employer": alv_employer,
                "total": round(alv_employee + alv_employer, 2),
                "rate_total": CONTRIBUTION_RATES["alv_total"],
                "legal_basis": "§ 341 SGB III",
            },
            "health_gkv": {
                "employee": gkv_employee, "employer": gkv_employer,
                "total": round(gkv_employee + gkv_employer, 2),
                "rate_employee": round(gkv_ee_rate, 6),
                "rate_employer": round(gkv_er_rate, 6),
                "legal_basis": "§ 241, § 249 SGB V",
            },
            "care_pv": {
                "employee": pv_employee, "employer": pv_employer,
                "total": round(pv_employee + pv_employer, 2),
                "rate_employee": pv_rates[f"{pv_key}_employee"],
                "rate_employer": pv_rates[f"{pv_key}_employer"],
                "childless_surcharge_applied": not has_children,
                "legal_basis": "§ 55 SGB XI",
            },
        },
        "totals": {
            "employee_annual": total_employee,
            "employer_annual": total_employer,
            "combined_annual": total_combined,
            "employer_cost_on_top_of_gross": total_employer,
        },
        "freelancer_gkv_min_monthly": FREELANCER_GKV_MIN_MONTHLY.get(resolved),
        "note": (
            "GKV health includes Zusatzbeitrag split 50/50 employee/employer (§ 249 SGB V). "
            "PV rate depends on parental status (§ 55 Abs. 3 SGB XI). "
            "Caps: RV/ALV uses BBG West; GKV/PV uses GKV-BBG."
        ),
    }
