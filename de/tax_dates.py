"""
German tax filing deadline helpers and calendar.

German tax calendar overview
─────────────────────────────
Employees (Arbeitnehmer) who file voluntarily have until 31 July of the
following year (§ 149 Abs. 2 AO). Mandatory filers have the same deadline.

With a tax adviser (Steuerberater) the deadline is extended to the last day
of February of the *second* year following the tax year (§ 149 Abs. 3 AO),
e.g. for tax year 2025 → 28 February 2027. In practice the BMF publishes
specific extension dates each year via AEAO.

Quarterly VAT prepayments (Umsatzsteuer-Vorauszahlungen) are due on
10 January, 10 April, 10 July, and 10 October (§ 18 Abs. 1 UStG).

Monthly Lohnsteueranmeldung is due on the 10th of the following month
(§ 41a Abs. 2 EStG). Employers with annual Lohnsteuer ≤ €5,000 may file
quarterly; ≤ €1,080 annually.

Vorabpauschale for investment funds is settled in January each year
(§ 16 InvStG); the custodian deducts it automatically.

Freistellungsauftrag (exemption order) should be reviewed each January
to optimise the Sparer-Pauschbetrag allocation across banks.
"""

from __future__ import annotations
from calendar import monthrange
from datetime import date, timedelta


# ── Filing deadlines ───────────────────────────────────────────────────────
# Key: (advised, tax_year) → filing deadline
# Source: § 149 Abs. 2 u. 3 AO; BMF AEAO zu § 149 AO (annual publication)
ADVISED_DEADLINES = {
    False: {
        2023: date(2025, 6, 2),    # § 149 Abs. 2 AO (extended due to COVID precedent)
        2024: date(2026, 4, 30),   # BMF-Schreiben; standard deadline: 31 Jul 2025
        2025: date(2027, 7, 31),   # standard deadline § 149 Abs. 2 AO
    },
    True: {
        2023: date(2025, 11, 3),   # § 149 Abs. 3 AO, extended
        2024: date(2026, 9, 30),   # § 149 Abs. 3 AO
        2025: date(2028, 2, 28),   # § 149 Abs. 3 AO — last day Feb 2028
    },
}

# ── Recurring important dates ──────────────────────────────────────────────
# These apply every calendar year (replace YEAR with actual year as needed).
# Sources:
#   § 18 Abs. 1 UStG (Umsatzsteuer-Vorauszahlung)
#   § 41a Abs. 2 EStG (Lohnsteueranmeldung)
#   § 16 InvStG (Vorabpauschale)
IMPORTANT_DATES = {
    "ust_vorauszahlung_q1": {
        "month": 1, "day": 10,
        "label": "USt-Vorauszahlung Q4 (Vorjahr) — 10. Januar",
        "category": "vat_prepayment",
        "applies_to": ["freelancer", "self_employed"],
        "legal_basis": "§ 18 Abs. 1 UStG",
        "note": "Vorauszahlung für das 4. Quartal des Vorjahres fällig.",
    },
    "ust_vorauszahlung_q2": {
        "month": 4, "day": 10,
        "label": "USt-Vorauszahlung Q1 — 10. April",
        "category": "vat_prepayment",
        "applies_to": ["freelancer", "self_employed"],
        "legal_basis": "§ 18 Abs. 1 UStG",
        "note": "Vorauszahlung für das 1. Quartal fällig.",
    },
    "ust_vorauszahlung_q3": {
        "month": 7, "day": 10,
        "label": "USt-Vorauszahlung Q2 — 10. Juli",
        "category": "vat_prepayment",
        "applies_to": ["freelancer", "self_employed"],
        "legal_basis": "§ 18 Abs. 1 UStG",
        "note": "Vorauszahlung für das 2. Quartal fällig.",
    },
    "ust_vorauszahlung_q4": {
        "month": 10, "day": 10,
        "label": "USt-Vorauszahlung Q3 — 10. Oktober",
        "category": "vat_prepayment",
        "applies_to": ["freelancer", "self_employed"],
        "legal_basis": "§ 18 Abs. 1 UStG",
        "note": "Vorauszahlung für das 3. Quartal fällig.",
    },
    "lohnsteueranmeldung_monthly": {
        "month": None, "day": 10,
        "label": "Lohnsteueranmeldung — 10. des Folgemonats",
        "category": "payroll_tax",
        "applies_to": ["employer"],
        "legal_basis": "§ 41a Abs. 2 EStG",
        "note": "Monatlich, sofern Lohnsteuer im Vorjahr > €5.000.",
    },
    "lohnsteueranmeldung_quarterly": {
        "month": None, "day": 10,
        "label": "Lohnsteueranmeldung — 10. des Folgequartals",
        "category": "payroll_tax",
        "applies_to": ["employer"],
        "legal_basis": "§ 41a Abs. 2 EStG",
        "note": "Quartalsweise, sofern Lohnsteuer im Vorjahr €1.080–€5.000.",
    },
    "vorabpauschale": {
        "month": 1, "day": 15,
        "label": "Vorabpauschale Fonds — Januar (Depotverwahrer)",
        "category": "investment",
        "applies_to": ["investor"],
        "legal_basis": "§ 16 InvStG",
        "note": "Depotverwahrer zieht Vorabpauschale automatisch ab; Freistellungsauftrag prüfen.",
    },
    "freistellungsauftrag_reminder": {
        "month": 1, "day": 1,
        "label": "Freistellungsauftrag überprüfen — Jahresbeginn",
        "category": "reminder",
        "applies_to": ["investor", "employed", "freelancer"],
        "legal_basis": "§ 44a EStG",
        "note": "Sparer-Pauschbetrag-Aufteilung auf Kreditinstitute optimieren.",
    },
}


