"""
US FICA and Medicare contribution estimates.

Covers W-2 (employee share) and self-employed (both shares).
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules


def estimate_fica(gross: float, year: int, filing_status: str = "single") -> dict:
    """
    Estimate FICA + Medicare for a W-2 employee (employee share only).
    For self-employed, both employee + employer shares apply — use estimate_self_employment_tax().
    """
    rules = get_tax_year_rules(year)
    fica = rules["fica"]

    ss = min(gross, fica["social_security_wage_base"]) * fica["social_security_rate"]
    medicare = gross * fica["medicare_rate"]
    _threshold_key = {
        "married_filing_jointly": "additional_medicare_threshold_mfj",
        "married_filing_separately": "additional_medicare_threshold_mfs",
    }.get(filing_status, "additional_medicare_threshold_single")
    add_medicare_threshold = fica.get(_threshold_key, 200_000)
    if gross > add_medicare_threshold:
        medicare += (gross - add_medicare_threshold) * fica["additional_medicare_rate"]

    return {
        "social_security": round(ss, 2),
        "medicare": round(medicare, 2),
        "total_employee": round(ss + medicare, 2),
        "employer_match": round(ss + gross * fica["medicare_rate"], 2),
        "wage_base": fica["social_security_wage_base"],
        "filing_status": filing_status,
        "year": year,
    }


def estimate_self_employment_tax(net_profit: float, year: int, filing_status: str = "single") -> dict:
    """
    Self-employment tax = both employee + employer FICA shares (15.3% up to wage base).
    The deductible half reduces AGI.
    """
    rules = get_tax_year_rules(year)
    fica = rules["fica"]

    # SE tax base = 92.35% of net profit (accounts for employer deduction)
    se_base = net_profit * 0.9235
    ss = min(se_base, fica["social_security_wage_base"]) * fica["social_security_rate"] * 2
    medicare = se_base * fica["medicare_rate"] * 2
    # Additional Medicare Tax (0.9%) on SE income over the threshold
    _threshold_key = {
        "married_filing_jointly": "additional_medicare_threshold_mfj",
        "married_filing_separately": "additional_medicare_threshold_mfs",
    }.get(filing_status, "additional_medicare_threshold_single")
    add_medicare_threshold = fica.get(_threshold_key, 200_000)
    if se_base > add_medicare_threshold:
        medicare += (se_base - add_medicare_threshold) * fica["additional_medicare_rate"]

    se_tax = ss + medicare
    deductible_half = se_tax / 2

    return {
        "net_profit": round(net_profit, 2),
        "se_base": round(se_base, 2),
        "social_security_tax": round(ss, 2),
        "medicare_tax": round(medicare, 2),
        "total_se_tax": round(se_tax, 2),
        "deductible_half": round(deductible_half, 2),
        "filing_status": filing_status,
        "year": year,
    }
