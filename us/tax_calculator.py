"""
US federal income tax calculator.

Computes estimated federal tax liability / refund for W-2 and self-employed filers.
Does NOT cover state taxes — that's a separate locale concern.

Self-employed additions (§199A QBI, SE tax, quarterly deadlines) implemented below.
TODO: itemized deductions (currently always uses standard), AMT
"""

from __future__ import annotations

from .tax_rules import get_tax_year_rules


def _apply_brackets(taxable: float, brackets: list[tuple]) -> float:
    tax = 0.0
    for rate, low, high in brackets:
        if taxable <= low:
            break
        ceiling = high if high is not None else taxable
        tax += rate * (min(taxable, ceiling) - low)
    return tax


def calculate_liability(ctx) -> dict:
    """
    Calculate federal income tax liability and estimated refund.

    ctx: LocaleContext or dict with keys:
      - employment.annual_gross (float)
      - tax_profile.filing_status: "single" | "married_filing_jointly" | "head_of_household"
      - tax_profile.tax_year (int, defaults to current year)
      - tax_profile.extra.withheld_federal (float, optional — federal income tax withheld only,
          i.e. W-2 Box 2. Do NOT include Social Security or Medicare withholding here.)
      - tax_profile.extra.pretax_401k (float, optional)
      - tax_profile.extra.pretax_hsa (float, optional)
      - tax_profile.extra.other_pretax (float, optional)
    """
    from datetime import date

    # Resolve inputs from ctx. Accept both a LocaleContext (the main skill path,
    # built by LocaleContext.from_finance_profile) and a plain dict (standalone
    # callers / tests).
    if hasattr(ctx, "annual_gross"):  # LocaleContext
        gross = float(getattr(ctx, "annual_gross", 0) or 0)
        extra = getattr(ctx, "extra", {}) or {}
        # filing_status isn't a first-class LocaleContext field — prefer an
        # explicit value carried in extra, else derive from marital status.
        filing_status = extra.get("filing_status") or (
            "married_filing_jointly" if getattr(ctx, "married", False) else "single"
        )
        year = getattr(ctx, "tax_year", None) or date.today().year
        employment_type = getattr(ctx, "employment_type", "employed") or "employed"
        side_income = float(getattr(ctx, "side_income", 0) or 0)
    else:
        emp = ctx.get("employment", {}) or {}
        tp = ctx.get("tax_profile", {}) or {}
        gross = float(emp.get("annual_gross", 0) or 0)
        filing_status = tp.get("filing_status", "single") or "single"
        year = tp.get("tax_year") or date.today().year
        extra = tp.get("extra", {}) or {}
        employment_type = emp.get("type", "employed") or "employed"
        side_income = float(emp.get("side_income", 0) or 0)

    rules = get_tax_year_rules(year)
    is_self_employed = employment_type in ("self_employed", "freelancer", "self-employed")

    # Split income into W-2 wages vs self-employment net profit.
    #   self-employed: the whole gross is SE net profit (+ any side income)
    #   employed:      gross is W-2 wages; side_income (if any) is SE
    if is_self_employed:
        w2_wages = 0.0
        se_profit = gross + side_income
    else:
        w2_wages = gross
        se_profit = side_income

    # ── Self-employment tax (both FICA halves) + ½ above-the-line deduction ──
    se = None
    se_tax = 0.0
    se_deductible_half = 0.0
    if se_profit > 0:
        se = calculate_self_employment_tax(se_profit, year, filing_status)
        se_tax = se["total_se_tax"]
        se_deductible_half = se["deductible_half"]

    # Pre-tax deductions
    pretax_401k = float(extra.get("pretax_401k", 0) or 0)
    pretax_hsa = float(extra.get("pretax_hsa", 0) or 0)
    other_pretax = float(extra.get("other_pretax", 0) or 0)

    # AGI = all income − pretax − ½ SE tax (above the line)
    agi = (w2_wages + se_profit) - pretax_401k - pretax_hsa - other_pretax - se_deductible_half

    # Standard deduction (itemized not yet implemented)
    std_deduction = rules["standard_deduction"].get(filing_status, rules["standard_deduction"]["single"])
    taxable_before_qbi = max(0.0, agi - std_deduction)

    # ── §199A QBI deduction (20% of pass-through profit, capped) ──
    qbi = None
    qbi_deduction = 0.0
    if se_profit > 0:
        qbi = calculate_qbi_deduction(se_profit, taxable_before_qbi, filing_status, year=year)
        qbi_deduction = qbi["qbi_deduction"]

    taxable_income = max(0.0, taxable_before_qbi - qbi_deduction)

    # Federal income tax
    bracket_key = filing_status if filing_status in rules["brackets"] else "single"
    federal_tax = _apply_brackets(taxable_income, rules["brackets"][bracket_key])

    # FICA — W-2 employee share only (SE income is covered by SE tax above)
    fica = rules["fica"]
    ss_tax = min(w2_wages, fica["social_security_wage_base"]) * fica["social_security_rate"]
    medicare_tax = w2_wages * fica["medicare_rate"]
    _threshold_key = {
        "married_filing_jointly": "additional_medicare_threshold_mfj",
        "married_filing_separately": "additional_medicare_threshold_mfs",
    }.get(filing_status, "additional_medicare_threshold_single")
    add_medicare_threshold = fica.get(_threshold_key, 200_000)
    if w2_wages > add_medicare_threshold:
        medicare_tax += (w2_wages - add_medicare_threshold) * fica["additional_medicare_rate"]

    total_tax = federal_tax + ss_tax + medicare_tax + se_tax
    withheld = float(extra.get("withheld_federal") or extra.get("withheld") or 0)
    # withheld_federal = W-2 Box 2 only (federal income tax). FICA withheld separately.
    refund = withheld - federal_tax

    effective_rate = (federal_tax / gross) if gross > 0 else 0.0

    result = {
        "year": year,
        "gross_income": gross,
        "agi": round(agi, 2),
        "standard_deduction": std_deduction,
        "taxable_income": round(taxable_income, 2),
        "federal_income_tax": round(federal_tax, 2),
        "social_security_tax": round(ss_tax, 2),
        "medicare_tax": round(medicare_tax, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 4),
        "withheld": withheld,
        "estimated_refund": round(refund, 2) if withheld else None,
        "filing_status": filing_status,
        "currency": "USD",
        "note": "Federal only. State taxes not included. Itemized deductions not yet supported.",
    }
    # Self-employment detail — only present for self-employed / side-income filers
    if se_profit > 0:
        result["employment_type"] = employment_type
        result["self_employment_net_profit"] = round(se_profit, 2)
        result["self_employment_tax"] = round(se_tax, 2)
        result["self_employment_tax_deductible_half"] = round(se_deductible_half, 2)
        result["qbi_deduction"] = round(qbi_deduction, 2)
        result["note"] += " Includes self-employment tax (Schedule SE) and §199A QBI deduction."
    return result


