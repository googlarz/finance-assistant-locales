"""
French social contributions for salaried employees (salariat).

Sources:
  https://www.urssaf.fr/accueil/outils-et-services/fiches-pratiques/plafond-securite-sociale.html
  https://www.service-public.fr/particuliers/vosdroits/F2971
  https://www.agirc-arrco.fr/
"""

from __future__ import annotations

# Plafond de la Sécurité Sociale (PASS) by year — needed for AGIRC-ARRCO caps
_PASS = {
    2024: 46_368,
    2025: 47_100,  # estimated
    2026: 47_800,  # estimated
}

# Plafond SS mensuel = PASS / 12; AGIRC-ARRCO tranche 1 is up to 1× PASS
# Tranche 2 is from 1× to 8× PASS


def get_social_contributions(gross: float, year: int) -> dict:
    """
    Return employee and employer social contribution breakdown for salaried workers.

    All rates are expressed as decimals. employee_share is the employee-only
    portion; annual_max is the maximum annual contribution for that item
    (None = uncapped).

    Note: assurance chômage employee contribution is 0% since 2018 (employer only).
    CSG/CRDS are listed here for reference but are also present in the IR output.
    """
    pass_annual = _PASS.get(year, _PASS[max(_PASS)])

    tranche1_gross = min(gross, pass_annual)
    tranche2_gross = max(0.0, min(gross, pass_annual * 8) - pass_annual)

    # ── Maladie ───────────────────────────────────────────────────────────
    # Employee: 0.75% (post-reform, all income)
    # Employer: 7.0% below pass, 13.0% above
    maladie_employee = gross * 0.0075
    maladie_employer_t1 = tranche1_gross * 0.070
    maladie_employer_t2 = max(0.0, gross - pass_annual) * 0.130
    maladie_employer = maladie_employer_t1 + maladie_employer_t2

    # ── Retraite de base (CNAV) ───────────────────────────────────────────
    # Employee: 6.9% up to PASS
    # Employer: 8.55% up to PASS
    retraite_base_employee = tranche1_gross * 0.069
    retraite_base_employer = tranche1_gross * 0.0855

    # ── Retraite complémentaire AGIRC-ARRCO ───────────────────────────────
    # Tranche 1 (up to PASS): employee 3.15%, employer 4.72%
    # Tranche 2 (1×–8× PASS): employee 8.64%, employer 12.95%
    retraite_comp_t1_employee = tranche1_gross * 0.0315
    retraite_comp_t1_employer = tranche1_gross * 0.0472
    retraite_comp_t2_employee = tranche2_gross * 0.0864
    retraite_comp_t2_employer = tranche2_gross * 0.1295

    retraite_comp_employee = retraite_comp_t1_employee + retraite_comp_t2_employee
    retraite_comp_employer = retraite_comp_t1_employer + retraite_comp_t2_employer

    # ── Assurance chômage ─────────────────────────────────────────────────
    # Employee: 0% since 2018
    # Employer: 4.05% up to 4× PASS
    chomage_base = min(gross, pass_annual * 4)
    chomage_employee = 0.0
    chomage_employer = chomage_base * 0.0405

    # ── CSG / CRDS (prélèvements sociaux) ────────────────────────────────
    # Applied on 98.25% of gross (after 1.75% professional expenses deduction)
    # For simplicity we apply to full gross as is common in calculators.
    csg_employee = gross * 0.092
    crds_employee = gross * 0.005

    # ── Totals ────────────────────────────────────────────────────────────
    total_employee = (
        maladie_employee
        + retraite_base_employee
        + retraite_comp_employee
        + csg_employee
        + crds_employee
    )
    total_employer = (
        maladie_employer
        + retraite_base_employer
        + retraite_comp_employer
        + chomage_employer
    )

    return {
        "assurance_maladie": {
            "employee_share": round(maladie_employee, 2),
            "employer_share": round(maladie_employer, 2),
            "rate_employee": 0.0075,
            "rate_employer": 0.070,
            "annual_max": None,
        },
        "retraite_base_cnav": {
            "employee_share": round(retraite_base_employee, 2),
            "employer_share": round(retraite_base_employer, 2),
            "rate_employee": 0.069,
            "rate_employer": 0.0855,
            "annual_max": round(pass_annual * 0.069, 2),
        },
        "retraite_complementaire_agirc_arrco": {
            "employee_share": round(retraite_comp_employee, 2),
            "employer_share": round(retraite_comp_employer, 2),
            "tranche1": {
                "rate_employee": 0.0315,
                "rate_employer": 0.0472,
                "ceiling": pass_annual,
                "employee": round(retraite_comp_t1_employee, 2),
                "employer": round(retraite_comp_t1_employer, 2),
            },
            "tranche2": {
                "rate_employee": 0.0864,
                "rate_employer": 0.1295,
                "ceiling": pass_annual * 8,
                "employee": round(retraite_comp_t2_employee, 2),
                "employer": round(retraite_comp_t2_employer, 2),
            },
            "annual_max": round(pass_annual * 0.0315 + pass_annual * 7 * 0.0864, 2),
        },
        "assurance_chomage": {
            "employee_share": 0.0,
            "employer_share": round(chomage_employer, 2),
            "rate_employee": 0.0,
            "rate_employer": 0.0405,
            "annual_max": round(pass_annual * 4 * 0.0405, 2),
            "notes": "Employee contribution abolished since 2018.",
        },
        "csg": {
            "employee_share": round(csg_employee, 2),
            "employer_share": 0.0,
            "rate_employee": 0.092,
            "rate_employer": 0.0,
            "deductible_portion": round(gross * 0.068, 2),
            "non_deductible_portion": round(gross * 0.024, 2),
            "annual_max": None,
        },
        "crds": {
            "employee_share": round(crds_employee, 2),
            "employer_share": 0.0,
            "rate_employee": 0.005,
            "rate_employer": 0.0,
            "annual_max": None,
        },
        "totals": {
            "total_employee": round(total_employee, 2),
            "total_employer": round(total_employer, 2),
            "pass_annual": pass_annual,
        },
    }
