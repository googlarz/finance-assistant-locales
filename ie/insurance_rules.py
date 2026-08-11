"""
Irish insurance guidance for financial planning.

Covers: income protection, life insurance, motor insurance, and health
insurance in the Irish context. Tax relief available on some products.

Sources:
  https://www.revenue.ie/en/personal-tax-credits-reliefs-and-exemptions/insurance-policies/income-protection/index.aspx
  https://www.citizensinformation.ie/en/money-and-tax/insurance/
"""

from __future__ import annotations


ESSENTIAL_INSURANCE_TYPES = [
    {
        "type": "income_protection",
        "priority": "high",
        "description": (
            "Replaces up to 75% of income if unable to work due to illness/injury. "
            "Tax relief at marginal rate on premiums. Benefit is taxable as income."
        ),
        "tax_relief": True,
        "relief_rate": "marginal (20% or 40%)",
    },
    {
        "type": "life_insurance",
        "priority": "high_if_dependants",
        "description": (
            "Lump sum on death. Essential if you have dependants or a mortgage. "
            "No income tax relief on premiums (relief abolished 2001). "
            "Proceeds generally tax-free to beneficiaries."
        ),
        "tax_relief": False,
    },
    {
        "type": "health_insurance",
        "priority": "medium",
        "description": (
            "Private health insurance (VHI, Laya, Irish Life). Tax relief at 20% "
            "applied at source (TRS). Covers private hospital, consultants, "
            "and faster access. Not required — public system available via medical card."
        ),
        "tax_relief": True,
        "relief_rate": "20% at source",
    },
    {
        "type": "motor_insurance",
        "priority": "mandatory",
        "description": (
            "Third-party motor insurance is legally required in Ireland. "
            "No tax relief. Shop around annually — loyalty penalty is real."
        ),
        "tax_relief": False,
    },
    {
        "type": "home_insurance",
        "priority": "high_if_owner",
        "description": (
            "Buildings insurance required by mortgage lender. Contents optional "
            "but recommended. No tax relief on premiums."
        ),
        "tax_relief": False,
    },
    {
        "type": "serious_illness",
        "priority": "medium",
        "description": (
            "Lump sum on diagnosis of specified illnesses (cancer, stroke, etc.). "
            "Complements income protection. No tax relief on premiums."
        ),
        "tax_relief": False,
    },
]


def get_income_protection_guidance(gross: float, age: int = None) -> dict:
    """
    Return income protection guidance for Irish context.

    Key Irish-specific points:
    - Tax relief at marginal rate (20% or 40%) on premiums.
    - Benefit capped at 75% of pre-disability income.
    - Benefit payments are taxable as income (USC + PRSI exempt).
    - Deferred period: 13/26/52 weeks (longer = cheaper premium).
    """
    recommended_cover = round(gross * 0.75, 2)

    guidance = {
        "recommended_cover": recommended_cover,
        "cover_ratio": 0.75,
        "tax_relief": True,
        "relief_note": (
            "Premiums qualify for tax relief at your marginal rate (20% or 40%). "
            "Effective cost is significantly reduced. E.g. €100/month premium "
            "costs €60/month net if you pay 40% tax."
        ),
        "benefit_taxation": (
            "Benefit payments are subject to income tax and USC but exempt from PRSI."
        ),
        "deferred_period_options": [
            {"weeks": 13, "note": "Most expensive; covers from week 13"},
            {"weeks": 26, "note": "Mid-range; many employers provide 6 months sick pay"},
            {"weeks": 52, "note": "Cheapest; suitable if you have savings to bridge"},
        ],
        "key_considerations": [
            "Check if employer provides group income protection (common in Ireland).",
            "Revenue allows relief on premiums up to 10% of total income.",
            "Policies typically pay until age 65/66 (State Pension age).",
            "Existing conditions: full disclosure required; non-disclosure voids policy.",
        ],
    }

    if age and age >= 50:
        guidance["age_note"] = (
            "Premiums increase significantly over 50. Consider locking in now "
            "or accepting higher deferred period to reduce cost."
        )

    return guidance


def get_life_insurance_guidance(gross: float, has_dependants: bool = False,
                                has_mortgage: bool = False) -> dict:
    """
    Return life insurance guidance for Irish context.

    No tax relief on premiums since 2001.
    Proceeds generally exempt from income tax and CGT.
    May be liable to CAT (inheritance tax) if not structured correctly.
    """
    if has_mortgage:
        priority = "essential"
        note = "Mortgage protection is a condition of most Irish mortgage lending."
    elif has_dependants:
        priority = "high"
        note = "Recommended to cover dependants' living costs and childcare."
    else:
        priority = "low"
        note = "Limited need without dependants or mortgage obligations."

    recommended_multiple = 10 if has_dependants else 5
    recommended_cover = round(gross * recommended_multiple, 2)

    return {
        "priority": priority,
        "recommended_cover": recommended_cover,
        "cover_multiple": recommended_multiple,
        "tax_relief": False,
        "relief_note": "No income tax relief on life insurance premiums (abolished 2001).",
        "proceeds_tax": (
            "Proceeds are generally free of income tax and CGT. "
            "However, may be subject to Capital Acquisitions Tax (CAT) "
            "at 33% above thresholds unless written in trust / under Section 72 policy."
        ),
        "note": note,
        "types": [
            {
                "name": "Mortgage Protection",
                "description": "Decreasing cover matching mortgage balance. Required by lenders.",
            },
            {
                "name": "Term Life",
                "description": "Fixed cover for a set period (e.g. until children are 18/23).",
            },
            {
                "name": "Whole of Life",
                "description": "Pays on death whenever it occurs. More expensive. Often used for inheritance tax planning.",
            },
        ],
        "key_considerations": [
            "Section 72 policies: proceeds used to pay inheritance tax are exempt from CAT.",
            "Group life cover through employer (often 2-4x salary) may reduce private need.",
            "Smoker/non-smoker rates differ significantly in Ireland.",
            "Consider writing policy in trust to avoid CAT on proceeds.",
        ],
    }
