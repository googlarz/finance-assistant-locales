"""
Polish tax filing deadlines and important dates.

Polish tax year = calendar year (1 January – 31 December).

Key dates for PIT (year Y, filed in Y+1):
  - PIT-11 (employer's certificate):   issued to employee by 31 January Y+1
  - PIT-8C (capital gains statement):  issued by brokers by end of February Y+1
  - Twój e-PIT (pre-filled return):    available from 15 February Y+1
      * If not rejected/modified, it is auto-accepted on 30 April Y+1
  - PIT-37 / PIT-36 filing deadline:   30 April Y+1
  - Quarterly advance payments (self-employed):
      Q1 (Jan–Mar)  → 20 April Y
      Q2 (Apr–Jun)  → 20 July Y
      Q3 (Jul–Sep)  → 20 October Y
      Q4 (Oct–Dec)  → 20 January Y+1
  - Monthly advance payments (large self-employed): 20th of following month

Sources:
  https://www.podatki.gov.pl/pit/twoj-e-pit/
  https://www.podatki.gov.pl/pit/terminy-i-sposoby-skladania-zeznania-pit/
"""

from __future__ import annotations
from datetime import date


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return all relevant PIT filing and payment deadlines for the given tax year.

    Args:
        year: Calendar tax year (e.g. 2024 → deadlines for filing 2024 income).

    Returns:
        List of dicts with keys: label, deadline (ISO 8601), notes.
    """
    y = year       # Tax year being filed
    y1 = year + 1  # Year in which filing takes place

    deadlines = [
        {
            "label": "PIT-11 od pracodawcy (employer certificate)",
            "deadline": f"{y1}-01-31",
            "notes": (
                f"Pracodawca jest zobowiązany przesłać PIT-11 za rok {y} "
                f"do pracownika i do urzędu skarbowego do 31 stycznia {y1}. "
                "This certificate shows total salary, ZUS, and income tax withheld."
            ),
        },
        {
            "label": "PIT-8C (capital gains statement from broker)",
            "deadline": f"{y1}-02-28",
            "notes": (
                f"Brokerzy przesyłają PIT-8C za rok {y} do końca lutego {y1}. "
                "Required if you had investment gains/losses reported via a Polish brokerage."
            ),
        },
        {
            "label": "Twój e-PIT dostępny (pre-filled return available)",
            "deadline": f"{y1}-02-15",
            "notes": (
                f"Twój e-PIT za rok {y} jest dostępny od 15 lutego {y1} na podatki.gov.pl. "
                "The return is pre-filled with data from employers and ZUS. "
                "IMPORTANT: if you do not reject or modify it, it is automatically accepted "
                f"on 30 April {y1}."
            ),
        },
        {
            "label": "PIT-37 / PIT-36 — termin złożenia zeznania (filing deadline)",
            "deadline": f"{y1}-04-30",
            "notes": (
                f"Termin złożenia zeznania PIT-37 lub PIT-36 za rok {y} to 30 kwietnia {y1}. "
                "PIT-37 is for employees (one employer, no business income). "
                "PIT-36 is for those with additional income sources, self-employment "
                "(skala podatkowa), or foreign income. "
                "Twój e-PIT is also auto-accepted on this date if not modified."
            ),
        },
        {
            "label": "Quarterly advance — Q1 (samorozliczenie zaliczki Q1)",
            "deadline": f"{y}-04-20",
            "notes": (
                f"Self-employed paying quarterly advances: Q1 ({y} Jan–Mar) "
                f"due 20 April {y}. Applies to działalność gospodarcza on skala podatkowa, "
                "podatek liniowy, or ryczałt (quarterly option)."
            ),
        },
        {
            "label": "Quarterly advance — Q2 (samorozliczenie zaliczki Q2)",
            "deadline": f"{y}-07-20",
            "notes": (
                f"Self-employed paying quarterly advances: Q2 ({y} Apr–Jun) "
                f"due 20 July {y}."
            ),
        },
        {
            "label": "Quarterly advance — Q3 (samorozliczenie zaliczki Q3)",
            "deadline": f"{y}-10-20",
            "notes": (
                f"Self-employed paying quarterly advances: Q3 ({y} Jul–Sep) "
                f"due 20 October {y}."
            ),
        },
        {
            "label": "Quarterly advance — Q4 (samorozliczenie zaliczki Q4)",
            "deadline": f"{y1}-01-20",
            "notes": (
                f"Self-employed paying quarterly advances: Q4 ({y} Oct–Dec) "
                f"due 20 January {y1}. "
                "Note: this is the same deadline as the Q4 advance, not the annual filing."
            ),
        },
    ]

    return deadlines


def get_upcoming_deadlines(year: int, months_ahead: int = 3) -> list[dict]:
    """
    Return PIT-related deadlines falling within the next N months
    from 1 January of the given calendar year.

    Args:
        year:         Calendar year to base the window on.
        months_ahead: How many calendar months ahead to look (default 3).

    Returns:
        List of deadline dicts sorted by date ascending.
    """
    window_start = date(year, 1, 1)
    end_month = window_start.month + months_ahead
    end_year = window_start.year + (end_month - 1) // 12
    end_month = ((end_month - 1) % 12) + 1
    window_end = date(end_year, end_month, 1)

    # Gather deadlines from two tax years to cover the window
    candidates = []
    for tax_year in (year - 2, year - 1, year):
        for dl in get_filing_deadlines(tax_year):
            candidates.append(dl)

    results = []
    for dl in candidates:
        try:
            dl_date = date.fromisoformat(dl["deadline"])
        except ValueError:
            continue
        if window_start <= dl_date < window_end:
            results.append(dl)

    results.sort(key=lambda x: x["deadline"])
    # Deduplicate by deadline+label in case of overlap
    seen = set()
    deduped = []
    for dl in results:
        key = (dl["deadline"], dl["label"])
        if key not in seen:
            seen.add(key)
            deduped.append(dl)

    return deduped
