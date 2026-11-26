"""
Canadian Income Tax Calculator.

Calculates federal income tax, provincial/territorial income tax, social contributions
(CPP/QPP and EI), and net take-home pay for Canadian residents across all 10 provinces
and 3 territories for tax years 2024, 2025, and 2026.

Features:
- Complete province-awareness (AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT)
- Federal & provincial graduated tax brackets
- Federal BPA with high-income taper ($173k - $246k in 2024, indexed 2025-2026)
- Provincial basic personal amount and non-refundable tax credits
- Canada Employment Amount (CEA) tax credit
- CPP/QPP and EI tax credits (plus enhanced CPP/CPP2 deduction)
- Ontario Surtax (20% above $5,554/$5,710/$5,818 and 36% above $7,108/$7,307/$7,446)
- Ontario Health Premium (OHP graduated scale)
- BC Tax Reduction (for modest income earners)
- Quebec Federal Abatement (16.5% reduction on basic federal tax for QC residents)
- Comprehensive marginal and effective tax rates

Sources:
  Income Tax Act (R.S.C., 1985, c. 1 (5th Supp.))
  CRA Publication T4127 - Payroll Deductions Formulas
  CRA Form 5000-S1 (Federal Tax) and provincial forms (ON428, BC428, AB428, etc.)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .tax_rules import (
    get_tax_year_rules,
    normalize_province,
    resolve_supported_year,
    PROVINCE_CODES,
)
from .social_contributions import calculate_social_contributions

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def _apply_brackets(taxable_income: float, brackets: list[dict]) -> tuple[float, float]:
    """
    Calculate progressive tax liability across brackets.

    Returns:
        (total_tax, marginal_rate)
    """
    if taxable_income <= 0:
        return 0.0, brackets[0]["rate"] if brackets else 0.0

    tax = 0.0
    marginal_rate = brackets[0]["rate"] if brackets else 0.0

    for b in brackets:
        b_from = b["from"]
        b_to = b["to"]
        rate = b["rate"]

        if taxable_income > b_from:
            if b_to is not None:
                taxable_in_band = min(taxable_income, b_to) - b_from
            else:
                taxable_in_band = taxable_income - b_from

            tax += taxable_in_band * rate
            marginal_rate = rate

    return max(0.0, tax), marginal_rate


def _calculate_ontario_health_premium(taxable_income: float) -> float:
    """Calculate Ontario Health Premium (OHP) based on annual taxable income."""
    a = taxable_income
    if a <= 20000.0:
        return 0.0
    elif a <= 36000.0:
        return min(300.0, 0.06 * (a - 20000.0))
    elif a <= 48000.0:
        return min(450.0, 300.0 + (0.06 * (a - 36000.0)))
    elif a <= 72000.0:
        return min(600.0, 450.0 + (0.25 * (a - 48000.0)))
    elif a <= 200000.0:
        return min(750.0, 600.0 + (0.25 * (a - 72000.0)))
    else:
        return min(900.0, 750.0 + (0.25 * (a - 200000.0)))


def calculate_tax(ctx: "LocaleContext | dict", year: int = None) -> dict:
    """
    Calculate full Canadian personal tax liability for the given profile and year.

    Args:
        ctx: LocaleContext or Finance Assistant profile dict.
        year: Tax year override (defaults to ctx.tax_year).

    Returns:
        Dict conforming to repo standards:
          gross, tax, net, effective_rate, marginal_rate, confidence,
          federal_tax, provincial_tax, cpp, ei, province, breakdown
    """
    if isinstance(ctx, dict):
        LocaleContext = _import_locale_context()
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    requested_year = ctx.tax_year or 2024
    resolved_year, year_note = resolve_supported_year(requested_year)
    rules = get_tax_year_rules(resolved_year)

    gross = float(ctx.annual_gross or 0.0)
    side_income = float(ctx.side_income or 0.0)
    total_income = gross + side_income

    province_code = normalize_province(getattr(ctx, "region", None))
    prov_rules = rules["provinces"].get(province_code, rules["provinces"]["ON"])
    province_name = prov_rules.get("name", "Ontario")

    is_self_employed = ctx.employment_type in ("self_employed", "freelancer")

    # ── Deductions from total income ─────────────────────────────────────
    # Standard deductions: RRSP contribution, union dues, child care, etc.
    extra = getattr(ctx, "extra", {}) or {}
    rrsp_deduction = float(extra.get("rrsp_contribution") or 0.0)
    union_dues = float(getattr(ctx, "union_dues", 0.0) or 0.0)
    childcare_deduction = sum(float(ch.childcare_annual_cost or 0.0) for ch in getattr(ctx, "children", []))

    total_deductions = rrsp_deduction + union_dues + childcare_deduction
    taxable_income = max(0.0, total_income - total_deductions)

    # ── Social contributions ──────────────────────────────────────────────
    social = calculate_social_contributions(gross, resolved_year, province=province_code, self_employed=is_self_employed)
    cpp_employee = social["cpp_employee"] + social["cpp2_employee"]
    ei_employee = social["ei_employee"]
    qpip_employee = social.get("qpip_employee", 0.0)

    # ── 1. Federal Tax Calculation ────────────────────────────────────────
    fed_brackets = rules["federal_brackets"]
    raw_fed_tax, fed_marginal = _apply_brackets(taxable_income, fed_brackets)

    # Federal Non-Refundable Tax Credits (NRTCs)
    # Basic personal amount with taper
    bpa_max = rules["federal_bpa_max"]
    bpa_min = rules["federal_bpa_min"]
    taper_start = rules["federal_bpa_taper_start"]
    taper_end = rules["federal_bpa_taper_end"]

    if total_income <= taper_start:
        fed_bpa = bpa_max
    elif total_income >= taper_end:
        fed_bpa = bpa_min
    else:
        fraction = (total_income - taper_start) / (taper_end - taper_start)
        fed_bpa = bpa_max - (fraction * (bpa_max - bpa_min))

    # Canada Employment Amount (CEA)
    cea_amount = min(gross, rules.get("canada_employment_amount_max", 1433.0)) if not is_self_employed else 0.0

    # CPP and EI tax credits (base CPP rate 4.95% portion is eligible for NRTC)
    base_cpp_contrib = social["cpp_employee"]
    if not is_self_employed:
        # Base employee contribution is 4.95/5.95 of the total CPP contribution
        cpp_nrtc_base = min(base_cpp_contrib * (0.0495 / 0.0595), base_cpp_contrib)
    else:
        cpp_nrtc_base = min((base_cpp_contrib / 2.0) * (0.0495 / 0.0595), base_cpp_contrib / 2.0)

    fed_nrtc_base = fed_bpa + cea_amount + cpp_nrtc_base + ei_employee
    fed_nrtc_rate = rules["federal_nrtc_rate"]
    fed_nrtc = fed_nrtc_base * fed_nrtc_rate

    basic_fed_tax = max(0.0, raw_fed_tax - fed_nrtc)

    # Quebec Abatement: 16.5% of basic federal tax for Quebec residents
    if province_code == "QC":
        abatement = basic_fed_tax * prov_rules.get("federal_abatement_rate", 0.165)
        fed_tax = max(0.0, basic_fed_tax - abatement)
    else:
        abatement = 0.0
        fed_tax = basic_fed_tax

    # ── 2. Provincial Tax Calculation ─────────────────────────────────────
    prov_brackets = prov_rules["brackets"]
    raw_prov_tax, prov_marginal = _apply_brackets(taxable_income, prov_brackets)

    prov_bpa = prov_rules.get("bpa", 12399.0)
    prov_nrtc_rate = prov_rules.get("nrtc_rate", 0.0505)

    # Provincial NRTC base
    prov_nrtc_base = prov_bpa + cpp_nrtc_base + ei_employee
    prov_nrtc = prov_nrtc_base * prov_nrtc_rate

    basic_prov_tax = max(0.0, raw_prov_tax - prov_nrtc)

    # Special Provincial Features:
    # A. Ontario: Surtax & Health Premium & Tax Reduction
    on_surtax = 0.0
    on_health_premium = 0.0
    prov_tax_reduction = 0.0

    if province_code == "ON":
        surtax_cfg = prov_rules.get("surtax", {})
        t1 = surtax_cfg.get("threshold_1", 5554.0)
        r1 = surtax_cfg.get("rate_1", 0.20)
        t2 = surtax_cfg.get("threshold_2", 7108.0)
        r2 = surtax_cfg.get("rate_2", 0.36)

        if basic_prov_tax > t2:
            on_surtax = (r1 * (basic_prov_tax - t1)) + (r2 * (basic_prov_tax - t2))
        elif basic_prov_tax > t1:
            on_surtax = r1 * (basic_prov_tax - t1)

        # Ontario Tax Reduction
        basic_red = prov_rules.get("tax_reduction", {}).get("basic", 286.0)
        prov_tax_before_red = basic_prov_tax + on_surtax
        prov_tax_reduction = max(0.0, min(prov_tax_before_red, (2 * basic_red) - prov_tax_before_red))

        # Ontario Health Premium
        on_health_premium = _calculate_ontario_health_premium(taxable_income)
        prov_tax = max(0.0, prov_tax_before_red - prov_tax_reduction) + on_health_premium

    elif province_code == "BC":
        # BC Tax Reduction
        bc_red_cfg = prov_rules.get("tax_reduction", {})
        max_red = bc_red_cfg.get("max_reduction", 547.0)
        p_start = bc_red_cfg.get("phase_out_start", 24230.0)
        p_rate = bc_red_cfg.get("phase_out_rate", 0.0356)

        if taxable_income <= p_start:
            bc_red = min(basic_prov_tax, max_red)
        else:
            bc_red = max(0.0, min(basic_prov_tax, max_red - ((taxable_income - p_start) * p_rate)))
        prov_tax_reduction = bc_red
        prov_tax = max(0.0, basic_prov_tax - prov_tax_reduction)

    else:
        prov_tax = basic_prov_tax

    # ── Totals, Effective Rate & Marginal Rate ────────────────────────────
    total_tax = round(fed_tax + prov_tax, 2)
    total_employee_deductions = total_tax + cpp_employee + ei_employee + qpip_employee
    net_income = round(gross - total_employee_deductions, 2)

    effective_rate = round(total_tax / gross, 4) if gross > 0 else 0.0

    # Combined marginal rate
    # Check if ON surtax or phase-outs apply at the margin
    combined_marginal = fed_marginal + prov_marginal
    if province_code == "ON" and basic_prov_tax > prov_rules.get("surtax", {}).get("threshold_2", 7108.0):
        # 56% surtax on provincial marginal rate
        combined_marginal = fed_marginal + (prov_marginal * 1.56)
    elif province_code == "ON" and basic_prov_tax > prov_rules.get("surtax", {}).get("threshold_1", 5554.0):
        combined_marginal = fed_marginal + (prov_marginal * 1.20)
    elif province_code == "QC":
        combined_marginal = (fed_marginal * (1.0 - 0.165)) + prov_marginal

    combined_marginal = round(combined_marginal, 4)

    # Confidence scoring
    if year_note:
        confidence = "Likely"
    else:
        confidence = rules.get("confidence", "Definitive")

    return {
        "gross": round(gross, 2),
        "taxable_income": round(taxable_income, 2),
        "tax": total_tax,
        "federal_tax": round(fed_tax, 2),
        "provincial_tax": round(prov_tax, 2),
        "soli": 0.0,  # Required by standard cross-locale contract (0.0 when not applicable)
        "net": net_income,
        "effective_rate": effective_rate,
        "marginal_rate": combined_marginal,
        "confidence": confidence,
        "province": province_code,
        "province_name": province_name,
        "cpp_employee": cpp_employee,
        "ei_employee": ei_employee,
        "qpip_employee": qpip_employee,
        "breakdown": {
            "gross_income": round(gross, 2),
            "deductions": round(total_deductions, 2),
            "taxable_income": round(taxable_income, 2),
            "federal_tax_gross": round(raw_fed_tax, 2),
            "federal_nrtc": round(fed_nrtc, 2),
            "federal_abatement": round(abatement, 2),
            "federal_tax_net": round(fed_tax, 2),
            "provincial_tax_gross": round(raw_prov_tax, 2),
            "provincial_nrtc": round(prov_nrtc, 2),
            "ontario_surtax": round(on_surtax, 2),
            "ontario_health_premium": round(on_health_premium, 2),
            "provincial_tax_reduction": round(prov_tax_reduction, 2),
            "provincial_tax_net": round(prov_tax, 2),
            "cpp_employee": cpp_employee,
            "ei_employee": ei_employee,
            "qpip_employee": qpip_employee,
            "total_tax_and_contributions": round(total_employee_deductions, 2),
        },
    }
