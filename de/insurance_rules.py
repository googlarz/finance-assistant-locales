"""
German insurance thresholds and helpers.

Covers GKV/PKV eligibility (Versicherungspflichtgrenze / JAEG),
contribution estimates, and essential insurance types for German residents.

Legal references:
  - § 6 SGB V  — Versicherungsfreiheit (JAEG / Jahresarbeitsentgeltgrenze)
  - § 223 SGB V — Beitragsbemessung
  - § 226 SGB V — Beitragspflichtige Einnahmen
  - § 243 SGB V — Zusatzbeitrag
  - § 5 Abs. 1 Nr. 13 SGB V — obligatorische Krankenversicherung
"""

from __future__ import annotations

# ── Jahresarbeitsentgeltgrenze (JAEG) — PKV-Wechselgrenze ─────────────────
# Source: § 6 Abs. 6 u. 7 SGB V; GKV-Spitzenverband Bekanntmachungen
JAEG = {
    2024: 69_300,   # official — Bundesanzeiger 2023
    2025: 73_800,   # official — Bundesanzeiger 2024
    2026: 77_100,   # estimated — based on BBG/JAEG progression
}

# ── Beitragsbemessungsgrenze GKV/PV ───────────────────────────────────────
# Source: § 223 Abs. 3 SGB V; GKV-Spitzenverband
GKV_BBG = {
    2024: 62_100,   # official
    2025: 66_150,   # official
    2026: 69_750,   # estimated
}

# ── Durchschnittlicher GKV-Zusatzbeitragssatz ─────────────────────────────
# Source: § 242a SGB V; BMG Bekanntmachung
GKV_ZUSATZBEITRAG = {
    2024: 0.017,    # 1.7% — BMG Bekanntmachung Dez 2023
    2025: 0.025,    # 2.5% — BMG Bekanntmachung Dez 2024
    2026: 0.025,    # 2.5% — estimated (assumed unchanged)
}

# ── GKV allgemeiner Beitragssatz ──────────────────────────────────────────
# Source: § 241 SGB V — fixed at 14.6% (employer/employee each 7.3%)
GKV_BASE_RATE = 0.146      # 14.6% total, split 7.3% + 7.3%
GKV_EMPLOYEE_BASE = 0.073  # employee share of base rate

# ── PKV Mindestbeitrag (freelancers / voluntarily insured) ────────────────
# Approximate monthly minimum premium for standard tariff (Basistarif):
# Source: GKV-Spitzenverband; PKV-Verband
PKV_MINDESTBEITRAG_MONTHLY = {
    2024: 210,   # approx. minimum monthly PKV contribution (Basistarif)
    2025: 220,   # approx. minimum monthly PKV contribution (Basistarif)
    2026: 230,   # estimated
}

# ── KVdR — Krankenversicherung der Rentner ────────────────────────────────
# Source: § 5 Abs. 1 Nr. 11 SGB V; § 237 SGB V
# Threshold: half the general contribution threshold of the last 2nd half
# of working life must have been covered by GKV (Vorversicherungszeit).
KVDR_VORVERSICHERUNGSZEIT_MIN_RATIO = 0.9  # 90% of second half of working life

# ── Essential insurance types for German residents ────────────────────────
ESSENTIAL_INSURANCE_TYPES = [
    {
        "id": "krankenversicherung",
        "name": "Krankenversicherung (GKV oder PKV)",
        "obligation": "mandatory",
        "legal_basis": "§ 5 Abs. 1 SGB V / § 193 Abs. 3 VVG",
        "note": "Pflichtversicherung für alle Einwohner Deutschlands.",
    },
    {
        "id": "privathaftpflicht",
        "name": "Privathaftpflichtversicherung",
        "obligation": "strongly_recommended",
        "legal_basis": "§ 823 BGB",
        "note": "Deckt Schäden Dritter ab; keine gesetzliche Pflicht, aber dringend empfohlen.",
    },
    {
        "id": "berufsunfaehigkeit",
        "name": "Berufsunfähigkeitsversicherung (BU)",
        "obligation": "strongly_recommended",
        "legal_basis": "none",
        "note": "Einkommenssicherung bei Berufsunfähigkeit; staatliche Erwerbsminderungsrente meist unzureichend.",
    },
    {
        "id": "pflegeversicherung",
        "name": "Pflegeversicherung (SPV)",
        "obligation": "mandatory",
        "legal_basis": "§ 1 SGB XI",
        "note": "Automatisch mit GKV; PKV-Versicherte benötigen private Pflegepflichtversicherung.",
    },
    {
        "id": "kfz_haftpflicht",
        "name": "Kfz-Haftpflichtversicherung",
        "obligation": "mandatory_if_vehicle",
        "legal_basis": "§ 1 PflVG",
        "note": "Pflicht für jedes zugelassene Kfz.",
    },
]


