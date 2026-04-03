"""
German-specific claim generation — ported from TaxDE claim_engine.py.

Generates tax deduction claims from a Finance Assistant profile using
the German locale's tax rules.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from .tax_rules import get_tax_year_rules
from .tax_calculator import calculate_refund


def generate_german_claims(ctx, year: int = None) -> list[dict]:
    """Generate German tax claims from LocaleContext or profile dict. Returns list of claim dicts."""
    if isinstance(ctx, dict):
        try:
            from ..context import LocaleContext
        except ImportError:
            from context import LocaleContext  # type: ignore
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)

    year = year or ctx.tax_year or datetime.now().year
    rules = get_tax_year_rules(year)

    is_employee = ctx.employment_type in ("employed", "angestellter")

    # Convert ChildInfo / ReceiptItem objects to dicts for downstream compatibility
    children = []
    for ch in ctx.children:
        if isinstance(ch, dict):
            children.append(ch)
        else:
            children.append({
                "birth_year": ch.birth_year,
                "childcare": ch.childcare,
                "childcare_annual_cost": ch.childcare_annual_cost,
            })

    receipts = []
    for r in ctx.receipts:
        if isinstance(r, dict):
            receipts.append(r)
        else:
            receipts.append({
                "category": r.category,
                "amount": r.amount,
                "business_use_pct": r.business_use_pct,
                "description": r.description,
                "deductible_amount": r.deductible_amount,
            })

    gross = ctx.annual_gross
    married = ctx.married

    claims = []

    # Homeoffice
    ho_days_pw = ctx.homeoffice_days_per_week
    if ho_days_pw is None and is_employee:
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "needs_input", None, None, "Likely",
                             "§4 Abs. 5 Nr. 6b EStG", "Confirm home-office days per week."))
    elif ho_days_pw:
        days = min(int(ho_days_pw * 46), rules["homeoffice_max_days"])
        amount = min(days * rules["homeoffice_tagespauschale"], rules["homeoffice_max_annual"])
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "ready", amount, None, "Definitive",
                             "§4 Abs. 5 Nr. 6b EStG", "Keep a day log."))

    # Commute
    commute_km = ctx.commute_km
    commute_days = ctx.commute_days_per_year
    if is_employee and not (commute_km and commute_days):
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "needs_input", None, None, "Likely",
                             "§9 Abs. 1 Nr. 4 EStG", "Confirm commute distance and office days."))
    elif commute_km and commute_days:
        short = min(commute_km, 20)
        long = max(commute_km - 20, 0)
        amount = commute_days * (short * rules["pendlerpauschale_short"] + long * rules["pendlerpauschale_long"])
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "ready", amount, None, "Definitive",
                             "§9 Abs. 1 Nr. 4 EStG", "Use actual commute days."))

    # Equipment from receipts
    equip_receipts = [r for r in receipts if r.get("category") == "equipment"]
    if equip_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in equip_receipts)
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment",
                             "ready", amount, None, "Likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Keep invoices with business-use note."))
    elif is_employee:
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment_opportunity",
                             "detected", None, None, "Likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Check if you bought work gear this year."))

    # Donations
    don_receipts = [r for r in receipts if r.get("category") == "donation"]
    if don_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in don_receipts)
        claims.append(_claim(year, "sonderausgaben", "Spenden", "donation",
                             "ready", amount, None, "Definitive",
                             "§10b EStG", "Keep donation receipts."))

    # Childcare
    for i, child in enumerate(children, 1):
        birth_year = child.get("birth_year")
        age = year - birth_year if birth_year else 99
        childcare = child.get("childcare") or child.get("kita")
        cost = child.get("childcare_annual_cost") or child.get("kita_annual_cost") or 0
        if age < 14 and childcare:
            if cost:
                amount = min(cost * rules["kinderbetreuung_pct"], rules["kinderbetreuung_max"])
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "ready", amount, None, "Definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Keep invoice and bank transfer proof."))
            else:
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "needs_evidence", None, None, "Definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Add annual childcare cost."))

    # Riester
    if ctx.riester:
        contrib = ctx.riester_contribution
        if contrib:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "ready", min(contrib, rules["riester_max"]), None, "Definitive",
                                 "§10a EStG", "Keep provider statement for Anlage AV."))
        else:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "needs_evidence", None, None, "Definitive",
                                 "§10a EStG", "Add annual Riester contribution."))

    # Rürup
    if ctx.ruerup:
        contrib = ctx.ruerup_contribution
        if contrib:
            cap = rules.get("ruerup_max_single")
            amount = contrib if cap is None else min(contrib, cap)
            claims.append(_claim(year, "sonderausgaben", "Rürup / Basisrente", "ruerup",
                                 "ready", amount, None, "Likely" if cap is None else "Definitive",
                                 "§10 Abs. 1 Nr. 2b EStG", "Keep provider statement."))

    # Union dues
    union = ctx.union_dues
    if union > 0:
        claims.append(_claim(year, "werbungskosten", "Gewerkschaftsbeiträge", "union_dues",
                             "ready", union, None, "Definitive",
                             "§9 Abs. 1 Nr. 3d EStG", "Keep union statement."))

    # Disability
    disability = ctx.disability_grade
    if disability >= 20:
        g = (disability // 10) * 10
        amount = rules["behindertenpauschbetrag"].get(g, 0)
        claims.append(_claim(year, "aussergewoehnliche_belastungen", "Behinderten-Pauschbetrag",
                             "disability", "ready", amount, None, "Definitive",
                             "§33b EStG", "Keep disability certificate."))

    # Steuerberatungskosten (§ 10 Abs. 1 Nr. 6 EStG)
    steuerberatung_cost = float(ctx.extra.get("steuerberatung_cost") or 0)
    steuerberatung_receipts = [r for r in receipts if r.get("category") == "steuerberatung"]
    if steuerberatung_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in steuerberatung_receipts)
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "ready", amount, None, "Definitive",
                             "§ 10 Abs. 1 Nr. 6 EStG", "Keep adviser invoices and payment receipts."))
    elif steuerberatung_cost > 0:
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "ready", steuerberatung_cost, None, "Definitive",
                             "§ 10 Abs. 1 Nr. 6 EStG", "Keep adviser invoices and payment receipts."))
    else:
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "detected", None, None, "Likely",
                             "§ 10 Abs. 1 Nr. 6 EStG",
                             "Did you pay a tax adviser or software this year? Add the cost."))

    # Handwerkerleistungen (§ 35a Abs. 3 EStG) — tax credit (Steuerermäßigung), not deduction
    housing_type = ctx.extra.get("housing_type", "")
    handwerker_labour_cost = float(ctx.extra.get("handwerker_labour_cost") or 0)
    if handwerker_labour_cost > 0:
        credit = min(handwerker_labour_cost * 0.20, 1200)
        claims.append(_claim(year, "steuerermaeßigung", "Handwerkerleistungen (Steuerermäßigung)",
                             "handwerker", "ready", credit, None, "Definitive",
                             "§ 35a Abs. 3 EStG",
                             "Tax credit (not deduction): 20% of labour costs, max €1,200. Keep invoices showing labour/material split."))
    elif housing_type in ("owner", "renter", "eigentuemer", "mieter"):
        claims.append(_claim(year, "steuerermaeßigung", "Handwerkerleistungen (Steuerermäßigung)",
                             "handwerker", "detected", None, None, "Likely",
                             "§ 35a Abs. 3 EStG",
                             "Did you have craftsmen/tradespeople work at your home? 20% of labour costs up to €1,200 credit."))

    # Haushaltsnahe Dienstleistungen (§ 35a Abs. 2 EStG) — tax credit
    haushaltsnahe_cost = float(ctx.extra.get("haushaltsnahe_cost") or 0)
    if haushaltsnahe_cost > 0:
        credit = min(haushaltsnahe_cost * 0.20, 4000)
        claims.append(_claim(year, "steuerermaeßigung", "Haushaltsnahe Dienstleistungen (Steuerermäßigung)",
                             "haushaltsnahe", "ready", credit, None, "Definitive",
                             "§ 35a Abs. 2 EStG",
                             "Tax credit: 20% of qualifying household service costs, max €4,000. Keep invoices."))
    else:
        claims.append(_claim(year, "steuerermaeßigung", "Haushaltsnahe Dienstleistungen (Steuerermäßigung)",
                             "haushaltsnahe", "detected", None, None, "Likely",
                             "§ 35a Abs. 2 EStG",
                             "Did you pay for cleaning, gardening, or care services at home? 20% credit up to €4,000."))

    # Außergewöhnliche Belastungen — Krankheitskosten (§ 33 EStG)
    num_children = len(children)
    medical_receipts = [r for r in receipts if r.get("category") == "medical"]
    if medical_receipts:
        medical_total = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in medical_receipts)
        # Simplified zumutbare Belastung: 1-7% of gross depending on income/family
        if num_children >= 2 or (num_children >= 1 and married):
            zb_pct = 0.01 if gross <= 15_340 else (0.02 if gross <= 51_130 else 0.04)
        elif num_children == 1 or married:
            zb_pct = 0.02 if gross <= 15_340 else (0.03 if gross <= 51_130 else 0.04)
        else:
            zb_pct = 0.05 if gross <= 15_340 else (0.06 if gross <= 51_130 else 0.07)
        zumutbare_belastung = gross * zb_pct
        net_medical = max(0.0, medical_total - zumutbare_belastung)
        if net_medical > 0:
            claims.append(_claim(year, "aussergewoehnliche_belastungen",
                                 "Krankheitskosten (nach zumutbarer Belastung)",
                                 "medical_costs", "ready", net_medical, None, "Likely",
                                 "§ 33 EStG",
                                 "Deductible portion after zumutbare Belastung threshold. Keep all medical receipts."))
        else:
            claims.append(_claim(year, "aussergewoehnliche_belastungen",
                                 "Krankheitskosten (unter zumutbarer Belastung)",
                                 "medical_costs", "needs_evidence", None, None, "Likely",
                                 "§ 33 EStG",
                                 "Medical costs do not exceed your zumutbare Belastung threshold. Collect all receipts."))
    else:
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Krankheitskosten", "medical_costs",
                             "needs_evidence", None, None, "Likely",
                             "§ 33 EStG",
                             "Add medical receipts (co-pays, glasses, dental, etc.) to check if threshold is exceeded."))

    # Ausbildungskosten / Zweitstudium (§ 10 Abs. 1 Nr. 7 EStG) — max €6,000/year
    ausbildung_costs = float(ctx.extra.get("ausbildung_costs") or 0)
    if ausbildung_costs > 0:
        amount = min(ausbildung_costs, 6_000)
        claims.append(_claim(year, "sonderausgaben",
                             "Ausbildungskosten (Zweitstudium / Berufsausbildung)",
                             "ausbildung", "ready", amount, None, "Definitive",
                             "§ 10 Abs. 1 Nr. 7 EStG",
                             "Second professional education or studies. Max €6,000/year. Keep tuition and course receipts."))

    # Unterhaltsleistungen (§ 33a EStG) — up to Grundfreibetrag
    unterhalt_paid = float(ctx.extra.get("unterhalt_paid") or 0)
    dependents_outside = ctx.extra.get("dependents_outside_household", [])
    if unterhalt_paid > 0:
        unterhalt_max = rules.get("grundfreibetrag", 11_784)
        amount = min(unterhalt_paid, unterhalt_max)
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Unterhaltsleistungen (§ 33a EStG)",
                             "unterhalt", "ready", amount, None, "Definitive",
                             "§ 33a EStG",
                             "Legal support payments up to Grundfreibetrag. Keep transfer records and maintenance agreements."))
    elif dependents_outside:
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Unterhaltsleistungen (§ 33a EStG)",
                             "unterhalt", "detected", None, None, "Likely",
                             "§ 33a EStG",
                             "You have dependents outside your household. Add maintenance payments via tax_profile.extra.unterhalt_paid."))

    # Sort: ready first, then by amount descending
    claims.sort(key=lambda c: (
        {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}.get(c["status"], 9),
        -(c.get("amount_deductible") or 0),
        c["title"],
    ))

    return claims


def _claim(year, category, title, claim_id, status, amount, refund_effect, confidence, legal_basis, next_action):
    return {
        "id": claim_id,
        "tax_year": year,
        "category": category,
        "title": title,
        "status": status,
        "amount_deductible": round(amount, 2) if amount is not None else None,
        "estimated_refund_effect": round(refund_effect, 2) if refund_effect is not None else None,
        "confidence": confidence,
        "legal_basis": legal_basis,
        "next_action": next_action,
    }
