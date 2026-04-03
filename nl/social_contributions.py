"""
Dutch social contributions.

The volksverzekeringen (AOW + ANW + WLZ) are embedded in the Box 1 first-bracket
rate. This module separates them out for transparency and also shows the
werknemersverzekeringen (WW, WAO/WIA) that employers pay on top.

ZVW (Zorgverzekeringswet — health insurance income-dependent contribution) is
paid by the employer on behalf of the employee on employment income, up to the
ZVW cap.

IMPORTANT: Do not add the volksverzekeringen to the Box 1 tax separately — they
are already included in box1_rate_low calculated in tax_calculator.py.

Sources:
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/inkomstenbelasting/heffingen_op_uw_inkomen_uit_werk_en_woning/belastingtarieven_box_1/
  https://www.uwv.nl/en/individuals/benefits/ww-unemployment-benefit
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules


def get_social_contributions(gross: float, year: int, self_employed: bool = False) -> dict:
    """
    Return social contribution breakdown for the given gross income and year.

    For employees the volksverzekeringen are embedded in Box 1. This function
    extracts the implied amounts for transparency.

    Keys:
      volksverzekeringen — AOW + ANW + WLZ embedded in Box 1 first bracket
      aow                — state pension premium (employees below AOW age)
      anw                — survivor benefit premium
      wlz                — long-term care premium
      zvw                — health insurance (employer-paid on behalf of employee)
      ww                 — unemployment (employer only)
      wao_wia            — disability (employer only)
      note               — warning that premiums are embedded in Box 1
    """
    rules = get_tax_year_rules(year)
    threshold = rules["box1_threshold"]

    # Volksverzekeringen only apply within the first bracket
    taxable_base = min(gross, threshold)

    aow = round(taxable_base * rules["aow_rate"], 2)
    anw = round(taxable_base * rules["anw_rate"], 2)
    wlz = round(taxable_base * rules["wlz_rate"], 2)
    volksverzekeringen = round(taxable_base * rules["volksverzekeringen_rate"], 2)

    # ZVW — inkomensafhankelijke bijdrage paid by employer
    zvw_base = min(gross, rules["zvw_max_income"])
    zvw = round(zvw_base * rules["zvw_rate_employee"], 2)
    zvw = min(zvw, rules["zvw_max_contribution"])

    # Werknemersverzekeringen (employer only)
    # WW: 2.64% low-risk, 10.45% high-risk sector — use low-risk as default
    ww_base = min(gross, threshold)
    ww_employer = round(ww_base * 0.0264, 2)

    # WAO/WIA: base premium ~6.18% (varies by sector; use average)
    wao_wia_employer = round(ww_base * 0.0618, 2)

    return {
        "note": (
            "Volksverzekeringen (AOW, ANW, WLZ) are embedded in the Box 1 first-bracket "
            "rate. Do not add them again on top of Box 1 tax."
        ),
        "volksverzekeringen": {
            "employee_share": volksverzekeringen,
            "employer_share": 0.0,
            "rate": rules["volksverzekeringen_rate"],
            "annual_max": round(threshold * rules["volksverzekeringen_rate"], 2),
            "embedded_in_box1": True,
        },
        "aow": {
            "employee_share": aow,
            "employer_share": 0.0,
            "rate": rules["aow_rate"],
            "annual_max": round(threshold * rules["aow_rate"], 2),
        },
        "anw": {
            "employee_share": anw,
            "employer_share": 0.0,
            "rate": rules["anw_rate"],
            "annual_max": round(threshold * rules["anw_rate"], 2),
        },
        "wlz": {
            "employee_share": wlz,
            "employer_share": 0.0,
            "rate": rules["wlz_rate"],
            "annual_max": round(threshold * rules["wlz_rate"], 2),
        },
        "zvw": {
            "employee_share": 0.0,       # employer pays on employee's behalf
            "employer_share": zvw,
            "rate": rules["zvw_rate_employee"],
            "annual_max": rules["zvw_max_contribution"],
            "notes": "Paid by employer; shown for informational purposes.",
        },
        "ww": {
            "employee_share": 0.0,
            "employer_share": ww_employer,
            "rate": 0.0264,
            "annual_max": round(threshold * 0.0264, 2),
            "notes": "WW low-risk rate. Employer only.",
        },
        "wao_wia": {
            "employee_share": 0.0,
            "employer_share": wao_wia_employer,
            "rate": 0.0618,
            "annual_max": round(threshold * 0.0618, 2),
            "notes": "WAO/WIA average employer rate. Sector-specific rates may differ.",
        },
        # Top-level helpers used by test suite
        "ni_employee": volksverzekeringen,   # alias for test compatibility
        "ni_employer": round(zvw + ww_employer + wao_wia_employer, 2),
    }
