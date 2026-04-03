"""
Dutch income tax calculator.

Calculates Box 1 (employment / home income), optionally Box 3 (savings &
investments), and applies heffingskortingen (heffingskorting + arbeidskorting).

Box 2 (substantial shareholding ≥5% in a BV) is only calculated when
ctx.extra["is_dga"] is True and ctx.extra["box2_income"] is provided.

Social premiums (volksverzekeringen: AOW, ANW, WLZ) are embedded in the Box 1
first-bracket rate and are not double-counted.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .tax_rules import (
    get_tax_year_rules,
    resolve_supported_year,
    calculate_box1_tax,
    calculate_box3_tax,
    calculate_heffingskorting,
    calculate_arbeidskorting,
    calculate_marginal_rate,
)

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
    Calculate Dutch income tax (all boxes).

    Returns:
        gross                   — Box 1 gross employment income
        box1_tax_before_credits — Box 1 tax before heffingskortingen
        heffingskorting_applied — algemene heffingskorting used
        arbeidskorting_applied  — arbeidskorting used
        box1_tax               — Box 1 tax after credits (floor 0)
        box2_tax               — Box 2 tax (0 if not DGA/BV owner)
        box3_tax               — Box 3 tax (0 if no portfolio data)
        total_tax              — sum of all boxes
        net                    — gross − total_tax
        effective_rate         — total_tax / gross
        marginal_rate          — marginal Box 1 rate on last euro
        confidence             — Definitive / Likely / Debatable
        breakdown              — detailed sub-amounts
    """
    LocaleContext = _import_locale_context()

    if isinstance(ctx, dict):
        if year:
            ctx = dict(ctx)
            ctx.setdefault("meta", {})["tax_year"] = year
        ctx = LocaleContext.from_finance_profile(ctx, tax_year=year)
    elif year is not None:
        from dataclasses import replace
        ctx = replace(ctx, tax_year=year)

    requested_year = ctx.tax_year
    resolved_year, year_note = resolve_supported_year(requested_year)
    rules = get_tax_year_rules(resolved_year)

    gross = ctx.annual_gross + ctx.side_income
    employment_type = ctx.employment_type
    partner = ctx.married

    # ── Box 1 ──────────────────────────────────────────────────────────────
    box1_raw = calculate_box1_tax(gross, rules)

    # Heffingskortingen
    hk = calculate_heffingskorting(gross, rules)
    ak = calculate_arbeidskorting(gross, rules) if employment_type == "employed" else 0.0

    box1_tax = max(0.0, box1_raw - hk - ak)
    box1_tax = round(box1_tax, 2)

    # ── Box 2 (DGA / BV owner) ────────────────────────────────────────────
    is_dga = ctx.extra.get("is_dga", False)
    box2_income = float(ctx.extra.get("box2_income", 0.0) or 0.0)
    if is_dga and box2_income > 0:
        threshold = rules["box2_threshold"]
        if box2_income <= threshold:
            box2_tax = box2_income * rules["box2_rate_low"]
        else:
            box2_tax = (threshold * rules["box2_rate_low"]
                        + (box2_income - threshold) * rules["box2_rate_high"])
        box2_tax = round(box2_tax, 2)
    else:
        box2_tax = 0.0

    # ── Box 3 (savings / investments) ─────────────────────────────────────
    savings = float(ctx.extra.get("savings", 0.0) or 0.0)
    investments = float(ctx.extra.get("investments", 0.0) or 0.0)
    debts = float(ctx.extra.get("debts", 0.0) or 0.0)
    has_box3 = (savings + investments) > 0

    if has_box3:
        box3_tax = calculate_box3_tax(savings, investments, debts, partner, rules)
    else:
        box3_tax = 0.0

    # ── Totals and confidence ─────────────────────────────────────────────
    total_tax = round(box1_tax + box2_tax + box3_tax, 2)
    net = round(gross - total_tax, 2)
    effective_rate = round(total_tax / gross, 4) if gross > 0 else 0.0
    marginal = calculate_marginal_rate(gross, rules)

    # Confidence
    base_confidence = rules["confidence"]
    if year_note:
        confidence = "Likely"
    elif has_box3 and (savings + investments) > rules["box3_exemption_single"]:
        confidence = "Debatable"  # Box 3 legal uncertainty
    elif employment_type in ("freelancer", "self_employed"):
        confidence = "Likely"
    else:
        confidence = base_confidence

    expat_30pct = ctx.expat and ctx.extra.get("has_30_ruling", False)

    return {
        "gross": gross,
        "box1_tax_before_credits": round(box1_raw, 2),
        "heffingskorting_applied": round(hk, 2),
        "arbeidskorting_applied": round(ak, 2),
        "box1_tax": box1_tax,
        "box2_tax": box2_tax,
        "box3_tax": box3_tax,
        "total_tax": total_tax,
        "net": net,
        "effective_rate": effective_rate,
        "marginal_rate": marginal,
        "confidence": confidence,
        "breakdown": {
            "gross": gross,
            "box1_rate_low": rules["box1_rate_low"],
            "box1_rate_high": rules["box1_rate_high"],
            "box1_threshold": rules["box1_threshold"],
            "box1_raw_tax": round(box1_raw, 2),
            "heffingskorting": round(hk, 2),
            "arbeidskorting": round(ak, 2),
            "box1_tax_after_credits": box1_tax,
            "box2_income": box2_income,
            "box2_tax": box2_tax,
            "box3_savings": savings,
            "box3_investments": investments,
            "box3_debts": debts,
            "box3_exemption": (
                rules["box3_exemption_partner"] if partner
                else rules["box3_exemption_single"]
            ),
            "box3_tax": box3_tax,
            "total_tax": total_tax,
            "net": net,
            "expat_30_ruling_detected": expat_30pct,
        },
    }
