"""
French income tax rules for Finance Assistant.

Income tax (Impôt sur le Revenu, IR) uses a quotient familial (family
quotient) system. Net taxable income (after the 10% abattement forfaitaire
for salaried workers) is divided by the number of "parts" to find the
income per part; the progressive schedule is applied to that slice; the
result is then multiplied back by the number of parts.

Prélèvements sociaux (CSG 9.2% + CRDS 0.5%) are collected alongside IR
but are technically separate levies — they are calculated on gross income
and noted in the output.

Sources:
  https://www.impots.gouv.fr/particulier/le-bareme-de-limpot
  https://www.impots.gouv.fr/particulier/le-quotient-familial
  https://www.service-public.fr/particuliers/vosdroits/F2971
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        # ── Brackets applied to (net_income / parts) ─────────────────────
        "brackets": [
            {"rate": 0.00, "from": 0,       "to": 11_294},
            {"rate": 0.11, "from": 11_295,   "to": 28_797},
            {"rate": 0.30, "from": 28_798,   "to": 82_341},
            {"rate": 0.41, "from": 82_342,   "to": 177_106},
            {"rate": 0.45, "from": 177_107,  "to": None},
        ],
        # ── Abattement forfaitaire pour frais professionnels ──────────────
        "abattement_pct": 0.10,
        "abattement_max": 4_321,    # annual cap (§ 83 CGI)
        "abattement_min": 495,      # annual floor
        # ── Micro-entrepreneur abattements ────────────────────────────────
        "micro_bic_abattement": 0.50,   # commerce / hébergement
        "micro_bnc_abattement": 0.34,   # services / professions libérales
        # ── Plafonnement du quotient familial ─────────────────────────────
        # Benefit of each extra half-part is capped at this amount of tax reduction
        "plafond_demi_part": 1_759,     # per half-part (2024)
        # ── Décote (low-income tax reduction) ────────────────────────────
        "decote_ceiling_single": 1_929,  # gross tax ceiling to qualify (single)
        "decote_ceiling_couple": 3_191,  # gross tax ceiling to qualify (couple)
        "decote_factor": 0.4525,         # décote = ceiling × 0.4525 − tax × 0.4525
        # ── Prélèvements sociaux on salaried income ───────────────────────
        "csg_rate": 0.092,              # total CSG — split below
        "csg_deductible_rate": 0.068,   # deductible from IR base
        "csg_non_deductible_rate": 0.024,
        "crds_rate": 0.005,
        # ── Plafond Annuel de la Sécurité Sociale (PASS) ─────────────────
        "pass": 46_368,
        "confidence": "Definitive",
    },
    2025: {
        # Indexed ~+1.8% on 2024 brackets per government announcement
        "brackets": [
            {"rate": 0.00, "from": 0,       "to": 11_497},
            {"rate": 0.11, "from": 11_498,   "to": 29_315},
            {"rate": 0.30, "from": 29_316,   "to": 83_823},
            {"rate": 0.41, "from": 83_824,   "to": 180_294},
            {"rate": 0.45, "from": 180_295,  "to": None},
        ],
        "abattement_pct": 0.10,
        "abattement_max": 4_399,    # estimated +1.8%
        "abattement_min": 504,
        "micro_bic_abattement": 0.50,
        "micro_bnc_abattement": 0.34,
        "plafond_demi_part": 1_791,     # estimated +1.8%
        "decote_ceiling_single": 1_963,
        "decote_ceiling_couple": 3_249,
        "decote_factor": 0.4525,
        "csg_rate": 0.092,
        "csg_deductible_rate": 0.068,
        "csg_non_deductible_rate": 0.024,
        "crds_rate": 0.005,
        "pass": 47_100,             # estimated
        "confidence": "Likely",
    },
    2026: {
        # Indexed ~+1.5% on 2025 brackets — estimate
        "brackets": [
            {"rate": 0.00, "from": 0,       "to": 11_670},
            {"rate": 0.11, "from": 11_671,   "to": 29_755},
            {"rate": 0.30, "from": 29_756,   "to": 85_080},
            {"rate": 0.41, "from": 85_081,   "to": 183_000},
            {"rate": 0.45, "from": 183_001,  "to": None},
        ],
        "abattement_pct": 0.10,
        "abattement_max": 4_465,    # estimated +1.5%
        "abattement_min": 512,
        "micro_bic_abattement": 0.50,
        "micro_bnc_abattement": 0.34,
        "plafond_demi_part": 1_818,     # estimated +1.5%
        "decote_ceiling_single": 1_992,
        "decote_ceiling_couple": 3_298,
        "decote_factor": 0.4525,
        "csg_rate": 0.092,
        "csg_deductible_rate": 0.068,
        "csg_non_deductible_rate": 0.024,
        "crds_rate": 0.005,
        "pass": 47_800,             # estimated
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


def calculate_parts(married: bool, children: int) -> float:
    """
    Compute the number of family quotient parts.

    Rules:
      - 1 part per adult (single = 1, married/PACS = 2)
      - First two children: +0.5 part each
      - From the 3rd child onwards: +1 part each
    """
    parts = 2.0 if married else 1.0
    for i in range(children):
        if i < 2:
            parts += 0.5
        else:
            parts += 1.0
    return parts


def apply_brackets(income_per_part: float, brackets: list[dict]) -> float:
    """Apply progressive brackets to income_per_part → tax per part."""
    tax = 0.0
    for bracket in brackets:
        floor = bracket["from"]
        ceiling = bracket["to"]
        rate = bracket["rate"]
        if income_per_part <= floor:
            break
        taxable_in_bracket = (
            income_per_part - floor
            if ceiling is None
            else min(income_per_part, ceiling) - floor
        )
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
    return tax


def calculate_income_tax(net_income: float, parts: float, year: int) -> float:
    """
    Calculate raw IR (before décote, after plafonnement du quotient familial).

    The function applies the bracket schedule to (net_income / parts),
    multiplies back by parts, then enforces the plafonnement du quotient
    familial cap compared to the single-person calculation.
    """
    rules = get_tax_year_rules(year)
    brackets = rules["brackets"]

    # Tax for the actual number of parts
    income_per_part = net_income / parts
    tax_per_part = apply_brackets(income_per_part, brackets)
    raw_tax = tax_per_part * parts

    # Tax for a single person (1 part) to compute the plafonnement
    tax_single_person = apply_brackets(net_income, brackets)

    # The benefit from extra parts must not exceed plafond_demi_part × extra_half_parts
    extra_half_parts = (parts - 1.0) * 2  # each extra half-part
    max_benefit = rules["plafond_demi_part"] * extra_half_parts
    if (tax_single_person - raw_tax) > max_benefit:
        raw_tax = tax_single_person - max_benefit

    return max(0.0, raw_tax)


def apply_decote(raw_tax: float, married: bool, year: int) -> float:
    """
    Apply the décote (low-income tax reducer).

    For 2024:
      Single: if raw_tax < €1,929 → décote = €873.45 − raw_tax × 0.4525
      Couple: if raw_tax < €3,191 → décote = €1,444.14 − raw_tax × 0.4525
    """
    rules = get_tax_year_rules(year)
    ceiling = rules["decote_ceiling_couple"] if married else rules["decote_ceiling_single"]
    factor = rules["decote_factor"]
    if raw_tax >= ceiling:
        return raw_tax
    decote_amount = ceiling * factor - raw_tax * factor
    return max(0.0, raw_tax - decote_amount)


def calculate_marginal_rate(net_income: float, brackets: list[dict]) -> float:
    """Return the marginal bracket rate for net_income."""
    for bracket in reversed(brackets):
        if net_income > bracket["from"]:
            return bracket["rate"]
    return 0.0
