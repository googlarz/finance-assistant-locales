"""
Dutch tax filing deadlines (aangifte inkomstenbelasting).

The Dutch tax year is the calendar year (1 Jan – 31 Dec). The aangifte
(return) is filed online via Mijn Belastingdienst using DigiD, with the
standard deadline of 1 May of the following year.

The Box 3 peildatum (reference date for asset valuation) is 1 January of
the tax year.

Sources:
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/aangifte_doen/wanneer_aangifte_doen/
  https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/aangifte_doen/
"""

from __future__ import annotations

_DEADLINES = {
    2024: {
        "confidence": "Definitive",
        "entries": [
            {
                "label": "Aangifte inkomstenbelasting — standaard deadline",
                "deadline": "2025-05-01",
                "notes": (
                    "Standard online filing deadline via Mijn Belastingdienst (DigiD). "
                    "Definitive. Paper returns must be received by 1 May."
                ),
            },
            {
                "label": "Uitstel aangifte (op verzoek)",
                "deadline": "2025-09-01",
                "notes": (
                    "Extension available on request via Mijn Belastingdienst. "
                    "Submit extension request before 1 May."
                ),
            },
            {
                "label": "M-formulier (migratie-/kwalificerend buitenlands belastingplichtige)",
                "deadline": "2025-08-01",
                "notes": (
                    "M-form for taxpayers who immigrated to or emigrated from the Netherlands "
                    "during the tax year."
                ),
            },
            {
                "label": "Voorlopige aanslag aanvragen",
                "deadline": "2025-04-30",
                "notes": (
                    "Request a provisional assessment (voorlopige aanslag) to pay or receive "
                    "tax in installments. Submit before 1 May."
                ),
            },
            {
                "label": "Box 3 peildatum (vermogenspeildatum)",
                "deadline": "2024-01-01",
                "notes": (
                    "Reference date for Box 3 asset valuation (savings and investments). "
                    "Asset values on 1 January 2024 determine Box 3 base."
                ),
            },
            {
                "label": "Betaling definitieve aanslag",
                "deadline": "2025-11-15",
                "notes": (
                    "Estimated payment deadline for the final tax assessment, "
                    "typically within 6 weeks of receiving the aanslag."
                ),
            },
        ],
    },
    2025: {
        "confidence": "Likely",
        "entries": [
            {
                "label": "Aangifte inkomstenbelasting — standaard deadline",
                "deadline": "2026-05-01",
                "notes": (
                    "Estimated standard online filing deadline (Likely). "
                    "Via Mijn Belastingdienst using DigiD."
                ),
            },
            {
                "label": "Uitstel aangifte (op verzoek)",
                "deadline": "2026-09-01",
                "notes": "Estimated extension deadline (Likely). Request before 1 May 2026.",
            },
            {
                "label": "M-formulier",
                "deadline": "2026-08-01",
                "notes": "Estimated M-form deadline for migration-year taxpayers (Likely).",
            },
            {
                "label": "Voorlopige aanslag aanvragen",
                "deadline": "2026-04-30",
                "notes": "Estimated deadline to request provisional assessment (Likely).",
            },
            {
                "label": "Box 3 peildatum (vermogenspeildatum)",
                "deadline": "2025-01-01",
                "notes": "Reference date for Box 3 asset valuation: 1 January 2025.",
            },
            {
                "label": "Betaling definitieve aanslag",
                "deadline": "2026-11-15",
                "notes": "Estimated final tax assessment payment deadline (Likely).",
            },
        ],
    },
    2026: {
        "confidence": "Likely",
        "entries": [
            {
                "label": "Aangifte inkomstenbelasting — standaard deadline",
                "deadline": "2027-05-01",
                "notes": "Estimated standard online filing deadline (Likely).",
            },
            {
                "label": "Uitstel aangifte (op verzoek)",
                "deadline": "2027-09-01",
                "notes": "Estimated extension deadline (Likely). Request before 1 May 2027.",
            },
            {
                "label": "M-formulier",
                "deadline": "2027-08-01",
                "notes": "Estimated M-form deadline for migration-year taxpayers (Likely).",
            },
            {
                "label": "Voorlopige aanslag aanvragen",
                "deadline": "2027-04-30",
                "notes": "Estimated deadline to request provisional assessment (Likely).",
            },
            {
                "label": "Box 3 peildatum (vermogenspeildatum)",
                "deadline": "2026-01-01",
                "notes": (
                    "Reference date for Box 3 asset valuation: 1 January 2026. "
                    "Note: Box 3 legal status may change before this date."
                ),
            },
            {
                "label": "Betaling definitieve aanslag",
                "deadline": "2027-11-15",
                "notes": "Estimated final tax assessment payment deadline (Likely).",
            },
        ],
    },
}


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return all tax filing deadlines for the given Dutch tax year.

    Each entry has:
      label      — human-readable name in Dutch
      deadline   — ISO 8601 date string (YYYY-MM-DD)
      notes      — explanation or conditions
      confidence — Definitive / Likely
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
