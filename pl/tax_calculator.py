"""
Polish PIT (podatek dochodowy od osób fizycznych) calculator.

Implements the standard progressive tax scale (skala podatkowa) for salaried
employees under the Polski Ład rules in force since 2022:

  1. Gross income (przychód)
  2. Subtract work cost deductions (koszty uzyskania przychodu)
  3. Subtract employee ZUS contributions from the tax base
  4. Apply brackets:
       income ≤ 30,000 PLN            → tax = 0
       30,001–120,000 PLN             → tax = (income − 30,000) × 12%
       > 120,000 PLN                  → tax = 10,800 + (income − 120,000) × 32%
  5. Apply ulga dla młodych if age < 26 and income ≤ 85,528 PLN
  6. Health insurance (składka zdrowotna): 9% of (gross − ZUS) — paid separately,
     NOT deductible from PIT

Note on self-employed (działalność gospodarcza):
  B2B/sole traders can choose between:
    - Skala podatkowa (same 12%/32% brackets as above)
    - Podatek liniowy (19% flat rate — no tax-free amount, no child reliefs)
    - Ryczałt od przychodów ewidencjonowanych (flat rates on revenue, 2%–17%)
  This calculator handles only the skala podatkowa variant.
  Pass employment_type="self_employed" to receive a "Likely" confidence flag.

Sources:
  https://www.podatki.gov.pl/pit/twoj-e-pit/
  https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU19910800350
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    resolve_supported_year,
    calculate_marginal_rate,
)
from .social_contributions import get_social_contributions

if TYPE_CHECKING:
    from ..context import LocaleContext


def _import_locale_context():
    try:
        from ..context import LocaleContext
    except ImportError:
        from context import LocaleContext  # type: ignore
    return LocaleContext


def calculate_tax(ctx: "LocaleContext | dict", year: int = None) -> dict:
    """
    Calculate Polish PIT (income tax), ZUS contributions, and net pay.

    Args:
        ctx:  LocaleContext or Finance Assistant profile dict.
        year: Override tax year (uses ctx.tax_year if not provided).

    Returns:
        Dict with:
          gross, income_tax, zus_employee, health_insurance, net,
          effective_rate, marginal_rate, currency, confidence,
          tax_year, and a breakdown sub-dict.
    """
    if isinstance(ctx, dict):
        LocaleContext = _import_locale_context()
        if year is not None:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    requested_year = ctx.tax_year
    resolved_year, year_note = resolve_supported_year(requested_year)
    rules = get_tax_year_rules(resolved_year)

    gross = float(ctx.annual_gross or 0.0)
    extra = ctx.extra or {}
    is_self_employed = ctx.employment_type in ("self_employed", "freelancer")
    age = int(extra.get("age", 0) or 0)

    # ── Step 1: Work cost deduction (koszty uzyskania przychodu) ──────────
    # Use elevated amount (3,600) if commuting from outside city
    if ctx.commute_km and float(ctx.commute_km) > 0:
        work_costs = float(rules["pracownicze_koszty_podwyzszone"])
    else:
        work_costs = float(rules["pracownicze_koszty_podstawowe"])

    # ── Step 2: ZUS employee contributions ────────────────────────────────
    zus_data = get_social_contributions(gross, resolved_year)
    zus_employee = zus_data["employee_total"]

    # ── Step 3: Tax base ──────────────────────────────────────────────────
    # Base = gross − work costs − ZUS employee
    tax_base = max(0.0, gross - work_costs - zus_employee)

    # ── Step 4: Apply PIT brackets ────────────────────────────────────────
    tax_free = float(rules["tax_free_amount"])
    bracket_threshold = float(rules["bracket_threshold"])
    rate1 = rules["first_bracket_rate"]
    rate2 = rules["second_bracket_rate"]

    # First bracket tax = 10,800 PLN (120,000 × 12% − 3,600)
    first_bracket_max_tax = (bracket_threshold - tax_free) * rate1  # = 90,000 × 12% = 10,800

    if tax_base <= 0:
        income_tax = 0.0
        marginal = 0.0
    elif tax_base <= tax_free:
        income_tax = 0.0
        marginal = 0.0
    elif tax_base <= bracket_threshold:
        income_tax = (tax_base - tax_free) * rate1
        marginal = rate1
    else:
        income_tax = first_bracket_max_tax + (tax_base - bracket_threshold) * rate2
        marginal = rate2

    income_tax = round(max(0.0, income_tax), 2)

    # ── Step 5: Ulga dla młodych (under-26 exemption) ─────────────────────
    ulga_mlodych_applied = False
    ulga_mlodych_limit = float(rules["ulga_dla_mlodych_limit"])

    if age > 0 and age < 26 and gross <= ulga_mlodych_limit:
        income_tax = 0.0
        ulga_mlodych_applied = True
        marginal = 0.0

    # ── Step 6: Health insurance (składka zdrowotna) ──────────────────────
    health_insurance = zus_data["health_insurance"]

    # ── Step 7: Net pay ────────────────────────────────────────────────────
    net = gross - income_tax - zus_employee - health_insurance
    net = round(net, 2)

    # ── Effective rate ─────────────────────────────────────────────────────
    effective_rate = round(income_tax / gross, 4) if gross > 0 else 0.0

    # ── Confidence ─────────────────────────────────────────────────────────
    if year_note:
        confidence = "Likely"
    elif resolved_year == 2026:
        confidence = "Debatable"
    elif is_self_employed:
        confidence = "Likely"  # B2B/działalność has more complex rules
    else:
        confidence = rules.get("confidence", "Definitive")

    notes = []
    if year_note:
        notes.append(year_note)
    if is_self_employed:
        notes.append(
            "Self-employed (działalność gospodarcza) can choose: skala podatkowa (12%/32%), "
            "podatek liniowy (19% flat, no tax-free amount), or ryczałt (flat rate by activity). "
            "This calculation uses skala podatkowa only — consult a tax adviser for optimal choice."
        )
    if ulga_mlodych_applied:
        notes.append(
            f"Ulga dla młodych applied: income below {ulga_mlodych_limit:,.0f} PLN and age < 26 "
            "— PIT set to zero."
        )

    # ── Joint filing estimate (wspólne rozliczenie z małżonkiem) ──────────
    spouse_gross = float(extra.get("spouse_gross", 0) or 0)
    joint_tax_estimate = None
    if ctx.married and spouse_gross > 0:
        joint_tax_estimate = _calculate_joint_tax(gross, spouse_gross, rules)

    result = {
        "gross": round(gross, 2),
        "income_tax": income_tax,
        "zus_employee": zus_employee,
        "health_insurance": health_insurance,
        "net": net,
        "effective_rate": effective_rate,
        "marginal_rate": marginal,
        "currency": rules["currency"],
        "confidence": confidence,
        "tax_year": resolved_year,
        "year_note": year_note,
        "notes": notes,
        "ulga_mlodych_applied": ulga_mlodych_applied,
        "is_self_employed": is_self_employed,
        "breakdown": {
            "gross": round(gross, 2),
            "work_costs_deduction": round(work_costs, 2),
            "zus_employee": zus_employee,
            "tax_base": round(tax_base, 2),
            "income_tax": income_tax,
            "health_insurance": health_insurance,
            "total_deductions": round(income_tax + zus_employee + health_insurance, 2),
            "net": net,
            # ZUS employer context (not deducted from net — paid by employer separately)
            "employer_zus_note": (
                f"Employer also pays ~{zus_data['employer_total']:,.2f} PLN ZUS on top of gross."
            ),
        },
        "zus_detail": zus_data,
    }

    if joint_tax_estimate is not None:
        result["joint_tax_estimate"] = joint_tax_estimate

    return result


def _calculate_joint_tax(
    gross_a: float, gross_b: float, rules: dict
) -> dict:
    """
    Estimate PIT for joint filing with spouse (wspólne rozliczenie z małżonkiem).

    Income is pooled and halved — each half is taxed using the standard bracket,
    then the result is doubled. This reduces tax when spouses have different incomes.

    Note: Work cost deductions and ZUS are handled individually; this function
    provides an indicative PIT comparison only.
    """
    combined = gross_a + gross_b
    half = combined / 2.0

    tax_free = float(rules["tax_free_amount"])
    bracket_threshold = float(rules["bracket_threshold"])
    rate1 = rules["first_bracket_rate"]
    rate2 = rules["second_bracket_rate"]
    first_bracket_max_tax = (bracket_threshold - tax_free) * rate1

    def _pit_on_half(income: float) -> float:
        if income <= tax_free:
            return 0.0
        if income <= bracket_threshold:
            return (income - tax_free) * rate1
        return first_bracket_max_tax + (income - bracket_threshold) * rate2

    joint_pit = round(max(0.0, _pit_on_half(half) * 2), 2)

    # Individual PIT on gross_a for comparison (no ZUS/work costs deduction here — simplified)
    def _individual_pit(income: float) -> float:
        if income <= tax_free:
            return 0.0
        if income <= bracket_threshold:
            return (income - tax_free) * rate1
        return first_bracket_max_tax + (income - bracket_threshold) * rate2

    individual_pit_a = round(max(0.0, _individual_pit(gross_a)), 2)
    individual_pit_b = round(max(0.0, _individual_pit(gross_b)), 2)
    combined_individual_pit = round(individual_pit_a + individual_pit_b, 2)

    saving = round(max(0.0, combined_individual_pit - joint_pit), 2)

    return {
        "joint_pit": joint_pit,
        "individual_pit_combined": combined_individual_pit,
        "estimated_saving": saving,
        "note": (
            "Simplified joint-filing estimate (wspólne rozliczenie z małżonkiem). "
            "Actual saving depends on individual ZUS deductions and applicable reliefs. "
            "Consult PIT-36 / e-PIT for precise figures."
        ),
    }
