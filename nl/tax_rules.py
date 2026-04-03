"""
Dutch income tax rules for Finance Assistant.

The Dutch system divides income into three Boxes:
  Box 1 — income from work and home (salary, self-employment, owner-occupied home)
  Box 2 — substantial shareholding (≥5% in a BV) — dividends and capital gains
  Box 3 — savings and investments — taxed on a deemed (fictitious) return

Box 1 rates include the volksverzekeringen (social insurance premiums): AOW,
ANW, and WLZ. These are embedded in the first bracket rate for those below
AOW-gerechtigde leeftijd (~67).

Box 3 is subject to ongoing legal challenge following the Kerstarrest (HR
24-12-2021). Since 2023 the Belastingdienst uses a fixed deemed-return
method; final resolution and potential refunds for earlier years are pending.

Sources:
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/inkomstenbelasting/heffingen_op_uw_inkomen_uit_werk_en_woning/belastingtarieven_box_1/
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/vermogen_en_aanmerkelijk_belang/vermogen/
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/inkomstenbelasting/heffingskortingen_boxen_1_2_en_3/heffingskortingen/
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        # ── Box 1 ─────────────────────────────────────────────────────────
        # First bracket includes volksverzekeringen (AOW 17.90% + ANW 0.10% + WLZ 9.65% = 27.65%)
        "box1_rate_low": 0.3697,        # 36.97% up to first bracket threshold
        "box1_threshold": 75_518,       # upper bound of first bracket
        "box1_rate_high": 0.4950,       # 49.50% above threshold

        # Social premiums embedded in box1_rate_low
        "aow_rate": 0.1790,
        "anw_rate": 0.0010,
        "wlz_rate": 0.0965,
        "volksverzekeringen_rate": 0.2765,  # total embedded in first bracket

        # ── Heffingskortingen (tax credits — reduce tax, not taxable income) ──
        "heffingskorting_base": 3_362,   # algemene heffingskorting
        "heffingskorting_taper_start": 24_814,   # income above which korting phases out
        "heffingskorting_taper_rate": 0.06315,   # reduction per euro above taper_start

        "arbeidskorting_max": 5_532,     # maximum employment credit
        "arbeidskorting_phase_in_end": 10_742,   # income at which max is reached
        "arbeidskorting_taper_start": 39_957,    # income above which it phases out
        "arbeidskorting_taper_rate": 0.06510,    # reduction rate
        "arbeidskorting_phase_in_rate": 0.08231, # phase-in rate below phase_in_end

        # ── Box 2 (substantial shareholding ≥5%) ─────────────────────────
        "box2_rate_low": 0.245,         # 24.5% on first €67,000
        "box2_threshold": 67_000,
        "box2_rate_high": 0.330,        # 33% above €67,000

        # ── Box 3 (savings and investments — deemed return) ───────────────
        # Fictional return rates applied to asset value on 1 January
        "box3_rate": 0.36,              # flat tax rate on deemed return
        "box3_savings_return": 0.0144,  # deemed return on savings (2024 provisional)
        "box3_other_return": 0.0604,    # deemed return on other investments
        "box3_debt_return": -0.0246,    # deemed return on debts (reduces box 3 base)
        "box3_exemption_single": 57_000,    # heffingvrij vermogen per person
        "box3_exemption_partner": 114_000,  # for partners (2× single)
        "box3_confidence": "Debatable",     # legal challenge ongoing

        # ── ZVW (health insurance contribution — employer/employee) ───────
        "zvw_rate_employee": 0.0532,    # inkomensafhankelijke bijdrage ZVW
        "zvw_max_income": 71_628,       # maximum income for ZVW calculation
        "zvw_max_contribution": 3_802,  # annual max

        "currency": "EUR",
        "confidence": "Definitive",
    },
    2025: {
        # First bracket rate reduced to 35.82% (tax portion reduced, premiums unchanged)
        "box1_rate_low": 0.3582,
        "box1_threshold": 76_817,
        "box1_rate_high": 0.4950,

        "aow_rate": 0.1790,
        "anw_rate": 0.0010,
        "wlz_rate": 0.0965,
        "volksverzekeringen_rate": 0.2765,

        "heffingskorting_base": 3_068,
        "heffingskorting_taper_start": 25_268,
        "heffingskorting_taper_rate": 0.06337,

        "arbeidskorting_max": 5_599,
        "arbeidskorting_phase_in_end": 10_882,
        "arbeidskorting_taper_start": 40_552,
        "arbeidskorting_taper_rate": 0.06510,
        "arbeidskorting_phase_in_rate": 0.08231,

        "box2_rate_low": 0.245,
        "box2_threshold": 67_000,
        "box2_rate_high": 0.330,

        "box3_rate": 0.36,
        "box3_savings_return": 0.0147,  # provisional estimate
        "box3_other_return": 0.0560,
        "box3_debt_return": -0.0250,
        "box3_exemption_single": 57_684,  # indexed estimate
        "box3_exemption_partner": 115_368,
        "box3_confidence": "Debatable",

        "zvw_rate_employee": 0.0532,
        "zvw_max_income": 72_709,
        "zvw_max_contribution": 3_868,

        "currency": "EUR",
        "confidence": "Likely",
    },
    2026: {
        # Estimated based on 2024→2025 trend; mark Likely
        "box1_rate_low": 0.3582,        # assumed unchanged (no announced change)
        "box1_threshold": 78_200,       # estimated +1.8%
        "box1_rate_high": 0.4950,

        "aow_rate": 0.1790,
        "anw_rate": 0.0010,
        "wlz_rate": 0.0965,
        "volksverzekeringen_rate": 0.2765,

        "heffingskorting_base": 3_068,  # assumed stable
        "heffingskorting_taper_start": 25_730,
        "heffingskorting_taper_rate": 0.06337,

        "arbeidskorting_max": 5_680,
        "arbeidskorting_phase_in_end": 11_065,
        "arbeidskorting_taper_start": 41_200,
        "arbeidskorting_taper_rate": 0.06510,
        "arbeidskorting_phase_in_rate": 0.08231,

        "box2_rate_low": 0.245,
        "box2_threshold": 67_000,
        "box2_rate_high": 0.330,

        "box3_rate": 0.36,
        "box3_savings_return": 0.0150,
        "box3_other_return": 0.0560,
        "box3_debt_return": -0.0250,
        "box3_exemption_single": 58_500,
        "box3_exemption_partner": 117_000,
        "box3_confidence": "Debatable",

        "zvw_rate_employee": 0.0532,
        "zvw_max_income": 74_000,
        "zvw_max_contribution": 3_937,

        "currency": "EUR",
        "confidence": "Likely",
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


def calculate_heffingskorting(gross: float, rules: dict) -> float:
    """
    Compute the algemene heffingskorting (general tax credit).

    The credit phases out linearly above heffingskorting_taper_start.
    Cannot go below 0.
    """
    base = rules["heffingskorting_base"]
    if gross <= rules["heffingskorting_taper_start"]:
        return float(base)
    reduction = (gross - rules["heffingskorting_taper_start"]) * rules["heffingskorting_taper_rate"]
    return max(0.0, base - reduction)


def calculate_arbeidskorting(gross: float, rules: dict) -> float:
    """
    Compute the arbeidskorting (employment tax credit).

    Phases in from €0 to max up to phase_in_end, then flat, then phases out.
    """
    phase_in_end = rules["arbeidskorting_phase_in_end"]
    taper_start = rules["arbeidskorting_taper_start"]
    max_credit = rules["arbeidskorting_max"]
    phase_in_rate = rules["arbeidskorting_phase_in_rate"]
    taper_rate = rules["arbeidskorting_taper_rate"]

    if gross <= phase_in_end:
        return round(gross * phase_in_rate, 2)
    if gross <= taper_start:
        return float(max_credit)
    reduction = (gross - taper_start) * taper_rate
    return max(0.0, max_credit - reduction)


def calculate_box1_tax(gross: float, rules: dict) -> float:
    """Calculate Box 1 tax before applying heffingskortingen."""
    threshold = rules["box1_threshold"]
    if gross <= threshold:
        return gross * rules["box1_rate_low"]
    low_tax = threshold * rules["box1_rate_low"]
    high_tax = (gross - threshold) * rules["box1_rate_high"]
    return low_tax + high_tax


def calculate_box3_tax(
    savings: float,
    investments: float,
    debts: float,
    partner: bool,
    rules: dict,
) -> float:
    """
    Calculate Box 3 tax on deemed return.

    Assets are valued on 1 January of the tax year. The exemption
    (heffingvrij vermogen) is subtracted before applying deemed returns.

    CAUTION: Box 3 is under legal challenge. Confidence is "Debatable".
    """
    exemption = rules["box3_exemption_partner"] if partner else rules["box3_exemption_single"]
    total_assets = savings + investments
    net_assets = max(0.0, total_assets - debts - exemption)

    if net_assets <= 0:
        return 0.0

    # Allocate in proportion to savings vs other investments
    total_portfolio = total_assets if total_assets > 0 else 1.0
    savings_share = savings / total_portfolio if total_portfolio > 0 else 0.0
    other_share = (investments / total_portfolio) if total_portfolio > 0 else 1.0

    deemed_return = (
        net_assets * savings_share * rules["box3_savings_return"]
        + net_assets * other_share * rules["box3_other_return"]
    )
    return round(max(0.0, deemed_return * rules["box3_rate"]), 2)


def calculate_marginal_rate(gross: float, rules: dict) -> float:
    """Return the Box 1 marginal rate for a given gross income."""
    if gross <= rules["box1_threshold"]:
        return rules["box1_rate_low"]
    return rules["box1_rate_high"]