def _last_day_of_february(year: int) -> int:
    return monthrange(year, 2)[1]


def get_filing_deadline(tax_year: int, advised: bool = False, agriculture: bool = False) -> date:
    """Return the filing deadline date for a given tax year.

    Args:
        tax_year: The year the income was earned (e.g. 2024).
        advised: True if the taxpayer uses a tax adviser.
        agriculture: True for agricultural businesses (extended deadlines).

    Returns:
        The filing deadline as a date object.
    """
    if advised:
        advised_table = ADVISED_DEADLINES[True]
        if tax_year in advised_table:
            return advised_table[tax_year]
        if agriculture:
            return date(tax_year + 2, 7, 31)
        return date(tax_year + 2, 2, _last_day_of_february(tax_year + 2))
    # Standard without-adviser deadline: check table, else 31 Jul of following year
    no_adviser_table = ADVISED_DEADLINES[False]
    if tax_year in no_adviser_table:
        return no_adviser_table[tax_year]
    return date(tax_year + 1, 7, 31)


def format_deadline_label(tax_year: int, advised: bool = False, agriculture: bool = False) -> str:
    """Return a human-readable deadline label."""
    deadline = get_filing_deadline(tax_year, advised=advised, agriculture=agriculture)
    label = "with tax adviser" if advised else "without tax adviser"
    if agriculture:
        label += ", agriculture case"
    return f"{deadline.isoformat()} ({label})"


def get_upcoming_deadlines(year: int, months_ahead: int = 3) -> list[dict]:
    """Return all tax-relevant deadlines in the next N months from 1 Jan of year.

    Includes quarterly USt-Vorauszahlung dates, Vorabpauschale, and
    Freistellungsauftrag reminder for the given calendar year.

    Args:
        year: The calendar year to compute dates for.
        months_ahead: How many months ahead to look (default 3).

    Returns:
        List of dicts with keys: date (ISO string), label, category,
        applies_to, legal_basis, note. Sorted by date ascending.
    """
    today = date(year, 1, 1)
    cutoff = date(year + (months_ahead // 12), ((months_ahead % 12) or 12), 1)
    # Simpler: use a fixed offset
    cutoff_month = (1 + months_ahead - 1) % 12 + 1
    cutoff_year = year + (1 + months_ahead - 1) // 12
    cutoff = date(cutoff_year, cutoff_month, 1)

    results = []

    for key, info in IMPORTANT_DATES.items():
        if info["month"] is None:
            continue  # skip dynamic monthly/quarterly entries
        d = date(year, info["month"], info["day"])
        if today <= d < cutoff:
            results.append({
                "date": d.isoformat(),
                "label": info["label"],
                "category": info["category"],
                "applies_to": info["applies_to"],
                "legal_basis": info["legal_basis"],
                "note": info["note"],
            })

    results.sort(key=lambda x: x["date"])
    return results