def calculate_self_employment_tax(
    net_se_income: float,
    year: int = 2024,
    filing_status: str = "single",
) -> dict:
    """
    Calculate self-employment (SE) tax for 1099/freelance/sole-proprietor filers.

    SE tax combines both the employee and employer FICA halves (15.3% up to the SS
    wage base, then 2.9% Medicare on amounts above). SE tax is applied to 92.35% of
    net SE income — the 7.65% reduction represents the notional "employer" share.

    The deductible_half (50% of SS + Medicare components) is an above-the-line
    deduction from gross income on Form 1040, reducing AGI before income tax.
    Additional Medicare tax (0.9%) is NOT deductible.

    Sources:
      IRS Schedule SE, IRS Publication 334
      2024 SS wage base: $168,600 (IRS Rev. Proc. 2023-34)
      2025 SS wage base: $176,100 (IRS Rev. Proc. 2024-40)

    Args:
        net_se_income: Net profit from self-employment after business expenses
        year: Tax year (2024 or 2025)
        filing_status: Used for the Additional Medicare Tax threshold

    Returns:
        net_se_earnings: 92.35% of net_se_income (taxable base)
        social_security_tax: 12.4% on earnings ≤ SS wage base
        medicare_tax: 2.9% on all net SE earnings
        additional_medicare_tax: 0.9% on earnings above threshold
        total_se_tax: sum of all SE tax components
        deductible_half: above-the-line deduction (half of SS + Medicare only)
        currency: "USD"
    """
    rules = get_tax_year_rules(year)
    fica = rules["fica"]

    # 92.35% factor: IRS SE calculation multiplier (= 1 - 0.0765)
    net_se_earnings = net_se_income * 0.9235

    # Social Security: 12.4% (both halves) up to wage base
    ss_earnings = min(net_se_earnings, fica["social_security_wage_base"])
    ss_tax = ss_earnings * (fica["social_security_rate"] * 2)

    # Medicare: 2.9% (both halves) on all SE earnings
    medicare_tax = net_se_earnings * (fica["medicare_rate"] * 2)

    # Additional Medicare: 0.9% on SE earnings above threshold
    _threshold_key = {
        "married_filing_jointly": "additional_medicare_threshold_mfj",
        "married_filing_separately": "additional_medicare_threshold_mfs",
    }.get(filing_status, "additional_medicare_threshold_single")
    add_threshold = fica.get(_threshold_key, 200_000)
    add_medicare = max(0.0, net_se_earnings - add_threshold) * fica["additional_medicare_rate"]

    total_se_tax = ss_tax + medicare_tax + add_medicare
    # Only the SS + Medicare halves are deductible; Additional Medicare is not
    deductible_half = (ss_tax + medicare_tax) / 2

    return {
        "net_se_earnings": round(net_se_earnings, 2),
        "social_security_tax": round(ss_tax, 2),
        "medicare_tax": round(medicare_tax, 2),
        "additional_medicare_tax": round(add_medicare, 2),
        "total_se_tax": round(total_se_tax, 2),
        "deductible_half": round(deductible_half, 2),
        "currency": "USD",
    }


