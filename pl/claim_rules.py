"""
Polish PIT deduction and relief discovery.

Generates applicable claims for common Polish PIT reliefs and allowances.
Each claim follows the standard Finance Assistant locale interface:
  id, title, status, amount_estimate, confidence, notes

Sources:
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/ulga-dla-mlodych/
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/ulga-na-dzieci/
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/ulga-na-internet/
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/ulga-rehabilitacyjna/
  https://www.podatki.gov.pl/pit/ulgi-odliczenia-i-zwolnienia/ulga-na-powrot/
  https://www.knf.gov.pl/dla_konsumenta/IKE_i_IKZE
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import get_tax_year_rules

if TYPE_CHECKING:
    from ..context import LocaleContext


def generate_polish_claims(ctx: "LocaleContext | dict", year: int = None) -> list[dict]:
    """
    Discover applicable Polish PIT deduction claims for the given profile and year.

    Args:
        ctx:  LocaleContext or Finance Assistant profile dict.
        year: Override tax year (uses ctx.tax_year if not provided).

    Returns:
        List of claim dicts, sorted ready → needs_input → needs_evidence → detected.
    """
    if isinstance(ctx, dict):
        try:
            from ..context import LocaleContext
        except ImportError:
            from context import LocaleContext  # type: ignore
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)

    if year is None:
        year = ctx.tax_year

    rules = get_tax_year_rules(year)
    gross = float(ctx.annual_gross or 0.0)
    extra = ctx.extra or {}

    age = int(extra.get("age", 0) or 0)
    num_children = len(ctx.children) if ctx.children else int(extra.get("num_children", 0) or 0)
    is_employee = ctx.employment_type in ("employed",)
    commutes = ctx.commute_km and float(ctx.commute_km) > 0

    # For IKZE / internet / disability / ulga_na_powrot — check extra fields
    ikze_contribution = float(extra.get("ikze_contribution", 0) or 0)
    internet_expense = float(extra.get("internet_expense", 0) or 0)
    internet_ulga_year = int(extra.get("internet_ulga_year", 0) or 0)
    disability_grade = int(ctx.disability_grade or extra.get("disability_grade", 0) or 0)
    recently_relocated = bool(extra.get("recently_relocated_to_poland", False))
    donation_receipts = [
        r for r in ctx.receipts
        if (r.category if hasattr(r, "category") else r.get("category")) == "donation"
    ]

    claims = []

    # ── 1. Koszty uzyskania przychodu — always present ────────────────────
    if commutes:
        koszty = float(rules["pracownicze_koszty_podwyzszone"])
        koszty_notes = (
            f"Podwyższone koszty uzyskania przychodu: {koszty:,.0f} PLN "
            "(commuting from outside city of employment). Applied automatically."
        )
    else:
        koszty = float(rules["pracownicze_koszty_podstawowe"])
        koszty_notes = (
            f"Podstawowe koszty uzyskania przychodu: {koszty:,.0f} PLN "
            "(standard annual work-cost deduction for one employer). Applied automatically."
        )

    claims.append(_claim(
        "koszty_uzyskania_przychodu",
        "Koszty uzyskania przychodu (work cost deduction)",
        "ready",
        koszty,
        "Definitive",
        koszty_notes,
    ))

    # ── 2. Ulga dla młodych (under-26 exemption) ──────────────────────────
    ulga_limit = float(rules["ulga_dla_mlodych_limit"])
    if age > 0:
        if age < 26 and gross <= ulga_limit:
            claims.append(_claim(
                "ulga_dla_mlodych",
                "Ulga dla młodych (under-26 PIT exemption)",
                "ready",
                gross,  # Entire income is exempt
                "Definitive",
                f"Dochód poniżej {ulga_limit:,.0f} PLN i wiek poniżej 26 lat "
                "— pełne zwolnienie z PIT. Applied automatically via Twój e-PIT.",
            ))
        elif age < 26 and gross > ulga_limit:
            claims.append(_claim(
                "ulga_dla_mlodych",
                "Ulga dla młodych (under-26 PIT exemption — limit exceeded)",
                "detected",
                ulga_limit,
                "Definitive",
                f"Wiek poniżej 26 lat, ale dochód {gross:,.0f} PLN przekracza limit "
                f"{ulga_limit:,.0f} PLN. Exemption does not apply.",
            ))
    else:
        # Age unknown — flag as needs_input
        claims.append(_claim(
            "ulga_dla_mlodych",
            "Ulga dla młodych (under-26 PIT exemption)",
            "needs_input",
            0.0,
            "Definitive",
            f"PIT is fully exempt for employees under 26 earning up to {ulga_limit:,.0f} PLN. "
            "Provide your age to determine whether this applies.",
        ))

    # ── 3. Ulga na dzieci (child relief) ─────────────────────────────────
    if num_children > 0:
        child_relief = _calculate_child_relief(num_children, rules)
        claims.append(_claim(
            "ulga_na_dzieci",
            f"Ulga na dzieci ({num_children} {'dziecko' if num_children == 1 else 'dzieci'})",
            "ready",
            child_relief,
            "Definitive",
            _child_relief_notes(num_children, rules),
        ))
    else:
        claims.append(_claim(
            "ulga_na_dzieci",
            "Ulga na dzieci (child relief)",
            "needs_input",
            0.0,
            "Definitive",
            "Per-child relief: 1,112.04 PLN (1st and 2nd child), "
            "2,000.04 PLN (3rd child), 2,700.00 PLN (4th+). "
            "Provide number of qualifying children to calculate.",
        ))

    # ── 4. IKZE (individual pension deduction) ────────────────────────────
    ikze_limit = float(rules["ikze_limit"])
    if ikze_contribution > 0:
        capped_ikze = min(ikze_contribution, ikze_limit)
        claims.append(_claim(
            "ikze",
            "IKZE (indywidualne konto zabezpieczenia emerytalnego)",
            "ready",
            capped_ikze,
            "Definitive",
            f"IKZE contributions are deductible up to {ikze_limit:,.0f} PLN/year. "
            f"Your contribution: {ikze_contribution:,.2f} PLN → deductible: {capped_ikze:,.2f} PLN. "
            "Reduces PIT base at your marginal rate (12% or 32%).",
        ))
    else:
        claims.append(_claim(
            "ikze",
            "IKZE (indywidualne konto zabezpieczenia emerytalnego)",
            "needs_input",
            ikze_limit,
            "Definitive",
            f"IKZE contributions are deductible from income up to {ikze_limit:,.0f} PLN/year. "
            "Add your IKZE contribution amount (ikze_contribution) to calculate the saving. "
            "Note: withdrawals at retirement are taxed at flat 10%.",
        ))

    # ── 5. Ulga internetowa (internet expense deduction) ─────────────────
    internet_max = float(rules["internet_ulga_max"])
    if internet_expense > 0 and internet_ulga_year > 0:
        # Only eligible in 2 consecutive years
        deductible_internet = min(internet_expense, internet_max)
        claims.append(_claim(
            "ulga_na_internet",
            "Ulga na internet (internet expense deduction)",
            "ready",
            deductible_internet,
            "Likely",
            f"Koszty internetu do {internet_max:,.0f} PLN rocznie. "
            "Eligible only in 2 consecutive tax years. Keep ISP invoices. "
            f"Your expense: {internet_expense:,.2f} PLN → deductible: {deductible_internet:,.2f} PLN.",
        ))
    else:
        claims.append(_claim(
            "ulga_na_internet",
            "Ulga na internet (internet expense deduction)",
            "needs_input",
            internet_max,
            "Likely",
            f"Odliczenie do {internet_max:,.0f} PLN za koszty internetu — only in 2 consecutive tax years. "
            "Provide your annual internet cost and whether you used this relief in the previous year. "
            "Keep ISP invoices to evidence the claim.",
        ))

    # ── 6. Darowizny (charitable donations) ──────────────────────────────
    max_donations_deduction = gross * rules["darowizny_pct"]
    if donation_receipts:
        total_donations = sum(
            float(r.amount if hasattr(r, "amount") else r.get("amount", 0))
            for r in donation_receipts
        )
        deductible_donations = min(total_donations, max_donations_deduction)
        claims.append(_claim(
            "darowizny",
            "Darowizny (charitable donations)",
            "needs_evidence",
            round(deductible_donations, 2),
            "Definitive",
            f"Darowizny na cele pożytku publicznego odliczane do 6% dochodu "
            f"({max_donations_deduction:,.2f} PLN). "
            f"Total donations logged: {total_donations:,.2f} PLN → "
            f"deductible: {deductible_donations:,.2f} PLN. "
            "Keep donation confirmations (potwierdzenia przelewu).",
        ))
    else:
        claims.append(_claim(
            "darowizny",
            "Darowizny (charitable donations)",
            "detected",
            0.0,
            "Definitive",
            f"Donations to public-benefit organisations are deductible up to 6% of income "
            f"({max_donations_deduction:,.2f} PLN). Add donation receipts if applicable.",
        ))

    # ── 7. Ulga rehabilitacyjna (disability relief) ───────────────────────
    if disability_grade > 0:
        # Amount varies greatly — flag as ready with unknown amount
        claims.append(_claim(
            "ulga_rehabilitacyjna",
            "Ulga rehabilitacyjna (disability relief)",
            "ready",
            0.0,  # Depends on specific expenses — too variable to estimate without receipts
            "Definitive",
            f"Orzeczenie o niepełnosprawności stopnia {disability_grade} — "
            "eligible for ulga rehabilitacyjna. Deductible expenses include: "
            "medical equipment, rehabilitation, care, transport. "
            "Provide expense details for exact amount estimate. "
            "Some items are limited (e.g., medications: over 100 PLN/month excess).",
        ))
    else:
        claims.append(_claim(
            "ulga_rehabilitacyjna",
            "Ulga rehabilitacyjna (disability relief)",
            "needs_input",
            0.0,
            "Definitive",
            "If you or a dependent family member has a disability certificate "
            "(orzeczenie o niepełnosprawności), you may be eligible for various "
            "rehabilitative expense deductions. Provide disability grade and expense details.",
        ))

    # ── 8. Ulga na powrót (returning-to-Poland relief) ────────────────────
    if recently_relocated:
        claims.append(_claim(
            "ulga_na_powrot",
            "Ulga na powrót (returning-to-Poland PIT exemption)",
            "detected",
            min(gross, float(rules["ulga_dla_mlodych_limit"])),  # Same PLN limit as ulga dla mlodych
            "Likely",
            f"Detected potential relocation to Poland. Persons returning to Poland after "
            "at least 3 years abroad may be exempt from PIT for up to 4 tax years "
            f"on income up to {rules['ulga_dla_mlodych_limit']:,} PLN/year. "
            "Confirm eligibility with a tax adviser — requires formal application.",
        ))
    else:
        claims.append(_claim(
            "ulga_na_powrot",
            "Ulga na powrót (returning-to-Poland PIT exemption)",
            "detected",
            0.0,
            "Likely",
            "If you relocated to Poland from abroad (minimum 3 years away), "
            "you may be exempt from PIT for 4 years on income up to 85,528 PLN/year. "
            "Set recently_relocated_to_poland=true in profile to flag this opportunity.",
        ))

    # ── 9. Wspólne rozliczenie z małżonkiem (joint filing) ────────────────
    if ctx.married:
        claims.append(_claim(
            "wspolne_rozliczenie",
            "Wspólne rozliczenie z małżonkiem (joint filing with spouse)",
            "detected",
            0.0,  # Saving depends on income difference — computed in calculate_tax
            "Definitive",
            "Married couples can file jointly (PIT-36 or PIT-37). Income is pooled and halved, "
            "reducing effective tax when spouses have different earnings. "
            "Beneficial if one spouse earns above 120,000 PLN or if incomes differ significantly. "
            "Use calculate_tax with spouse_gross in extra to estimate the saving.",
        ))
    else:
        claims.append(_claim(
            "wspolne_rozliczenie",
            "Wspólne rozliczenie z małżonkiem (joint filing with spouse)",
            "needs_input",
            0.0,
            "Definitive",
            "If you are married and your spouse has a different income level, "
            "joint filing may reduce your combined tax. "
            "Provide marital status and spouse income (spouse_gross) to evaluate.",
        ))

    # ── Sort: ready first, then needs_evidence, needs_input, detected ─────
    _STATUS_ORDER = {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}
    claims.sort(key=lambda c: (
        _STATUS_ORDER.get(c["status"], 9),
        -(c.get("amount_estimate") or 0),
        c["title"],
    ))

    return claims


def _calculate_child_relief(num_children: int, rules: dict) -> float:
    """Calculate total child relief for the given number of qualifying children."""
    r1 = float(rules["ulga_na_dzieci_1_2"])
    r2 = float(rules["ulga_na_dzieci_3"])
    r3 = float(rules["ulga_na_dzieci_4plus"])

    if num_children == 0:
        return 0.0
    if num_children == 1:
        return r1
    if num_children == 2:
        return r1 * 2
    if num_children == 3:
        return r1 * 2 + r2
    # 4+
    return r1 * 2 + r2 + r3 * (num_children - 3)


def _child_relief_notes(num_children: int, rules: dict) -> str:
    r1 = rules["ulga_na_dzieci_1_2"]
    r2 = rules["ulga_na_dzieci_3"]
    r3 = rules["ulga_na_dzieci_4plus"]
    total = _calculate_child_relief(num_children, rules)
    return (
        f"Ulga na {num_children} {'dziecko' if num_children == 1 else 'dzieci'}: "
        f"{total:,.2f} PLN total. "
        f"Rates: 1st–2nd child {r1:,.2f} PLN each, "
        f"3rd child {r2:,.2f} PLN, "
        f"4th+ {r3:,.2f} PLN each. "
        "If tax is insufficient to absorb the full relief, the remainder is refundable "
        "(ulga prorodzinna — zwrot różnicy)."
    )


def _claim(claim_id, title, status, amount_estimate, confidence, notes):
    return {
        "id": claim_id,
        "title": title,
        "status": status,
        "amount_estimate": round(float(amount_estimate), 2) if amount_estimate is not None else 0.0,
        "confidence": confidence,
        "notes": notes,
    }