def get_insurance_thresholds(year: int) -> dict:
    """Return key insurance thresholds for the given year.

    Returns a dict with JAEG, GKV BBG, PKV Mindestbeitrag, and Zusatzbeitrag.
    Falls back to the most recent known year if year is out of range.
    """
    known_years = sorted(JAEG.keys())
    if year not in JAEG:
        year = known_years[-1] if year > known_years[-1] else known_years[0]

    return {
        "year": year,
        "jaeg": JAEG[year],
        "gkv_bbg": GKV_BBG[year],
        "gkv_zusatzbeitrag_avg": GKV_ZUSATZBEITRAG[year],
        "pkv_mindestbeitrag_monthly": PKV_MINDESTBEITRAG_MONTHLY[year],
        "gkv_base_rate": GKV_BASE_RATE,
        "essential_insurance_types": ESSENTIAL_INSURANCE_TYPES,
        "note": (
            "JAEG: Versicherungspflichtgrenze (§ 6 SGB V). "
            "GKV-BBG: Beitragsbemessungsgrenze (§ 223 SGB V). "
            "PKV Mindestbeitrag: Approximate Basistarif."
        ),
    }


def get_pkv_eligible(annual_gross: float, year: int) -> bool:
    """Return True if the employee's gross exceeds the JAEG for the year.

    Note: Actual PKV eligibility requires exceeding the JAEG for the *current*
    AND the *previous* calendar year (§ 6 Abs. 4 SGB V). This function checks
    only the single-year threshold and should be used as an indicator only.

    Args:
        annual_gross: Annual gross salary in EUR.
        year: Calendar year to check.

    Returns:
        True if annual_gross > JAEG[year].
    """
    known_years = sorted(JAEG.keys())
    resolved_year = year if year in JAEG else (known_years[-1] if year > known_years[-1] else known_years[0])
    return annual_gross > JAEG[resolved_year]


def get_gkv_contribution_estimate(
    annual_gross: float,
    year: int,
    zusatzbeitrag_rate: float | None = None,
) -> dict:
    """Estimate GKV contributions (employee and employer shares).

    The GKV contribution is capped at the Beitragsbemessungsgrenze.
    Employer pays exactly 7.3% base rate; the Zusatzbeitrag is split 50/50
    between employer and employee (§ 249 SGB V, § 242a SGB V since 2019).

    Args:
        annual_gross: Annual gross income in EUR.
        year: Calendar year.
        zusatzbeitrag_rate: Override the average Zusatzbeitrag (e.g. 0.018).
            Defaults to the published average for the year.

    Returns:
        Dict with employee_annual, employer_annual, total_annual,
        effective_rate_employee, cap_applied (bool), and notes.
    """
    known_years = sorted(GKV_BBG.keys())
    resolved_year = year if year in GKV_BBG else (known_years[-1] if year > known_years[-1] else known_years[0])

    bbg = GKV_BBG[resolved_year]
    base = min(annual_gross, bbg)
    cap_applied = annual_gross > bbg

    zb_rate = zusatzbeitrag_rate if zusatzbeitrag_rate is not None else GKV_ZUSATZBEITRAG[resolved_year]
    # Employee: 7.3% base + half Zusatzbeitrag
    employee_rate = GKV_EMPLOYEE_BASE + zb_rate / 2
    # Employer: 7.3% base + half Zusatzbeitrag
    employer_rate = GKV_EMPLOYEE_BASE + zb_rate / 2

    employee_annual = round(base * employee_rate, 2)
    employer_annual = round(base * employer_rate, 2)
    total_annual = round(employee_annual + employer_annual, 2)

    return {
        "year": resolved_year,
        "annual_gross_used": round(base, 2),
        "cap_applied": cap_applied,
        "bbg": bbg,
        "zusatzbeitrag_rate": zb_rate,
        "employee_annual": employee_annual,
        "employer_annual": employer_annual,
        "total_annual": total_annual,
        "effective_rate_employee": round(employee_rate, 6),
        "effective_rate_employer": round(employer_rate, 6),
        "legal_basis": "§ 223, § 241, § 242a, § 249 SGB V",
    }
