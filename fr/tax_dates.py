"""
French tax filing deadlines.

The French tax year is the calendar year (1 Jan – 31 Dec).
Declarations are filed in spring of the following year via impots.gouv.fr.
Since 2019, prélèvement à la source (withholding at source) collects tax
throughout the year; the spring declaration adjusts for the final balance.

Zone breakdown for online deadlines:
  Zone 1: départements 01–19 (métropole)
  Zone 2: départements 20–54 + DOM (Outre-Mer)
  Zone 3: départements 55–976 (including overseas)

Sources:
  https://www.impots.gouv.fr/particulier/declaration-annuelle
  https://www.service-public.fr/particuliers/vosdroits/F358
"""

from __future__ import annotations

# Deadlines for each tax year. Dates are ISO 8601 strings.
# Deadlines marked "Likely" are estimates for future years.

_DEADLINES = {
    2024: {
        "confidence": "Definitive",
        "filing_year": 2025,
        "entries": [
            {
                "label": "Ouverture déclaration en ligne",
                "deadline": "2025-04-10",
                "notes": "Opening date for online income declaration on impots.gouv.fr.",
            },
            {
                "label": "Déclaration papier (limite)",
                "deadline": "2025-05-19",
                "notes": "Paper declaration deadline (sent to tax office). Definitive.",
            },
            {
                "label": "Déclaration en ligne — Zone 1 (dép. 01–19)",
                "deadline": "2025-05-23",
                "notes": "Online deadline for Zone 1 (départements 01 to 19). Definitive.",
            },
            {
                "label": "Déclaration en ligne — Zone 2 (dép. 20–54 + DOM)",
                "deadline": "2025-05-30",
                "notes": "Online deadline for Zone 2 (départements 20 to 54 and DOM). Definitive.",
            },
            {
                "label": "Déclaration en ligne — Zone 3 (dép. 55–976)",
                "deadline": "2025-06-06",
                "notes": "Online deadline for Zone 3 (départements 55 to 976). Definitive.",
            },
            {
                "label": "Paiement solde d'impôt (si > 300 €)",
                "deadline": "2025-09-15",
                "notes": "Balance payment if total tax due exceeds €300. Direct debit via SEPA.",
            },
            {
                "label": "Prélèvement à la source — mensuel",
                "deadline": "2024-01-15",
                "notes": (
                    "Monthly withholding throughout the tax year (January–December 2024). "
                    "Deducted from salary by employer."
                ),
            },
        ],
    },
    2025: {
        "confidence": "Likely",
        "filing_year": 2026,
        "entries": [
            {
                "label": "Ouverture déclaration en ligne",
                "deadline": "2026-04-09",
                "notes": "Estimated opening date (Likely) for 2025 income declaration.",
            },
            {
                "label": "Déclaration papier (limite)",
                "deadline": "2026-05-18",
                "notes": "Estimated paper deadline (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 1 (dép. 01–19)",
                "deadline": "2026-05-22",
                "notes": "Estimated online deadline Zone 1 (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 2 (dép. 20–54 + DOM)",
                "deadline": "2026-05-29",
                "notes": "Estimated online deadline Zone 2 (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 3 (dép. 55–976)",
                "deadline": "2026-06-05",
                "notes": "Estimated online deadline Zone 3 (Likely).",
            },
            {
                "label": "Paiement solde d'impôt (si > 300 €)",
                "deadline": "2026-09-15",
                "notes": "Estimated balance payment deadline (Likely).",
            },
            {
                "label": "Prélèvement à la source — mensuel",
                "deadline": "2025-01-15",
                "notes": "Monthly withholding throughout tax year 2025.",
            },
        ],
    },
    2026: {
        "confidence": "Likely",
        "filing_year": 2027,
        "entries": [
            {
                "label": "Ouverture déclaration en ligne",
                "deadline": "2027-04-08",
                "notes": "Estimated opening date (Likely) for 2026 income declaration.",
            },
            {
                "label": "Déclaration papier (limite)",
                "deadline": "2027-05-17",
                "notes": "Estimated paper deadline (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 1 (dép. 01–19)",
                "deadline": "2027-05-21",
                "notes": "Estimated online deadline Zone 1 (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 2 (dép. 20–54 + DOM)",
                "deadline": "2027-05-28",
                "notes": "Estimated online deadline Zone 2 (Likely).",
            },
            {
                "label": "Déclaration en ligne — Zone 3 (dép. 55–976)",
                "deadline": "2027-06-04",
                "notes": "Estimated online deadline Zone 3 (Likely).",
            },
            {
                "label": "Paiement solde d'impôt (si > 300 €)",
                "deadline": "2027-09-15",
                "notes": "Estimated balance payment deadline (Likely).",
            },
            {
                "label": "Prélèvement à la source — mensuel",
                "deadline": "2026-01-15",
                "notes": "Monthly withholding throughout tax year 2026.",
            },
        ],
    },
}


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return all tax filing deadlines for the given French tax year.

    Each entry has:
      label     — human-readable name
      deadline  — ISO 8601 date string (YYYY-MM-DD)
      notes     — explanation or conditions
    """
    if year not in _DEADLINES:
        supported = sorted(_DEADLINES)
        fallback = supported[-1] if year > supported[-1] else supported[0]
        data = _DEADLINES[fallback]
    else:
        data = _DEADLINES[year]

    result = []
    for entry in data["entries"]:
        result.append({
            "label": entry["label"],
            "deadline": entry["deadline"],
            "notes": entry["notes"],
            "confidence": data["confidence"],
        })
    return result