def calculate_qbi_deduction(
    qbi: float,
    taxable_income_before_qbi: float,
    filing_status: str = "single",
    year: int = 2024,
    is_sstb: bool = False,
) -> dict:
    """
    Estimate the §199A Qualified Business Income (QBI) deduction.

    The deduction is 20% of QBI, subject to:
      1. The taxable income cap: cannot exceed 20% of taxable income
         (computed before the QBI deduction itself)
      2. A phase-out for Specified Service Trades or Businesses (SSTBs —
         consultants, lawyers, accountants, financial advisors, etc.) when
         taxable income exceeds the threshold.

    W-2 wages / UBIA limitation (for high-income non-SSTBs) is NOT implemented
    here — it requires payroll records. Mark such cases in the note field.

    Sources:
      IRS §199A, IRS Form 8995-A instructions
      2024 thresholds: $182,050 single / $364,100 MFJ (IRS Rev. Proc. 2023-34)
      2025 thresholds: $197,300 single / $394,600 MFJ (IRS Rev. Proc. 2024-40)

    Args:
        qbi: Qualified Business Income (net profit from pass-through business)
        taxable_income_before_qbi: Taxable income BEFORE applying the QBI deduction
        filing_status: "single" | "married_filing_jointly"
        year: Tax year (2024 or 2025)
        is_sstb: True for specified service trades or businesses

    Returns:
        qbi_deduction: The allowed §199A deduction amount
        tentative_deduction: 20% of QBI before limits
        taxable_income_cap: 20% of taxable_income_before_qbi
        phase_out_reduction: Amount reduced by phase-out (SSTBs only)
        note: Explanation of any limitations applied
        currency: "USD"
    """
    rules = get_tax_year_rules(year)
    qbi_rules = rules.get("qbi", {})

    rate = qbi_rules.get("rate", 0.20)
    if filing_status == "married_filing_jointly":
        threshold = qbi_rules.get("threshold_mfj", 364_100)
        phase_out_range = qbi_rules.get("phase_out_range_mfj", 100_000)
    else:
        threshold = qbi_rules.get("threshold_single", 182_050)
        phase_out_range = qbi_rules.get("phase_out_range_single", 50_000)

    tentative = qbi * rate
    taxable_cap = taxable_income_before_qbi * rate  # 20% of taxable income ceiling

    # Phase-out for SSTBs above threshold
    phase_out_reduction = 0.0
    note_parts = []
    if is_sstb and taxable_income_before_qbi > threshold:
        if taxable_income_before_qbi >= threshold + phase_out_range:
            # Fully phased out
            deduction = 0.0
            note_parts.append(
                "SSTB deduction fully phased out: taxable income exceeds phase-out range."
            )
        else:
            # Partial phase-out
            excess = taxable_income_before_qbi - threshold
            reduction_pct = excess / phase_out_range
            phase_out_reduction = tentative * reduction_pct
            deduction = min(tentative - phase_out_reduction, taxable_cap)
            note_parts.append(
                f"SSTB partial phase-out applied ({reduction_pct:.0%} reduction)."
            )
    else:
        deduction = min(tentative, taxable_cap)

    deduction = max(0.0, deduction)

    if taxable_income_before_qbi > threshold and not is_sstb:
        note_parts.append(
            "W-2 wages / UBIA limitation may apply for non-SSTBs above the threshold — "
            "consult a tax professional or Form 8995-A."
        )

    if not note_parts:
        note_parts.append("Standard 20% QBI deduction, below phase-out threshold.")

    return {
        "qbi_deduction": round(deduction, 2),
        "tentative_deduction": round(tentative, 2),
        "taxable_income_cap": round(taxable_cap, 2),
        "phase_out_reduction": round(phase_out_reduction, 2),
        "note": " ".join(note_parts),
        "currency": "USD",
    }


def get_quarterly_deadlines(year: int = 2024) -> list[dict]:
    """
    Return IRS estimated tax payment deadlines for the given year.

    Quarterly estimated taxes are due in April, June, September of the
    filing year, and January of the following year (Form 1040-ES).

    Due dates are adjusted for weekends/holidays per IRS rules.

    Sources:
      IRS Publication 505, IRS Form 1040-ES instructions
      2024 dates: Rev. Proc. 2023-34 calendar adjustments
      2025 dates: Rev. Proc. 2024-40 calendar adjustments

    Args:
        year: The tax year for which to return estimated payment deadlines

    Returns:
        List of dicts: [{"quarter": int, "period": str, "due": "YYYY-MM-DD"}, ...]
    """
    rules = get_tax_year_rules(year)
    return rules.get("quarterly_deadlines", [])
