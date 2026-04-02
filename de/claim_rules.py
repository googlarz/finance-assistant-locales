"""
German-specific claim generation — ported from TaxDE claim_engine.py.

Generates tax deduction claims from a Finance Assistant profile using
the German locale's tax rules.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from locales.de.tax_rules import get_tax_year_rules
from locales.de.tax_calculator import calculate_refund


def generate_german_claims(profile: dict, year: int = None) -> list[dict]:
    """Generate German tax claims from profile. Returns list of claim dicts."""
    year = year or profile.get("meta", {}).get("tax_year", datetime.now().year)
    rules = get_tax_year_rules(year)

    tax_extra = profile.get("tax_profile", {}).get("extra", {})
    emp = profile.get("employment", {})
    fam = profile.get("family", {})
    housing = profile.get("housing", {})
    receipts = profile.get("current_year_receipts", [])

    emp_type = emp.get("type", "")
    is_employee = emp_type in ("employed", "angestellter")

    claims = []

    # Homeoffice
    ho_days_pw = housing.get("homeoffice_days_per_week")
    if ho_days_pw is None and is_employee:
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "needs_input", None, None, "likely",
                             "§4 Abs. 5 Nr. 6b EStG", "Confirm home-office days per week."))
    elif ho_days_pw:
        days = min(int(ho_days_pw * 46), rules["homeoffice_max_days"])
        amount = min(days * rules["homeoffice_tagespauschale"], rules["homeoffice_max_annual"])
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "ready", amount, None, "definitive",
                             "§4 Abs. 5 Nr. 6b EStG", "Keep a day log."))

    # Commute
    commute_km = housing.get("commute_km")
    commute_days = housing.get("commute_days_per_year")
    if is_employee and not (commute_km and commute_days):
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "needs_input", None, None, "likely",
                             "§9 Abs. 1 Nr. 4 EStG", "Confirm commute distance and office days."))
    elif commute_km and commute_days:
        short = min(commute_km, 20)
        long = max(commute_km - 20, 0)
        amount = commute_days * (short * rules["pendlerpauschale_short"] + long * rules["pendlerpauschale_long"])
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "ready", amount, None, "definitive",
                             "§9 Abs. 1 Nr. 4 EStG", "Use actual commute days."))

    # Equipment from receipts
    equip_receipts = [r for r in receipts if r.get("category") == "equipment"]
    if equip_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in equip_receipts)
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment",
                             "ready", amount, None, "likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Keep invoices with business-use note."))
    elif is_employee:
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment_opportunity",
                             "detected", None, None, "likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Check if you bought work gear this year."))

    # Donations
    don_receipts = [r for r in receipts if r.get("category") == "donation"]
    if don_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in don_receipts)
        claims.append(_claim(year, "sonderausgaben", "Spenden", "donation",
                             "ready", amount, None, "definitive",
                             "§10b EStG", "Keep donation receipts."))

    # Childcare
    children = fam.get("children", [])
    for i, child in enumerate(children, 1):
        birth_year = child.get("birth_year")
        age = year - birth_year if birth_year else 99
        childcare = child.get("childcare") or child.get("kita")
        cost = child.get("childcare_annual_cost") or child.get("kita_annual_cost") or 0
        if age < 14 and childcare:
            if cost:
                amount = min(cost * rules["kinderbetreuung_pct"], rules["kinderbetreuung_max"])
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "ready", amount, None, "definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Keep invoice and bank transfer proof."))
            else:
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "needs_evidence", None, None, "definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Add annual childcare cost."))

    # Riester
    if tax_extra.get("riester"):
        contrib = float(tax_extra.get("riester_contribution") or 0)
        if contrib:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "ready", min(contrib, rules["riester_max"]), None, "definitive",
                                 "§10a EStG", "Keep provider statement for Anlage AV."))
        else:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "needs_evidence", None, None, "definitive",
                                 "§10a EStG", "Add annual Riester contribution."))

    # Rürup
    if tax_extra.get("ruerup"):
        contrib = float(tax_extra.get("ruerup_contribution") or 0)
        if contrib:
            cap = rules.get("ruerup_max_single")
            amount = contrib if cap is None else min(contrib, cap)
            claims.append(_claim(year, "sonderausgaben", "Rürup / Basisrente", "ruerup",
                                 "ready", amount, None, "likely" if cap is None else "definitive",
                                 "§10 Abs. 1 Nr. 2b EStG", "Keep provider statement."))

    # Union dues
    union = float(tax_extra.get("gewerkschaft_beitrag") or 0)
    if union > 0:
        claims.append(_claim(year, "werbungskosten", "Gewerkschaftsbeiträge", "union_dues",
                             "ready", union, None, "definitive",
                             "§9 Abs. 1 Nr. 3d EStG", "Keep union statement."))

    # Disability
    disability = int(tax_extra.get("disability_grade") or 0)
    if disability >= 20:
        g = (disability // 10) * 10
        amount = rules["behindertenpauschbetrag"].get(g, 0)
        claims.append(_claim(year, "aussergewoehnliche_belastungen", "Behinderten-Pauschbetrag",
                             "disability", "ready", amount, None, "definitive",
                             "§33b EStG", "Keep disability certificate."))

    # Steuerberatungskosten (§ 10 Abs. 1 Nr. 6 EStG)
    steuerberatung_cost = float(tax_extra.get("steuerberatung_cost") or 0)
    steuerberatung_receipts = [r for r in receipts if r.get("category") == "steuerberatung"]
    if steuerberatung_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in steuerberatung_receipts)
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "ready", amount, None, "definitive",
                             "§ 10 Abs. 1 Nr. 6 EStG", "Keep adviser invoices and payment receipts."))
    elif steuerberatung_cost > 0:
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "ready", steuerberatung_cost, None, "definitive",
                             "§ 10 Abs. 1 Nr. 6 EStG", "Keep adviser invoices and payment receipts."))
    else:
        claims.append(_claim(year, "sonderausgaben", "Steuerberatungskosten", "steuerberatung",
                             "detected", None, None, "likely",
                             "§ 10 Abs. 1 Nr. 6 EStG",
                             "Did you pay a tax adviser or software this year? Add the cost."))

    # Handwerkerleistungen (§ 35a Abs. 3 EStG) — tax credit (Steuerermäßigung), not deduction
    housing_type = housing.get("type", "")
    handwerker_labour_cost = float(tax_extra.get("handwerker_labour_cost") or 0)
    if handwerker_labour_cost > 0:
        credit = min(handwerker_labour_cost * 0.20, 1200)
        claims.append(_claim(year, "steuerermaeßigung", "Handwerkerleistungen (Steuerermäßigung)",
                             "handwerker", "ready", credit, None, "definitive",
                             "§ 35a Abs. 3 EStG",
                             "Tax credit (not deduction): 20% of labour costs, max €1,200. Keep invoices showing labour/material split."))
    elif housing_type in ("owner", "renter", "eigentuemer", "mieter"):
        claims.append(_claim(year, "steuerermaeßigung", "Handwerkerleistungen (Steuerermäßigung)",
                             "handwerker", "detected", None, None, "likely",
                             "§ 35a Abs. 3 EStG",
                             "Did you have craftsmen/tradespeople work at your home? 20% of labour costs up to €1,200 credit."))

    # Haushaltsnahe Dienstleistungen (§ 35a Abs. 2 EStG) — tax credit
    haushaltsnahe_cost = float(tax_extra.get("haushaltsnahe_cost") or 0)
    if haushaltsnahe_cost > 0:
        credit = min(haushaltsnahe_cost * 0.20, 4000)
        claims.append(_claim(year, "steuerermaeßigung", "Haushaltsnahe Dienstleistungen (Steuerermäßigung)",
                             "haushaltsnahe", "ready", credit, None, "definitive",
                             "§ 35a Abs. 2 EStG",
                             "Tax credit: 20% of qualifying household service costs, max €4,000. Keep invoices."))
    else:
        claims.append(_claim(year, "steuerermaeßigung", "Haushaltsnahe Dienstleistungen (Steuerermäßigung)",
                             "haushaltsnahe", "detected", None, None, "likely",
                             "§ 35a Abs. 2 EStG",
                             "Did you pay for cleaning, gardening, or care services at home? 20% credit up to €4,000."))

    # Außergewöhnliche Belastungen — Krankheitskosten (§ 33 EStG)
    gross = emp.get("annual_gross") or 0.0
    medical_receipts = [r for r in receipts if r.get("category") == "medical"]
    if medical_receipts:
        medical_total = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in medical_receipts)
        # Simplified zumutbare Belastung: 1-7% of gross depending on income/family
        num_children = len(fam.get("children", []))
        married = fam.get("status") in ("married", "civil_partnership")
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
                                 "medical_costs", "ready", net_medical, None, "likely",
                                 "§ 33 EStG",
                                 "Deductible portion after zumutbare Belastung threshold. Keep all medical receipts."))
        else:
            claims.append(_claim(year, "aussergewoehnliche_belastungen",
                                 "Krankheitskosten (unter zumutbarer Belastung)",
                                 "medical_costs", "needs_evidence", None, None, "likely",
                                 "§ 33 EStG",
                                 "Medical costs do not exceed your zumutbare Belastung threshold. Collect all receipts."))
    else:
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Krankheitskosten", "medical_costs",
                             "needs_evidence", None, None, "likely",
                             "§ 33 EStG",
                             "Add medical receipts (co-pays, glasses, dental, etc.) to check if threshold is exceeded."))

    # Ausbildungskosten / Zweitstudium (§ 10 Abs. 1 Nr. 7 EStG) — max €6,000/year
    ausbildung_costs = float(tax_extra.get("ausbildung_costs") or 0)
    if ausbildung_costs > 0:
        amount = min(ausbildung_costs, 6_000)
        claims.append(_claim(year, "sonderausgaben",
                             "Ausbildungskosten (Zweitstudium / Berufsausbildung)",
                             "ausbildung", "ready", amount, None, "definitive",
                             "§ 10 Abs. 1 Nr. 7 EStG",
                             "Second professional education or studies. Max €6,000/year. Keep tuition and course receipts."))

    # Unterhaltsleistungen (§ 33a EStG) — up to Grundfreibetrag
    unterhalt_paid = float(tax_extra.get("unterhalt_paid") or 0)
    dependents_outside = fam.get("dependents_outside_household", [])
    if unterhalt_paid > 0:
        unterhalt_max = rules.get("grundfreibetrag", 11_784)
        amount = min(unterhalt_paid, unterhalt_max)
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Unterhaltsleistungen (§ 33a EStG)",
                             "unterhalt", "ready", amount, None, "definitive",
                             "§ 33a EStG",
                             "Legal support payments up to Grundfreibetrag. Keep transfer records and maintenance agreements."))
    elif dependents_outside:
        claims.append(_claim(year, "aussergewoehnliche_belastungen",
                             "Unterhaltsleistungen (§ 33a EStG)",
                             "unterhalt", "detected", None, None, "likely",
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
